import ipywidgets as ipw
import traitlets

from aiidalab_optimade.utils import (
    get_list_of_valid_providers,
    get_list_of_provider_implementations,
)


__all__ = ("ProviderImplementationChooser", "ProviderImplementationSummary")


class ProviderImplementationChooser(ipw.VBox):
    """List all OPTIMADE providers and their implementations"""

    provider = traitlets.Dict(allow_none=True)
    database = traitlets.Tuple(
        traitlets.Unicode(), traitlets.Dict(allow_none=True), default_value=("", None)
    )

    HINT = {"provider": "Select a provider", "child_dbs": "Select a database"}
    NO_OPTIONS = "No provider chosen"

    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug

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
        self.child_dbs.disabled = True
        if index is None or self.providers.value is None:
            self.child_dbs.options = [(self.NO_OPTIONS, None)]
            self.child_dbs.disabled = True
            with self.hold_trait_notifications():
                self.providers.index = 0
                self.child_dbs.index = 0
        else:
            self.provider = self.providers.value
            implementations = get_list_of_provider_implementations(self.provider)
            implementations.insert(0, (self.HINT["child_dbs"], None))
            self.child_dbs.options = implementations
            self.child_dbs.disabled = False
            with self.hold_trait_notifications():
                self.child_dbs.index = 0
        self.child_dbs.disabled = False

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
            n_rows=1, n_columns=31, layout={"border": "solid 0.5px"}, **kwargs
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
        html_text = f"""<h4 style="line-height:1;{self.text_style}">{self.provider.get('name', 'Provider')}</h4>
        <p style="line-height:1.2;{self.text_style}">{self.provider.get('description', '')}</p>"""
        self.provider_summary.value = html_text

    def _update_database(self):
        """Update database summary"""
        html_text = f"""<h4 style="line-height:1;{self.text_style}">{self.database.get('name', 'Database')}</h4>
        <p style="line-height:1.2;{self.text_style}">{self.database.get('description', '')}</p>"""
        self.database_summary.value = html_text

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.provider = None
