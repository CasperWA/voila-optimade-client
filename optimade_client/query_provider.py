import ipywidgets as ipw
import traitlets

from optimade.models import LinksResourceAttributes

from optimade_client.subwidgets import (
    ProviderImplementationChooser,
    ProviderImplementationSummary,
)


DEFAULT_FILTER_VALUE = (
    'chemical_formula_descriptive CONTAINS "Al" OR (chemical_formula_anonymous = "AB" AND '
    'elements HAS ALL "Si","Al","O")'
)


class OptimadeQueryProviderWidget(ipw.GridspecLayout):
    """Database/Implementation search and chooser widget for OPTIMADE

    NOTE: Only supports offset-pagination at the moment.
    """

    database = traitlets.Tuple(
        traitlets.Unicode(),
        traitlets.Instance(LinksResourceAttributes, allow_none=True),
        default_value=("", None),
    )

    def __init__(self, embedded: bool = False, database_limit: int = None, **kwargs):
        database_limit = database_limit if database_limit and database_limit > 0 else 10

        layout = ipw.Layout(width="100%", height="auto")

        self.chooser = ProviderImplementationChooser(
            child_db_limit=database_limit, **kwargs
        )

        self.summary = ProviderImplementationSummary(**kwargs) if not embedded else None

        if embedded:
            super().__init__(n_rows=1, n_columns=1, layout=layout, **kwargs)
            self[:, :] = self.chooser
        else:
            super().__init__(n_rows=1, n_columns=31, layout=layout, **kwargs)
            self[:, :10] = self.chooser
            self[:, 11:] = self.summary

            ipw.dlink((self.chooser, "provider"), (self.summary, "provider"))
            ipw.dlink(
                (self.chooser, "database"),
                (self.summary, "database"),
                transform=(lambda db: db[1] if db and db is not None else None),
            )

        ipw.dlink((self.chooser, "database"), (self, "database"))

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
