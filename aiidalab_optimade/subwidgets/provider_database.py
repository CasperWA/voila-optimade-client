import os
from typing import List, Tuple, Union

try:
    import simplejson as json
except ImportError:
    import json

import ipywidgets as ipw
import requests
import traitlets

from optimade.models import LinksResourceAttributes, ChildResource

from aiidalab_optimade.exceptions import QueryError
from aiidalab_optimade.logger import LOGGER
from aiidalab_optimade.subwidgets.results import ResultsPageChooser
from aiidalab_optimade.utils import (
    get_list_of_valid_providers,
    get_versioned_base_url,
    handle_errors,
    perform_optimade_query,
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
    NO_OPTIONS = "No provider chosen"

    def __init__(self, child_db_limit: int = None, **kwargs):
        self.child_db_limit = (
            child_db_limit if child_db_limit and child_db_limit > 0 else 10
        )
        self.offset = 0
        self.__perform_query = True

        self.debug = bool(os.environ.get("OPTIMADE_CLIENT_DEBUG", None))

        dropdown_layout = ipw.Layout(width="auto")

        providers = []
        providers = get_list_of_valid_providers()
        providers.insert(0, (self.HINT["provider"], None))
        if self.debug:
            from aiidalab_optimade.utils import __optimade_version__

            local_provider = {
                "name": "Local server",
                "description": "Local server, running aiida-optimade",
                "base_url": f"http://localhost:5000/optimade/v{__optimade_version__.split('.')[0]}",
                "homepage": "https://example.org",
            }
            providers.insert(1, ("Local server", local_provider))
        implementations = [(self.NO_OPTIONS, None)]

        self.providers = ipw.Dropdown(options=providers, layout=dropdown_layout)
        self.child_dbs = ipw.Dropdown(
            options=implementations, layout=dropdown_layout, disabled=True
        )
        self.page_chooser = ResultsPageChooser(self.child_db_limit, **kwargs)

        self.providers.observe(self._observe_providers, names="index")
        self.child_dbs.observe(self._observe_child_dbs, names="index")
        self.page_chooser.observe(
            self._get_more_child_dbs, names=["page_offset", "page_link"]
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
        with self.hold_trait_notifications():
            self.providers.index = 0
            self.providers.disabled = False

            self.child_dbs.options = [(self.NO_OPTIONS, None)]
            self.child_dbs.disabled = True

    def _observe_providers(self, change):
        """Update child database dropdown upon changing provider"""
        index = change["new"]
        self.child_dbs.disabled = True
        if index is None or self.providers.value is None:
            self.child_dbs.options = [(self.NO_OPTIONS, None)]
            self.child_dbs.disabled = True
            with self.hold_trait_notifications():
                self.providers.index = 0
                self.child_dbs.index = 0
        else:
            self.provider = self.providers.value
            self._initialize_child_dbs()
            self.child_dbs.disabled = False

    def _observe_child_dbs(self, change):
        """Update database traitlet with base URL for chosen child database"""
        index = change["new"]
        if index is None or not self.child_dbs.options[index][1]:
            self.database = "", None
        else:
            self.database = self.child_dbs.options[index]

    def _initialize_child_dbs(self):
        """New provider chosen; initialize child DB dropdown"""
        self.offset = 0
        try:
            # Freeze and disable list of structures in dropdown widget
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Reset the error or status message
            if self.error_or_status_messages.value:
                self.error_or_status_messages.value = ""

            # Query database and get child_dbs
            child_dbs, links, data_returned = self._query()

            # Update list of structures in dropdown widget
            self._update_child_dbs(child_dbs)

            # Update pageing
            self.page_chooser.set_pagination_data(
                data_returned=data_returned, links_to_page=links, reset_cache=True
            )

        except QueryError as exc:
            if exc.remove_target:
                with self.hold_trait_notifications():
                    self.providers.options.pop(self.providers.index, None)
                self.reset()
            else:
                with self.hold_trait_notifications():
                    self.child_dbs.options = [(self.NO_OPTIONS, None)]
                    self.child_dbs.disabled = True

        finally:
            self.unfreeze()

    def _set_child_dbs(self, data: List[Tuple[str, LinksResourceAttributes]]):
        """Update the child_dbs options with `data`"""
        data.insert(0, (self.HINT["child_dbs"], {}))
        self.child_dbs.options = data
        with self.hold_trait_notifications():
            self.child_dbs.index = 0

    def _update_child_dbs(self, data: List[dict]):
        """Update child DB dropdown from response data"""
        child_dbs = []

        for entry in data:
            child_db = ChildResource(**entry)

            attributes = child_db.attributes

            # Skip if there is no base_url
            if attributes.base_url is None:
                LOGGER.debug(
                    "Base URL found to be None for child DB: %s", str(child_db)
                )
                continue

            versioned_base_url = get_versioned_base_url(attributes.base_url)
            if versioned_base_url:
                attributes.base_url = versioned_base_url
            else:
                # Not a valid/supported child DB: skip
                LOGGER.debug(
                    "Could not determine versioned base URL for child DB: %s",
                    str(child_db),
                )
                continue

            child_dbs.append((attributes.name, attributes))

        self._set_child_dbs(child_dbs)

    def _get_more_child_dbs(self, change):
        """Query for more child DBs according to page_offset"""
        offset_or_link: Union[int, str] = change["new"]
        LOGGER.debug(
            "Detected change in page_chooser.page_offset or .page_link: %s, type: %s",
            str(offset_or_link),
            type(offset_or_link),
        )
        if isinstance(offset_or_link, int):
            LOGGER.debug("Got offset %d to retrieve more child DBs", offset_or_link)
            self.offset = offset_or_link
            offset_or_link = None
        else:
            LOGGER.debug("Got link %s to retrieve more child DBs", offset_or_link)
            # It is needed to update page_offset, but we do not wish to query again
            with self.hold_trait_notifications():
                self.__perform_query = False
                self.page_chooser.update_offset()

        if not self.__perform_query:
            self.__perform_query = True
            LOGGER.debug(
                "Will not perform query with offset_or_link: %s", str(offset_or_link)
            )
            return

        try:
            # Freeze and disable both dropdown widgets
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Query index meta-database
            LOGGER.debug(
                "Querying for more child DBs using offset_or_link: %s",
                str(offset_or_link),
            )
            child_dbs, links, _ = self._query(offset_or_link)

            # Update child DB dropdown widget
            self._update_child_dbs(child_dbs)

            # Update pageing
            self.page_chooser.set_pagination_data(links_to_page=links)

        except QueryError as exc:
            if exc.remove_target:
                with self.hold_trait_notifications():
                    self.providers.options.pop(self.providers.index, None)
                self.reset()
            else:
                with self.hold_trait_notifications():
                    self.child_dbs.options = [(self.NO_OPTIONS, None)]
                    self.child_dbs.disabled = True

        finally:
            self.unfreeze()

    def _query(self, link: str = None) -> Tuple[List[dict], dict, int]:
        """Query helper function"""
        # If a complete link is provided, use it straight up
        if link is not None:
            try:
                response = requests.get(link).json()
            except json.JSONDecodeError:
                response = {"errors": {}}
        else:
            response = perform_optimade_query(
                base_url=self.provider.base_url,
                endpoint="/links",
                page_limit=self.child_db_limit,
                page_offset=self.offset,
            )
        msg = handle_errors(response)
        if msg:
            self.error_or_status_messages.value = msg
            raise QueryError(remove_target=False)

        # Check implementation API version
        msg = validate_api_version(
            response.get("meta", {}).get("api_version", ""), raise_on_fail=False
        )
        if msg:
            self.error_or_status_messages.value = (
                f"{msg}.<br>The provider will be removed."
            )
            raise QueryError(remove_target=True)

        LOGGER.debug(
            "First attempt (in /links): Found implementations:\n%s",
            str(json.dumps(response.get("data", []), indent=2)),
        )
        # Return all implementations of type "child"
        implementations = [
            implementation
            for implementation in response.get("data", [])
            if implementation.get("type", "") == "child"
        ]

        # Get links and data_returned
        links = response.get("links", {})
        data_returned = response.get("meta", {}).get("data_returned", 0)

        # If there are no implementations, try if index meta-database == implementation database
        if not implementations:
            new_response = perform_optimade_query(
                base_url=self.provider.base_url, endpoint="/structures", page_limit=1
            )
            msg = handle_errors(new_response)
            if msg:
                self.error_or_status_messages.value = (
                    f"{msg}.<br>The provider will be removed."
                )
                raise QueryError(remove_target=True)

            if new_response:
                LOGGER.debug(
                    "Second attempt, checking if index db and implementation are the same: Success"
                )
                # Indeed, index meta-database == implementation database
                implementation = {
                    "id": "main_db",
                    "type": "child",
                    "attributes": self.provider.dict(),
                }
                implementation["attributes"]["name"] = "Main database"
                implementations = [implementation]
                data_returned = 1
            else:
                LOGGER.debug(
                    "Second attempt, checking if index db and implementation are the same: "
                    "Failure. Response:\n%s",
                    new_response.get("meta", {}),
                )

        return implementations, links, data_returned


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

    def _on_provider_change(self, change):
        """Update provider summary, since self.provider has been changed"""
        self.database_summary.value = ""
        if change["new"] is None:
            self.provider_summary.value = ""
        else:
            self._update_provider()

    def _on_database_change(self, change):
        """Update database summary, since self.database has been changed"""
        if change["new"] is None:
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
