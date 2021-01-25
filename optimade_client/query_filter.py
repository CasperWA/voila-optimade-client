from enum import Enum, auto
from typing import List, Union
import traitlets
import ipywidgets as ipw
import requests

try:
    from simplejson import JSONDecodeError
except (ImportError, ModuleNotFoundError):
    from json import JSONDecodeError

from optimade.adapters import Structure
from optimade.models import LinksResourceAttributes
from optimade.models.utils import CHEMICAL_SYMBOLS, SemanticVersion

from optimade_client.exceptions import BadResource, QueryError
from optimade_client.logger import LOGGER
from optimade_client.subwidgets import (
    FilterTabs,
    ResultsPageChooser,
    SortSelector,
    StructureDropdown,
)
from optimade_client.utils import (
    ButtonStyle,
    check_entry_properties,
    handle_errors,
    ordered_query_url,
    perform_optimade_query,
    get_sortable_fields,
    SESSION,
    TIMEOUT_SECONDS,
)


class QueryFilterWidgetOrder(Enum):
    """Order of filter query widget parts"""

    filter_header = auto()
    filters = auto()
    query_button = auto()
    structures_header = auto()
    structure_drop = auto()
    sort_selector = auto()
    error_or_status_messages = auto()
    structure_page_chooser = auto()

    @classmethod
    def default_order(
        cls, as_str: bool = True
    ) -> List[Union[str, "QueryFilterWidgetOrder"]]:
        """Get the default order of filter query widget parts"""
        default_order = [
            cls.filter_header,
            cls.filters,
            cls.query_button,
            cls.structures_header,
            cls.sort_selector,
            cls.structure_page_chooser,
            cls.structure_drop,
            cls.error_or_status_messages,
        ]
        return [_.name for _ in default_order] if as_str else default_order


class OptimadeQueryFilterWidget(  # pylint: disable=too-many-instance-attributes
    ipw.VBox
):
    """Structure search and import widget for OPTIMADE

    NOTE: Only supports offset- and number-pagination at the moment.
    """

    structure = traitlets.Instance(Structure, allow_none=True)
    database = traitlets.Tuple(
        traitlets.Unicode(),
        traitlets.Instance(LinksResourceAttributes, allow_none=True),
    )

    def __init__(
        self,
        result_limit: int = None,
        button_style: Union[ButtonStyle, str] = None,
        embedded: bool = False,
        subparts_order: List[str] = None,
        **kwargs,
    ):
        self.page_limit = result_limit if result_limit else 10
        if button_style:
            if isinstance(button_style, str):
                button_style = ButtonStyle[button_style.upper()]
            elif isinstance(button_style, ButtonStyle):
                pass
            else:
                raise TypeError(
                    "button_style should be either a string or a ButtonStyle Enum. "
                    f"You passed type {type(button_style)!r}."
                )
        else:
            button_style = ButtonStyle.PRIMARY

        subparts_order = subparts_order or QueryFilterWidgetOrder.default_order(
            as_str=True
        )

        self.offset = 0
        self.number = 1
        self._data_available = None
        self.__perform_query = True
        self.__cached_ranges = {}
        self.__cached_versions = {}
        self.database_version = ""

        self.filter_header = ipw.HTML(
            '<h4 style="margin:0px;padding:0px;">Apply filters</h4>'
        )
        self.filters = FilterTabs(show_large_filters=not embedded)
        self.filters.freeze()
        self.filters.on_submit(self.retrieve_data)

        self.query_button = ipw.Button(
            description="Search",
            button_style=button_style.value,
            icon="search",
            disabled=True,
            tooltip="Search - No database chosen",
        )
        self.query_button.on_click(self.retrieve_data)

        self.structures_header = ipw.HTML(
            '<h4 style="margin-bottom:0px;padding:0px;">Results</h4>'
        )

        self.sort_selector = SortSelector(disabled=True)
        self.sorting = self.sort_selector.value
        self.sort_selector.observe(self._sort, names="value")

        self.structure_drop = StructureDropdown(disabled=True)
        self.structure_drop.observe(self._on_structure_select, names="value")
        self.error_or_status_messages = ipw.HTML("")

        self.structure_page_chooser = ResultsPageChooser(self.page_limit)
        self.structure_page_chooser.observe(
            self._get_more_results, names=["page_link", "page_offset", "page_number"]
        )

        for subpart in subparts_order:
            if not hasattr(self, subpart):
                raise ValueError(
                    f"Wrongly specified subpart_order: {subpart!r}. Available subparts "
                    f"(and default order): {QueryFilterWidgetOrder.default_order(as_str=True)}"
                )

        super().__init__(
            children=[getattr(self, _) for _ in subparts_order],
            layout=ipw.Layout(width="auto", height="auto"),
            **kwargs,
        )

    @traitlets.observe("database")
    def _on_database_select(self, _):
        """Load chosen database"""
        self.structure_drop.reset()

        if (
            self.database[1] is None
            or getattr(self.database[1], "base_url", None) is None
        ):
            self.query_button.tooltip = "Search - No database chosen"
            self.freeze()
        else:
            self.offset = 0
            self.number = 1
            self.structure_page_chooser.silent_reset()
            try:
                self.freeze()

                self.query_button.description = "Updating ..."
                self.query_button.icon = "cog"
                self.query_button.tooltip = "Updating filters ..."

                self._set_intslider_ranges()
                self._set_version()
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error(
                    "Exception raised during setting IntSliderRanges: %s",
                    exc.with_traceback(),
                )
            finally:
                self.query_button.description = "Search"
                self.query_button.icon = "search"
                self.query_button.tooltip = "Search"
                self.sort_selector.valid_fields = sorted(
                    get_sortable_fields(self.database[1].base_url)
                )
                self.unfreeze()

    def _on_structure_select(self, change):
        """Update structure trait with chosen structure dropdown value"""
        chosen_structure = change["new"]
        if chosen_structure is None:
            self.structure = None
            with self.hold_trait_notifications():
                self.structure_drop.index = 0
        else:
            self.structure = chosen_structure["structure"]

    def _get_more_results(self, change):
        """Query for more results according to pageing"""
        if not self.__perform_query:
            self.__perform_query = True
            LOGGER.debug(
                "NOT going to perform query with change: name=%s value=%s",
                change["name"],
                change["new"],
            )
            return

        pageing: Union[int, str] = change["new"]
        LOGGER.debug(
            "Updating results with pageing change: name=%s value=%s",
            change["name"],
            pageing,
        )
        if change["name"] == "page_offset":
            self.offset = pageing
            pageing = None
        elif change["name"] == "page_number":
            self.number = pageing
            pageing = None
        else:
            # It is needed to update page_offset, but we do not wish to query again
            with self.hold_trait_notifications():
                self.__perform_query = False
                self.structure_page_chooser.update_offset()

        try:
            # Freeze and disable list of structures in dropdown widget
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Update button text and icon
            self.query_button.description = "Updating ... "
            self.query_button.icon = "cog"
            self.query_button.tooltip = "Please wait ..."

            # Query database
            response = self._query(pageing)
            msg, _ = handle_errors(response)
            if msg:
                self.error_or_status_messages.value = msg
                return

            # Update list of structures in dropdown widget
            self._update_structures(response["data"])

            # Update pageing
            self.structure_page_chooser.set_pagination_data(
                links_to_page=response.get("links", {}),
            )

        finally:
            self.query_button.description = "Search"
            self.query_button.icon = "search"
            self.query_button.tooltip = "Search"
            self.unfreeze()

    def _sort(self, change: dict) -> None:
        """"Perform new query with new sorting"""
        sort = change["new"]
        if not sort:
            raise ValueError(
                f"The sort parameter could not be determined (sort={sort!r})."
            )
        self.sorting = sort
        self.retrieve_data({})

    def freeze(self):
        """Disable widget"""
        self.query_button.disabled = True
        self.filters.freeze()
        self.structure_drop.freeze()
        self.structure_page_chooser.freeze()
        self.sort_selector.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.query_button.disabled = False
        self.filters.unfreeze()
        self.structure_drop.unfreeze()
        self.structure_page_chooser.unfreeze()
        self.sort_selector.unfreeze()

    def reset(self):
        """Reset widget"""
        self.offset = 0
        self.number = 1
        with self.hold_trait_notifications():
            self.query_button.disabled = False
            self.query_button.tooltip = "Search - No database chosen"
            self.filters.reset()
            self.structure_drop.reset()
            self.structure_page_chooser.reset()
            self.sort_selector.reset()

    def _uses_new_structure_features(self) -> bool:
        """Check whether self.database_version is >= v1.0.0-rc.2"""
        critical_version = SemanticVersion("1.0.0-rc.2")
        version = SemanticVersion(self.database_version)

        LOGGER.debug("Semantic version: %r", version)

        if version.base_version > critical_version.base_version:
            return True

        if version.base_version == critical_version.base_version:
            if version.prerelease:
                return version.prerelease >= critical_version.prerelease

            # Version is bigger than critical version and is not a pre-release
            return True

        # Major.Minor.Patch is lower than critical version
        return False

    def _set_version(self):
        """Set self.database_version from an /info query"""
        base_url = self.database[1].base_url
        if base_url not in self.__cached_versions:
            # Retrieve and cache version
            response = perform_optimade_query(
                base_url=self.database[1].base_url, endpoint="/info"
            )
            msg, _ = handle_errors(response)
            if msg:
                raise QueryError(msg)

            if "meta" not in response:
                raise QueryError(
                    f"'meta' field not found in /info endpoint for base URL: {base_url}"
                )
            if "api_version" not in response["meta"]:
                raise QueryError(
                    f"'api_version' field not found in 'meta' for base URL: {base_url}"
                )

            version = response["meta"]["api_version"]
            if version.startswith("v"):
                version = version[1:]
            self.__cached_versions[base_url] = version
            LOGGER.debug(
                "Cached version %r for base URL: %r",
                self.__cached_versions[base_url],
                base_url,
            )

        self.database_version = self.__cached_versions[base_url]

    def _set_intslider_ranges(self):
        """Update IntRangeSlider ranges according to chosen database

        Query database to retrieve ranges.
        Cache ranges in self.__cached_ranges.
        """
        defaults = {
            "nsites": {"min": 0, "max": 10000},
            "nelements": {"min": 0, "max": len(CHEMICAL_SYMBOLS)},
        }

        db_base_url = self.database[1].base_url
        if db_base_url not in self.__cached_ranges:
            self.__cached_ranges[db_base_url] = {}

        sortable_fields = check_entry_properties(
            base_url=db_base_url,
            entry_endpoint="structures",
            properties=["nsites", "nelements"],
            checks=["sort"],
        )

        for response_field in sortable_fields:
            if response_field in self.__cached_ranges[db_base_url]:
                # Use cached value(s)
                continue

            page_limit = 1

            new_range = {}
            for extremum, sort in [
                ("min", response_field),
                ("max", f"-{response_field}"),
            ]:
                query_params = {
                    "base_url": db_base_url,
                    "page_limit": page_limit,
                    "response_fields": response_field,
                    "sort": sort,
                }
                LOGGER.debug(
                    "Querying %s to get %s of %s.\nParameters: %r",
                    self.database[0],
                    extremum,
                    response_field,
                    query_params,
                )

                response = perform_optimade_query(**query_params)
                msg, _ = handle_errors(response)
                if msg:
                    raise QueryError(msg)

                if not response.get("meta", {}).get("data_available", 0):
                    new_range[extremum] = defaults[response_field][extremum]
                else:
                    new_range[extremum] = (
                        response.get("data", [{}])[0]
                        .get("attributes", {})
                        .get(response_field, None)
                    )

            # Cache new values
            LOGGER.debug(
                "Caching newly found range values for %s\nValue: %r",
                db_base_url,
                {response_field: new_range},
            )
            self.__cached_ranges[db_base_url].update({response_field: new_range})

        if not self.__cached_ranges[db_base_url]:
            LOGGER.debug("No values found for %s, storing default values.", db_base_url)
            self.__cached_ranges[db_base_url].update(
                {
                    "nsites": {"min": 0, "max": 10000},
                    "nelements": {"min": 0, "max": len(CHEMICAL_SYMBOLS)},
                }
            )

        # Set widget's new extrema
        LOGGER.debug(
            "Updating range extrema for %s\nValues: %r",
            db_base_url,
            self.__cached_ranges[db_base_url],
        )
        self.filters.update_range_filters(self.__cached_ranges[db_base_url])

    def _query(self, link: str = None) -> dict:
        """Query helper function"""
        # If a complete link is provided, use it straight up
        if link is not None:
            try:
                link = ordered_query_url(link)
                response = SESSION.get(link, timeout=TIMEOUT_SECONDS)
                if response.from_cache:
                    LOGGER.debug("Request to %s was taken from cache !", link)
                response = response.json()
            except (
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
            ) as exc:
                response = {
                    "errors": {
                        "msg": "CLIENT: Connection error or timeout.",
                        "url": link,
                        "Exception": repr(exc),
                    }
                }
            except JSONDecodeError as exc:
                response = {
                    "errors": {
                        "msg": "CLIENT: Could not decode response to JSON.",
                        "url": link,
                        "Exception": repr(exc),
                    }
                }
            return response

        # Avoid structures with null positions and with assemblies.
        add_to_filter = 'NOT structure_features HAS ANY "assemblies"'
        if not self._uses_new_structure_features():
            add_to_filter += ',"unknown_positions"'

        optimade_filter = self.filters.collect_value()
        optimade_filter = (
            "( {} ) AND ( {} )".format(optimade_filter, add_to_filter)
            if optimade_filter and add_to_filter
            else optimade_filter or add_to_filter or None
        )
        LOGGER.debug("Querying with filter: %s", optimade_filter)

        # OPTIMADE queries
        queries = {
            "base_url": self.database[1].base_url,
            "filter": optimade_filter,
            "page_limit": self.page_limit,
            "page_offset": self.offset,
            "page_number": self.number,
            "sort": self.sorting,
        }
        LOGGER.debug(
            "Parameters (excluding filter) sent to query util func: %s",
            {key: value for key, value in queries.items() if key != "filter"},
        )

        return perform_optimade_query(**queries)

    def _update_structures(self, data: list):
        """Update structures dropdown from response data"""
        structures = []

        for entry in data:
            structure = Structure(entry)

            formula = structure.attributes.chemical_formula_descriptive
            if formula is None:
                formula = structure.attributes.chemical_formula_reduced
            if formula is None:
                formula = structure.attributes.chemical_formula_anonymous
            if formula is None:
                formula = structure.attributes.chemical_formula_hill
            if formula is None:
                raise BadResource(
                    resource=structure,
                    fields=[
                        "chemical_formula_descriptive",
                        "chemical_formula_reduced",
                        "chemical_formula_anonymous",
                        "chemical_formula_hill",
                    ],
                    msg="At least one of the following chemical formula fields "
                    "should have a valid value",
                )

            entry_name = f"{formula} (id={structure.id})"
            structures.append((entry_name, {"structure": structure}))

        # Update list of structures in dropdown widget
        self.structure_drop.set_options(structures)

    def retrieve_data(self, _):
        """Perform query and retrieve data"""
        self.offset = 0
        self.number = 1
        try:
            # Freeze and disable list of structures in dropdown widget
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Reset the error or status message
            if self.error_or_status_messages.value:
                self.error_or_status_messages.value = ""

            # Update button text and icon
            self.query_button.description = "Querying ... "
            self.query_button.icon = "cog"
            self.query_button.tooltip = "Please wait ..."

            # Query database
            response = self._query()
            msg, _ = handle_errors(response)
            if msg:
                self.error_or_status_messages.value = msg
                raise QueryError(msg)

            # Update list of structures in dropdown widget
            self._update_structures(response["data"])

            # Update pageing
            if self._data_available is None:
                self._data_available = response.get("meta", {}).get(
                    "data_available", None
                )
            data_returned = response.get("meta", {}).get(
                "data_returned", len(response.get("data", []))
            )
            self.structure_page_chooser.set_pagination_data(
                data_returned=data_returned,
                data_available=self._data_available,
                links_to_page=response.get("links", {}),
                reset_cache=True,
            )

            # Note if no data has been found
            if not data_returned:
                self.error_or_status_messages.value = "No structures found!"

        except QueryError:
            self.structure_drop.reset()
            self.structure_page_chooser.reset()

        except Exception as exc:
            self.structure_drop.reset()
            self.structure_page_chooser.reset()
            raise QueryError(f"Bad stuff happened: {exc!r}") from exc

        finally:
            self.query_button.description = "Search"
            self.query_button.icon = "search"
            self.query_button.tooltip = "Search"
            self.unfreeze()
