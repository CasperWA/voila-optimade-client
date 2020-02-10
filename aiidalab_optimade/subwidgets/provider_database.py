import ipywidgets as ipw
import traitlets

from aiidalab_optimade.utils import (
    get_list_of_valid_providers,
    get_list_of_provider_implementations,
)


__all__ = ("ProvidersImplementations",)


class ProviderImplementationChooser(ipw.VBox):
    """List all OPTiMaDe providers and their implementations"""

    provider = traitlets.Dict(allow_none=True)
    database = traitlets.Tuple(traitlets.Unicode(), traitlets.Dict(allow_none=True))

    HINT = {"provider": "Select a provider", "child_dbs": "Select a database"}
    NO_OPTIONS = "No provider chosen"

    def __init__(self, **kwargs):
        providers = get_list_of_valid_providers()
        providers.insert(0, (self.HINT["provider"], None))
        implementations = [(self.NO_OPTIONS, None)]

        self.providers = ipw.Dropdown(options=providers)
        self.child_dbs = ipw.Dropdown(options=implementations, disabled=True)

        self.providers.observe(self._observe_providers, names="index")
        self.child_dbs.observe(self._observe_child_dbs, names="index")

        super().__init__(
            children=[self.providers, self.child_dbs],
            layout=ipw.Layout(width="auto"),
            **kwargs,
        )

    def _observe_providers(self, change):
        """Update child database dropdown upon changing provider"""
        index = change["new"]
        if index is None or self.providers.options[index][1] is None:
            self.child_dbs.options = [(self.NO_OPTIONS, None)]
            self.child_dbs.disabled = True
            with self.hold_trait_notifications():
                self.providers.index = 0
                self.child_dbs.index = 0
        else:
            self.provider = self.providers.options[index][1]
            implementations = get_list_of_provider_implementations(self.provider)
            implementations.insert(0, (self.HINT["child_dbs"], None))
            self.child_dbs.options = implementations
            self.child_dbs.disabled = False
            with self.hold_trait_notifications():
                self.child_dbs.index = 0

    def _observe_child_dbs(self, change):
        """Update database traitlet with base URL for chosen child database"""
        index = change["new"]
        if index is None or self.child_dbs.options[index][1] is None:
            self.database = "", None
        else:
            self.database = self.child_dbs.options[index]

    def freeze(self):
        """Disable widget"""
        self.providers.disabled = True
        self.child_dbs.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.providers.disabled = False
        self.child_dbs.disabled = False

    def reset(self):
        """Reset widget"""
        with self.hold_trait_notifications():
            self.providers.index = 0
            self.providers.disabled = False

            self.child_dbs.options = [(self.NO_OPTIONS, None)]
            self.child_dbs.disabled = True


class ProviderImplementationSummary(ipw.GridspecLayout):
    """Summary/description of chosen provider and their database"""

    provider = traitlets.Dict(allow_none=True)
    database = traitlets.Dict(allow_none=True)

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

        super().__init__(n_rows=1, n_columns=7, **kwargs)
        self[:, :3] = provider_section
        self[:, 4:] = database_section

        self.observe(self._update_provider_summary, names="provider")
        self.observe(self._update_database_summary, names="database")

    def _update_provider_summary(self, change):
        """Update provider summary"""
        new_provider = change["new"]
        if new_provider is None:
            self.provider_summary.value = None
            self.database_summary.value = None

    def _update_database_summary(self, change):
        """Update database summary"""

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.provider = None


class ProvidersImplementations(ipw.GridspecLayout):
    """Combining chooser and summary widgets"""

    database = traitlets.Tuple(traitlets.Unicode(), traitlets.Dict(allow_none=True))

    def __init__(self, include_summary: bool = False, **kwargs):
        self.summary_included = include_summary

        self.chooser = ProviderImplementationChooser()

        self.sections = [self.chooser]
        if self.summary_included:
            self.summary = ProviderImplementationSummary()
            self.sections.append(self.summary)

        if self.summary_included:
            super().__init__(n_rows=3, n_columns=15, **kwargs)
            self[1, :5] = self.chooser
            self[:, 7:] = self.summary
        else:
            super().__init__(n_rows=1, n_columns=1, **kwargs)
            self[:, :] = self.chooser

        self.chooser.observe(self._update_database, names="database")
        if self.summary_included:
            self.chooser.observe(self._update_provider, names="provider")

    def _update_database(self, change):
        """Patch database through to own traitlet and pass info to summary"""
        self.database = change["new"]
        if self.summary_included:
            self.summary.database = self.database[1]

    def _update_provider(self, change):
        """Pass information to summary"""
        self.summary.provider = change["new"]

    def freeze(self):
        """Disable widget"""
        for widget in self.sections:
            widget.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for widget in self.sections:
            widget.unfreeze()

    def reset(self):
        """Reset widget"""
        for widget in self.sections:
            widget.reset()
