from typing import Union, Tuple, List, Dict, Optional
import warnings

import ipywidgets as ipw
import traitlets

from optimade.models import LinksResourceAttributes

from optimade_client.subwidgets import (
    ProviderImplementationChooser,
    ProviderImplementationSummary,
)
from optimade_client.warnings import OptimadeClientWarning
from optimade_client.default_parameters import (
    PROVIDER_DATABASE_GROUPINGS,
    SKIP_DATABASE,
    SKIP_PROVIDERS,
    DISABLE_PROVIDERS,
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
        database_limit: Optional[int] = None,
        width_ratio: Optional[Union[Tuple[int, int], List[int]]] = None,
        width_space: Optional[int] = None,
        disable_providers: Optional[List[str]] = None,
        skip_providers: Optional[List[str]] = None,
        skip_databases: Optional[List[str]] = None,
        provider_database_groupings: Optional[Dict[str, Dict[str, List[str]]]] = None,
        **kwargs,
    ):
        # At the moment, the pagination does not work properly as each database is not tested for
        # validity immediately, only when each "page" is loaded. This can result in the pagination
        # failing. Instead the default is set to 100 in an attempt to never actually do paging.
        database_limit = (
            database_limit if database_limit and database_limit > 0 else 100
        )
        disable_providers = disable_providers or DISABLE_PROVIDERS
        skip_providers = skip_providers or SKIP_PROVIDERS
        skip_databases = skip_databases or SKIP_DATABASE
        provider_database_groupings = (
            provider_database_groupings or PROVIDER_DATABASE_GROUPINGS
        )

        layout = ipw.Layout(width="100%", height="auto")

        self.chooser = ProviderImplementationChooser(
            child_db_limit=database_limit,
            disable_providers=disable_providers,
            skip_providers=skip_providers,
            skip_databases=skip_databases,
            provider_database_groupings=provider_database_groupings,
            **kwargs,
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
