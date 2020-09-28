import ipywidgets as ipw

from widget_periodictable import PTableWidget

from optimade_client.logger import LOGGER


__all__ = ("PeriodicTable",)


class PeriodicTable(ipw.VBox):
    """Wrapper-widget for PTableWidget"""

    def __init__(self, **kwargs):
        self._disabled = kwargs.get("disabled", False)

        self.select_any_all = ipw.Checkbox(
            value=False,
            description="Structure must ex-/include ALL chosen elements",
            indent=False,
            layout={"width": "auto"},
            disabled=kwargs.get("disabled", False),
        )
        self.ptable = PTableWidget(**kwargs)

        super().__init__(
            children=(self.select_any_all, self.ptable),
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
            "PeriodicTable: Select ANY (False) or ALL (True) = %r",
            self.select_any_all.value,
        )

        return self.select_any_all.value, self.ptable.selected_elements.copy()

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
