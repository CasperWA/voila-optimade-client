import ipywidgets as ipw

from widget_periodictable import PTableWidget

from aiidalab_optimade.logger import LOGGER


__all__ = ("PeriodicTable",)


class PeriodicTable(ipw.VBox):
    """Wrapper-widget for PTableWidget"""

    def __init__(self, **kwargs):
        layout = kwargs.pop("layout", None)
        if layout is None:
            layout = ipw.Layout(width="auto")

        self.select_any_all = ipw.Checkbox(
            value=False, description="Exclude all unselected elements",
        )
        self.ptable = PTableWidget(**kwargs)

        super().__init__(
            children=(self.select_any_all, self.ptable), layout=layout,
        )

    @property
    def value(self) -> dict:
        """Return value for wrapped PTableWidget"""
        LOGGER.debug(
            "PeriodicTable: PTableWidget.selected_elements = %r",
            self.ptable.selected_elements,
        )
        LOGGER.debug("PeriodicTable: Select ANY or ALL = %r", self.select_any_all.value)

        return self.select_any_all.value, self.ptable.selected_elements.copy()
