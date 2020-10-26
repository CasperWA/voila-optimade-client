import warnings

import ipywidgets as ipw
import traitlets
from typing import Union, Tuple, List

from optimade.models import LinksResourceAttributes

from optimade_client.subwidgets import (
    ProviderImplementationChooser,
    ProviderImplementationSummary,
)
from optimade_client.warnings import OptimadeClientWarning


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

    def __init__(
        self,
        embedded: bool = False,
        database_limit: int = None,
        width_ratio: Union[Tuple[int, int], List[int]] = None,
        width_space: int = None,
        **kwargs,
    ):
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
            if width_ratio is not None and isinstance(width_ratio, (tuple, list)):
                if len(width_ratio) != 2 or sum(width_ratio) <= 0:
                    width_ratio = (10, 21)
                    warnings.warn(
                        "width_ratio is not a list or tuple of length 2. "
                        f"Will use defaults {width_ratio}.",
                        OptimadeClientWarning,
                    )
            else:
                width_ratio = (10, 21)

            width_space = width_space if width_space is not None else 1

            super().__init__(
                n_rows=1, n_columns=sum(width_ratio), layout=layout, **kwargs
            )
            self[:, : width_ratio[0]] = self.chooser
            self[:, width_ratio[0] + width_space :] = self.summary

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
