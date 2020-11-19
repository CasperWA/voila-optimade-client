import os
from typing import List, Tuple, Union
import urllib.parse

try:
    import simplejson as json
except ImportError:
    import json

import ipywidgets as ipw
import requests
import traitlets

from ipywidgets_extended.dropdown import DropdownExtended

from optimade.models import LinksResource, LinksResourceAttributes
from optimade.models.links import LinkType

from optimade_client.exceptions import OptimadeClientError, QueryError
from optimade_client.logger import LOGGER
from optimade_client.subwidgets.results import ResultsPageChooser
from optimade_client.utils import (
    get_list_of_valid_providers,
    get_versioned_base_url,
    handle_errors,
    ordered_query_url,
    perform_optimade_query,
    SESSION,
    TIMEOUT_SECONDS,
    update_old_links_resources,
    validate_api_version,
)


__all__ = ("ProviderImplementationChooser", "ProviderImplementationSummary")


class ProviderImplementationChooser(  # pylint: disable=too-many-instance-attributes
    ipw.VBox
):
    """List all OPTIMADE providers and their implementations"""

    provider = traitlets.Instance(LinksResourceAttributes, allow_none=True)
    database = traitlets.Tuple(
        traitlets.Unicode(),
        traitlets.Instance(LinksResourceAttributes, allow_none=True),
        default_value=("", None),
    )

    HINT = {"provider": "Select a provider", "child_dbs": "Select a database"}
    INITIAL_CHILD_DBS = [("No provider chosen", None)]

    def __init__(self, child_db_limit: int = None, **kwargs):
        self.child_db_limit = (
            child_db_limit if child_db_limit and child_db_limit > 0 else 10
        )
        self.offset = 0
        self.number = 1
        self.__perform_query = True
        self.__cached_child_dbs = {}

        self.debug = bool(os.environ.get("OPTIMADE_CLIENT_DEBUG", None))

        dropdown_layout = ipw.Layout(width="auto")

        providers = []
        providers, invalid_providers = get_list_of_valid_providers()
        providers.insert(0, (self.HINT["provider"], None))
        if self.debug:
            from optimade_client.utils import VERSION_PARTS

            local_provider = LinksResourceAttributes(
                **{
                    "name": "Local server",
                    "description": "Local server, running aiida-optimade",
                    "base_url": f"http://localhost:5000{VERSION_PARTS[0][0]}",
                    "homepage": "https://example.org",
                    "link_type": "external",
                }
            )
            providers.insert(1, ("Local server", local_provider))

        self.providers = DropdownExtended(
            options=providers,
            disabled_options=invalid_providers,
            layout=dropdown_layout,
        )
        self.child_dbs = ipw.Dropdown(
            options=self.INITIAL_CHILD_DBS, layout=dropdown_layout, disabled=True
        )
        self.page_chooser = ResultsPageChooser(self.child_db_limit, **kwargs)

        self.providers.observe(self._observe_providers, names="index")
        self.child_dbs.observe(self._observe_child_dbs, names="index")
        self.page_chooser.observe(
            self._get_more_child_dbs, names=["page_link", "page_offset", "page_number"]
        )
        self.error_or_status_messages = ipw.HTML("")

        super().__init__(
            children=(
                self.providers,
                self.child_dbs,
                self.page_chooser,
                self.error_or_status_messages,
            ),
            layout=ipw.Layout(width="auto"),
            **kwargs,
        )

    def freeze(self):
        """Disable widget"""
        self.providers.disabled = True
        self.child_dbs.disabled = True
        self.page_chooser.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.providers.disabled = False
        self.child_dbs.disabled = False
        self.page_chooser.unfreeze()

    def reset(self):
        """Reset widget"""
        self.page_chooser.reset()
        self.offset = 0
        self.number = 1

        self.providers.index = 0
        self.providers.disabled = False

        self.child_dbs.options = self.INITIAL_CHILD_DBS
        self.child_dbs.disabled = True

    def _observe_providers(self, change: dict):
        """Update child database dropdown upon changing provider"""
        index = change["new"]
        self.child_dbs.disabled = True
        self.provider = self.providers.value
        if index is None or self.providers.value is None:
            self.child_dbs.options = self.INITIAL_CHILD_DBS
            self.child_dbs.disabled = True
            self.providers.index = 0
            self.child_dbs.index = 0
        else:
            self._initialize_child_dbs()
            if len(self.child_dbs.options) <= 2:
                # The provider either has 0 or 1 implementations
                # or we have failed to retrieve any implementations.
                # Automatically choose the 1 implementation (if there),
                # while otherwise keeping the dropdown disabled.
                self.child_dbs.disabled = True
                try:
                    self.child_dbs.index = 1
                except IndexError:
                    pass
            else:
                self.child_dbs.disabled = False

    def _observe_child_dbs(self, change):
        """Update database traitlet with base URL for chosen child database"""
        index = change["new"]
        if index is None or not self.child_dbs.options[index][1]:
            self.database = "", None
        else:
            self.database = self.child_dbs.options[index]

    @staticmethod
    def _remove_current_dropdown_option(dropdown: ipw.Dropdown) -> tuple:
        """Remove the current option from a Dropdown widget and return updated options

        Since Dropdown.options is a tuple there is a need to go through a list.
        """
        list_of_options = list(dropdown.options)
        list_of_options.pop(dropdown.index)
        return tuple(list_of_options)

    def _initialize_child_dbs(self):
        """New provider chosen; initialize child DB dropdown"""
        self.offset = 0
        self.number = 1
        try:
            # Freeze and disable list of structures in dropdown widget
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Reset the error or status message
            if self.error_or_status_messages.value:
                self.error_or_status_messages.value = ""

            if self.provider.base_url in self.__cached_child_dbs:
                cache = self.__cached_child_dbs[self.provider.base_url]

                LOGGER.debug(
                    "Initializing child DBs for %s. Using cached info:\n%r",
                    self.provider.name,
                    cache,
                )

                self._set_child_dbs(cache["child_dbs"])
                data_returned = cache["data_returned"]
                data_available = cache["data_available"]
                links = cache["links"]
            else:
                LOGGER.debug("Initializing child DBs for %s.", self.provider.name)

                # Query database and get child_dbs
                child_dbs, links, data_returned, data_available = self._query()

                while True:
                    # Update list of structures in dropdown widget
                    exclude_child_dbs, final_child_dbs = self._update_child_dbs(
                        child_dbs
                    )

                    LOGGER.debug("Exclude child DBs: %r", exclude_child_dbs)
                    data_returned -= len(exclude_child_dbs)
                    if exclude_child_dbs and data_returned:
                        child_dbs, links, data_returned, _ = self._query(
                            exclude_ids=exclude_child_dbs
                        )
                    else:
                        break
                self._set_child_dbs(final_child_dbs)

                # Cache initial child_dbs and related information
                self.__cached_child_dbs[self.provider.base_url] = {
                    "child_dbs": final_child_dbs,
                    "data_returned": data_returned,
                    "data_available": data_available,
                    "links": links,
                }

                LOGGER.debug(
                    "Found the following, which has now been cached:\n%r",
                    self.__cached_child_dbs[self.provider.base_url],
                )

            # Update pageing
            self.page_chooser.set_pagination_data(
                data_returned=data_returned,
                data_available=data_available,
                links_to_page=links,
                reset_cache=True,
            )

        except QueryError as exc:
            LOGGER.debug("Trying to initalize child DBs. QueryError caught: %r", exc)
            if exc.remove_target:
                LOGGER.debug(
                    "Remove target: %r. Will remove target at %r: %r",
                    exc.remove_target,
                    self.providers.index,
                    self.providers.value,
                )
                self.providers.options = self._remove_current_dropdown_option(
                    self.providers
                )
                self.reset()
            else:
                LOGGER.debug(
                    "Remove target: %r. Will NOT remove target at %r: %r",
                    exc.remove_target,
                    self.providers.index,
                    self.providers.value,
                )
                self.child_dbs.options = self.INITIAL_CHILD_DBS
                self.child_dbs.disabled = True

        else:
            self.unfreeze()

    def _set_child_dbs(self, data: List[Tuple[str, LinksResourceAttributes]]):
        """Update the child_dbs options with `data`"""
        first_choice = (
            self.HINT["child_dbs"] if data else "No valid implementations found"
        )
        new_data = list(data)
        new_data.insert(0, (first_choice, {}))
        self.child_dbs.options = new_data
        with self.hold_trait_notifications():
            self.child_dbs.index = 0

    @staticmethod
    def _update_child_dbs(data: List[dict]) -> Tuple[List[str], List[LinksResource]]:
        """Update child DB dropdown from response data"""
        child_dbs = []
        exclude_dbs = []

        for entry in data:
            child_db = update_old_links_resources(entry)
            if child_db is None:
                continue

            attributes = child_db.attributes

            # Skip if not a 'child' link_type database
            if attributes.link_type != LinkType.CHILD:
                LOGGER.debug(
                    "Skip %s: Links resource not a %r link_type, instead: %r",
                    attributes.name,
                    LinkType.CHILD,
                    attributes.link_type,
                )
                continue

            # Skip if there is no base_url
            if attributes.base_url is None:
                LOGGER.debug(
                    "Skip %s: Base URL found to be None for child DB: %r",
                    attributes.name,
                    child_db,
                )
                exclude_dbs.append(child_db.id)
                continue

            versioned_base_url = get_versioned_base_url(attributes.base_url)
            if versioned_base_url:
                attributes.base_url = versioned_base_url
            else:
                # Not a valid/supported child DB: skip
                LOGGER.debug(
                    "Skip %s: Could not determine versioned base URL for child DB: %r",
                    attributes.name,
                    child_db,
                )
                exclude_dbs.append(child_db.id)
                continue

            child_dbs.append((attributes.name, attributes))

        return exclude_dbs, child_dbs

    def _get_more_child_dbs(self, change):
        """Query for more child DBs according to page_offset"""
        if self.providers.value is None:
            # This may be called if a provider is suddenly removed (bad provider)
            return

        if not self.__perform_query:
            self.__perform_query = True
            LOGGER.debug(
                "Will not perform query with pageing: name=%s value=%s",
                change["name"],
                change["new"],
            )
            return

        pageing: Union[int, str] = change["new"]
        LOGGER.debug(
            "Detected change in page_chooser: name=%s value=%s",
            change["name"],
            pageing,
        )
        if change["name"] == "page_offset":
            LOGGER.debug(
                "Got offset %d to retrieve more child DBs from %r",
                pageing,
                self.providers.value,
            )
            self.offset = pageing
            pageing = None
        elif change["name"] == "page_number":
            LOGGER.debug(
                "Got number %d to retrieve more child DBs from %r",
                pageing,
                self.providers.value,
            )
            self.number = pageing
            pageing = None
        else:
            LOGGER.debug(
                "Got link %r to retrieve more child DBs from %r",
                pageing,
                self.providers.value,
            )
            # It is needed to update page_offset, but we do not wish to query again
            with self.hold_trait_notifications():
                self.__perform_query = False
                self.page_chooser.update_offset()

        try:
            # Freeze and disable both dropdown widgets
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Query index meta-database
            LOGGER.debug("Querying for more child DBs using pageing: %r", pageing)
            child_dbs, links, _, _ = self._query(pageing)

            data_returned = self.page_chooser.data_returned
            while True:
                # Update list of structures in dropdown widget
                exclude_child_dbs, final_child_dbs = self._update_child_dbs(child_dbs)

                data_returned -= len(exclude_child_dbs)
                if exclude_child_dbs and data_returned:
                    child_dbs, links, data_returned, _ = self._query(
                        link=pageing, exclude_ids=exclude_child_dbs
                    )
                else:
                    break
            self._set_child_dbs(final_child_dbs)

            # Update pageing
            self.page_chooser.set_pagination_data(
                data_returned=data_returned, links_to_page=links
            )

        except QueryError as exc:
            LOGGER.debug(
                "Trying to retrieve more child DBs (new page). QueryError caught: %r",
                exc,
            )
            if exc.remove_target:
                LOGGER.debug(
                    "Remove target: %r. Will remove target at %r: %r",
                    exc.remove_target,
                    self.providers.index,
                    self.providers.value,
                )
                self.providers.options = self._remove_current_dropdown_option(
                    self.providers
                )
                self.reset()
            else:
                LOGGER.debug(
                    "Remove target: %r. Will NOT remove target at %r: %r",
                    exc.remove_target,
                    self.providers.index,
                    self.providers.value,
                )
                self.child_dbs.options = self.INITIAL_CHILD_DBS
                self.child_dbs.disabled = True

        else:
            self.unfreeze()

    def _query(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self, link: str = None, exclude_ids: List[str] = None
    ) -> Tuple[List[dict], dict, int, int]:
        """Query helper function"""
        # If a complete link is provided, use it straight up
        if link is not None:
            try:
                if exclude_ids:
                    filter_value = " AND ".join([f"id!={id_}" for id_ in exclude_ids])

                    parsed_url = urllib.parse.urlparse(link)
                    queries = urllib.parse.parse_qs(parsed_url.query)
                    # Since parse_qs wraps all values in a list,
                    # this extracts the values from the list(s).
                    queries = {key: value[0] for key, value in queries.items()}

                    if "filter" in queries:
                        queries[
                            "filter"
                        ] = f"( {queries['filter']} ) AND ( {filter_value} )"
                    else:
                        queries["filter"] = filter_value

                    parsed_query = urllib.parse.urlencode(queries)

                    link = (
                        f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        f"?{parsed_query}"
                    )

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
            except json.JSONDecodeError as exc:
                response = {
                    "errors": {
                        "msg": "CLIENT: Could not decode response to JSON.",
                        "url": link,
                        "Exception": repr(exc),
                    }
                }
        else:
            filter_ = "link_type=child OR type=child"
            if exclude_ids:
                filter_ += (
                    " AND ( "
                    + " AND ".join([f"id!={id_}" for id_ in exclude_ids])
                    + " )"
                )

            response = perform_optimade_query(
                filter=filter_,
                base_url=self.provider.base_url,
                endpoint="/links",
                page_limit=self.child_db_limit,
                page_offset=self.offset,
                page_number=self.number,
            )
        msg, http_errors = handle_errors(response)
        if msg:
            if 404 in http_errors:
                # If /links not found move on
                pass
            else:
                self.error_or_status_messages.value = msg
                raise QueryError(msg=msg, remove_target=True)

        # Check implementation API version
        msg = validate_api_version(
            response.get("meta", {}).get("api_version", ""), raise_on_fail=False
        )
        if msg:
            self.error_or_status_messages.value = (
                f"{msg}<br>The provider has been removed."
            )
            raise QueryError(msg=msg, remove_target=True)

        LOGGER.debug("Manually remove `exclude_ids` if filters are not supported")
        child_db_data = {
            impl.get("id", "N/A"): impl for impl in response.get("data", [])
        }
        if exclude_ids:
            for links_id in exclude_ids:
                if links_id in list(child_db_data.keys()):
                    child_db_data.pop(links_id)
            LOGGER.debug("child_db_data after popping: %r", child_db_data)
            response["data"] = list(child_db_data.values())
            if "meta" in response:
                if "data_available" in response["meta"]:
                    old_data_available = response["meta"].get("data_available", 0)
                    if len(response["data"]) > old_data_available:
                        LOGGER.debug("raising OptimadeClientError")
                        raise OptimadeClientError(
                            f"Reported data_available ({old_data_available}) is smaller than "
                            f"curated list of responses ({len(response['data'])}).",
                        )
                response["meta"]["data_available"] = len(response["data"])
            else:
                raise OptimadeClientError("'meta' not found in response. Bad response")

        LOGGER.debug(
            "Attempt for %r (in /links): Found implementations (names+base_url only):\n%s",
            self.provider.name,
            [
                f"(id: {name}; base_url: {base_url}) "
                for name, base_url in [
                    (
                        impl.get("id", "N/A"),
                        impl.get("attributes", {}).get("base_url", "N/A"),
                    )
                    for impl in response.get("data", [])
                ]
            ],
        )
        # Return all implementations of link_type "child"
        implementations = [
            implementation
            for implementation in response.get("data", [])
            if (
                implementation.get("attributes", {}).get("link_type", "") == "child"
                or implementation.get("type", "") == "child"
            )
        ]
        LOGGER.debug(
            "After curating for implementations which are of 'link_type' = 'child' or 'type' == "
            "'child' (old style):\n%s",
            [
                f"(id: {name}; base_url: {base_url}) "
                for name, base_url in [
                    (
                        impl.get("id", "N/A"),
                        impl.get("attributes", {}).get("base_url", "N/A"),
                    )
                    for impl in implementations
                ]
            ],
        )

        # Get links, data_returned, and data_available
        links = response.get("links", {})
        data_returned = response.get("meta", {}).get(
            "data_returned", len(implementations)
        )
        if data_returned > 0 and not implementations:
            # Most probably dealing with pre-v1.0.0-rc.2 implementations
            data_returned = 0
        data_available = response.get("meta", {}).get("data_available", 0)

        return implementations, links, data_returned, data_available


class ProviderImplementationSummary(ipw.GridspecLayout):
    """Summary/description of chosen provider and their database"""

    provider = traitlets.Instance(LinksResourceAttributes, allow_none=True)
    database = traitlets.Instance(LinksResourceAttributes, allow_none=True)

    text_style = "margin:0px;padding-top:6px;padding-bottom:4px;padding-left:4px;padding-right:4px;"

    def __init__(self, **kwargs):
        self.provider_summary = ipw.HTML()
        provider_section = ipw.VBox(
            children=[self.provider_summary],
            layout=ipw.Layout(width="auto", height="auto"),
        )

        self.database_summary = ipw.HTML()
        database_section = ipw.VBox(
            children=[self.database_summary],
            layout=ipw.Layout(width="auto", height="auto"),
        )

        super().__init__(
            n_rows=1,
            n_columns=31,
            layout={
                "border": "solid 0.5px darkgrey",
                "margin": "0px 0px 0px 0px",
                "padding": "0px 0px 10px 0px",
            },
            **kwargs,
        )
        self[:, :15] = provider_section
        self[:, 16:] = database_section

        self.observe(self._on_provider_change, names="provider")
        self.observe(self._on_database_change, names="database")

    def _on_provider_change(self, change: dict):
        """Update provider summary, since self.provider has been changed"""
        LOGGER.debug("Provider changed in summary. New value: %r", change["new"])
        self.database_summary.value = ""
        if not change["new"] or change["new"] is None:
            self.provider_summary.value = ""
        else:
            self._update_provider()

    def _on_database_change(self, change):
        """Update database summary, since self.database has been changed"""
        LOGGER.debug("Database changed in summary. New value: %r", change["new"])
        if not change["new"] or change["new"] is None:
            self.database_summary.value = ""
        else:
            self._update_database()

    def _update_provider(self):
        """Update provider summary"""
        html_text = f"""<strong style="line-height:1;{self.text_style}">{getattr(self.provider, 'name', 'Provider')}</strong>
<p style="line-height:1.2;{self.text_style}">{getattr(self.provider, 'description', '')}</p>"""
        self.provider_summary.value = html_text

    def _update_database(self):
        """Update database summary"""
        html_text = f"""<strong style="line-height:1;{self.text_style}">{getattr(self.database, 'name', 'Database')}</strong>
<p style="line-height:1.2;{self.text_style}">{getattr(self.database, 'description', '')}</p>"""
        self.database_summary.value = html_text

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.provider = None
