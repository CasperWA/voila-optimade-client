import traitlets
import ipywidgets as ipw

from aiidalab_optimade.utils import (
    get_list_of_valid_providers,
    get_list_of_provider_implementations,
)


class ProvidersImplementations(ipw.VBox):
    """List all OPTiMaDe providers and their implementations"""

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

        super().__init__(children=[self.providers, self.child_dbs], **kwargs)

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
            provider = self.providers.options[index][1]
            implementations = get_list_of_provider_implementations(provider)
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


class StructureDropdown(ipw.Dropdown):
    """From aiidalab-qe"""

    NO_OPTIONS = "Search for structures ..."
    HINT = "Select a structure"

    def __init__(self, options=None, **kwargs):
        if options is None:
            options = [(self.NO_OPTIONS, None)]
        else:
            options.insert(0, (self.HINT, None))

        super().__init__(options=options, **kwargs)

    def set_options(self, options):
        """Set options with hint at top/as first entry"""
        self.options = options
        self.options.insert(0, (self.HINT, None))

    def reset(self):
        """Reset widget"""
        with self.hold_trait_notifications():
            self.options = [(self.NO_OPTIONS, None)]
            self.index = 0
            self.disabled = True

    def freeze(self):
        """Disable widget"""
        self.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.disabled = False
