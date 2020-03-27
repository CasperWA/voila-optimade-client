from typing import Union
import traitlets
import ipywidgets as ipw

from aiidalab_optimade.subwidgets import (
    ProviderImplementationChooser,
    ProviderImplementationSummary,
    ResultsPageChooser,
)
from aiidalab_optimade.utils import handle_errors


DEFAULT_FILTER_VALUE = (
    'chemical_formula_descriptive CONTAINS "Al" OR (chemical_formula_anonymous = "AB" AND '
    'elements HAS ALL "Si","Al","O")'
)


class OptimadeQueryProviderWidget(ipw.GridspecLayout):
    """Database/Implementation search and chooser widget for OPTIMADE

    NOTE: Only supports offset-pagination at the moment.
    """

    database = traitlets.Tuple(
        traitlets.Unicode(), traitlets.Dict(allow_none=True), default_value=("", None)
    )

    def __init__(
        self,
        debug: bool = False,
        embedded: bool = False,
        database_limit: int = None,
        **kwargs
    ):
        self.debug = debug
        self.page_limit = (
            database_limit if database_limit and database_limit > 0 else 10
        )
        self.offset = 0

        layout = ipw.Layout(width="100%", height="auto")

        self.chooser = ProviderImplementationChooser(debug=self.debug, **kwargs)
        self.page_chooser = ResultsPageChooser(self.page_limit, **kwargs)

        self.summary = ProviderImplementationSummary(**kwargs) if not embedded else None

        if embedded:
            super().__init__(n_rows=2, n_columns=1, layout=layout, **kwargs)
            self[0, :] = self.chooser
            self[1, :] = self.page_chooser
        else:
            super().__init__(n_rows=2, n_columns=31, layout=layout, **kwargs)
            self[0, :10] = self.chooser
            self[1, :10] = self.page_chooser
            self[:, 11:] = self.summary

            ipw.dlink((self.chooser, "provider"), (self.summary, "provider"))
            ipw.dlink(
                (self.chooser, "database"),
                (self.summary, "database"),
                transform=(lambda db: db[1] if db and db is not None else None),
            )

        ipw.dlink((self.chooser, "database"), (self, "database"))
        # self.page_chooser.observe(
        #     self._get_more_databases, names=["page_offset", "page_link"]
        # )

    def _get_more_databases(self, change):
        """Query for more databases according to page_offset"""
        offset_or_link: Union[int, str] = change["new"]
        if isinstance(offset_or_link, int):
            self.offset = offset_or_link
            offset_or_link = None

        try:
            # Freeze and disable both dropdown widgets
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Query index meta-database
            # response = self._query(offset_or_link)
            response = {}
            msg = handle_errors(response, self.debug)
            if msg:
                if self.debug:
                    print(msg)
                return

            # Update list of databases in dropdown widget
            # self._update_databases(response["data"])

            # Update pageing
            self.page_chooser.set_pagination_data(
                links_to_page=response.get("links", {}),
            )

        finally:
            self.unfreeze()

    def freeze(self):
        """Disable widget"""
        for widget in self.children:
            widget.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for widget in self.children:
            widget.unfreeze()

    def reset(self):
        """Reset widget"""
        for widget in self.children:
            widget.reset()
