import ipywidgets as ipw

from widget_periodictable import PTableWidget

from optimade_client.logger import LOGGER
from optimade_client.utils import ButtonStyle


__all__ = ("PeriodicTable",)


class PeriodicTable(ipw.VBox):
    """Wrapper-widget for PTableWidget"""

    def __init__(self, extended: bool = True, **kwargs):
        self._disabled = kwargs.get("disabled", False)

        self.toggle_button = ipw.ToggleButton(
            value=extended,
            description="Hide Periodic Table" if extended else "Show Periodic Table",
            button_style=ButtonStyle.INFO.value,
            icon="flask",
            tooltip="Hide Periodic Table" if extended else "Show Periodic Table",
            layout={"width": "auto"},
        )
        self.select_any_all = ipw.Checkbox(
            value=False,
            description="Structures can include any chosen elements (instead of all)",
            indent=False,
            layout={"width": "auto"},
            disabled=self.disabled,
        )
        self.ptable = PTableWidget(**kwargs)
        self.ptable_container = ipw.VBox(
            children=(self.select_any_all, self.ptable),
            layout={
                "width": "auto",
                "height": "auto" if extended else "0px",
                "visibility": "visible" if extended else "hidden",
            },
        )

        self.toggle_button.observe(self._toggle_widget, names="value")

        super().__init__(
            children=(self.toggle_button, self.ptable_container),
            layout=kwargs.get("layout", {}),
        )

    @property
    def value(self) -> dict:
        """Return value for wrapped PTableWidget"""
        LOGGER.debug(
            "PeriodicTable: PTableWidget.selected_elements = %r",
            self.ptable.selected_elements,
        )
        LOGGER.debug(
            "PeriodicTable: Select ANY (True) or ALL (False) = %r",
            self.select_any_all.value,
        )

        return not self.select_any_all.value, self.ptable.selected_elements.copy()

    @property
    def disabled(self) -> None:
        """Disable widget"""
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        """Disable widget"""
        if not isinstance(value, bool):
            raise TypeError("disabled must be a boolean")

        self.select_any_all.disabled = self.ptable.disabled = value

    def reset(self):
        """Reset widget"""
        self.select_any_all.value = False
        self.ptable.selected_elements = {}

    def freeze(self):
        """Disable widget"""
        self.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.disabled = False

    def _toggle_widget(self, change: dict):
        """Hide or show the widget according to the toggle button"""
        if change["new"]:
            # Show widget
            LOGGER.debug("Show widget since toggle is %s", change["new"])
            self.ptable_container.layout.visibility = "visible"
            self.ptable_container.layout.height = "auto"
            self.toggle_button.tooltip = "Hide Periodic Table"
            self.toggle_button.description = "Hide Periodic Table"
        else:
            # Hide widget
            LOGGER.debug("Hide widget since toggle is %s", change["new"])
            self.ptable_container.layout.visibility = "hidden"
            self.ptable_container.layout.height = "0px"
            self.toggle_button.tooltip = "Show Periodic Table"
            self.toggle_button.description = "Show Periodic Table"
