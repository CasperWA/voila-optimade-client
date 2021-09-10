# pylint: disable=no-self-use,too-many-instance-attributes
from enum import Enum
from typing import List, Union

import ipywidgets as ipw
from traitlets import traitlets


__all__ = ("SortSelector",)


class Order(Enum):
    """Sort order"""

    ASCENDING = ""
    DESCENDING = "-"


class SortSelector(ipw.HBox):
    """Select what to sort results by, the order, and a button to sort.

    The "Sort" button will only be enabled if the the sorting field or order is changed.
    """

    NO_AVAILABLE_FIELDS = "Not available"
    DEFAULT_FIELD = "id"

    field = traitlets.Unicode("", allow_none=False)
    order = traitlets.UseEnum(Order, default_value=Order.ASCENDING)
    latest_sorting = traitlets.Dict(
        default_value={"field": None, "order": order.default_value}
    )
    valid_fields = traitlets.List(
        traitlets.Unicode(), default_value=[], allow_none=True
    )

    value = traitlets.Unicode(None, allow_none=True)

    def __init__(
        self,
        valid_fields: List[str] = None,
        field: str = None,
        order: Union[str, Order] = None,
        disabled: bool = False,
        **kwargs,
    ) -> None:
        self._disabled = disabled

        try:
            self.order = order
        except traitlets.TraitError:
            # Use default
            pass

        self.order_select = ipw.ToggleButton(
            value=self.order == Order.DESCENDING,
            description=self.order.name.capitalize(),
            disabled=disabled,
            button_style="",
            tooltip=self.order.name.capitalize(),
            icon=self._get_order_icon(),
            layout={"width": "auto", "min_width": "105px"},
        )
        self.order_select.observe(self._change_order, names="value")

        self.fields_drop = ipw.Dropdown(
            options=self.valid_fields, disabled=disabled, layout={"width": "auto"}
        )
        self.fields_drop.observe(self._validate_field, names="value")

        self.sort_button = ipw.Button(
            description="Sort",
            disabled=True,
            button_style="primary",
            tooltip="Sort the results",
            icon="random",
            layout={"width": "auto"},
        )
        self.sort_button.on_click(self._sort_clicked)

        self.valid_fields = valid_fields or [self.NO_AVAILABLE_FIELDS]

        if field is not None:
            self.field = field

        super().__init__(
            children=(self.order_select, self.fields_drop, self.sort_button), **kwargs
        )

    @property
    def disabled(self) -> None:
        """Disable widget"""
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        """Disable widget"""
        if not isinstance(value, bool):
            raise TypeError("disabled must be a boolean")

        self.order_select.disabled = self.fields_drop.disabled = value

        if value:
            self.sort_button.disabled = True

    def reset(self):
        """Reset widget"""
        self.order_select.value = False
        self.fields_drop.options = [self.NO_AVAILABLE_FIELDS]
        self.sort_button.disabled = True

    def freeze(self):
        """Disable widget"""
        self.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.disabled = False

    def _update_latest_sorting(self) -> None:
        """Update `latest_sorting` with current values for `field` and `order`."""
        self.latest_sorting = {"field": self.field, "order": self.order}

    def _toggle_sort_availability(self) -> None:
        """Enable/Disable "Sort" button according to user choices."""
        for key, value in self.latest_sorting.items():
            if getattr(self, key) != value:
                self.sort_button.disabled = False
                break
        else:
            self.sort_button.disabled = True

    @traitlets.observe("valid_fields")
    def _update_drop_options(self, change: dict) -> None:
        """Update list of sort fields dropdown."""
        fields = change["new"]
        if not fields:
            self.fields_drop.options = [self.NO_AVAILABLE_FIELDS]
            self.fields_drop.value = self.NO_AVAILABLE_FIELDS
            self.freeze()
            return
        value = self.fields_drop.value
        self.fields_drop.options = fields
        if value in fields:
            self.fields_drop.value = value
        elif self.DEFAULT_FIELD in fields:
            self.fields_drop.value = self.DEFAULT_FIELD
        self.fields_drop.layout.width = "auto"

    def _validate_field(self, change: dict) -> None:
        """The traitlet field should be a valid OPTIMADE field."""
        field = change["new"]
        if field and field != self.NO_AVAILABLE_FIELDS:
            self.field = field
            self._toggle_sort_availability()
        else:
            self.freeze()

    @traitlets.observe("field")
    def _set_value_from_field(self, change: dict) -> None:
        """Update `value` from the new `field`."""
        value = change["new"]
        if value and value != self.NO_AVAILABLE_FIELDS:
            self.value = f"{self.order.value}{value}"
        else:
            self.value = None

    def _get_order_icon(self) -> str:
        """Return button icon according to sort order."""
        if self.order == Order.ASCENDING:
            return "sort-up"
        if self.order == Order.DESCENDING:
            return "sort-down"
        raise traitlets.TraitError(
            f"Out of Order! Could not determine order from self.order: {self.order!r}"
        )

    def _change_order(self, change: dict) -> None:
        """The order button has been toggled.

        When the toggle-button is "pressed down", i.e., the value is `True`,
        the order should be `descending`.
        """
        descending: bool = change["new"]
        self.order = Order.DESCENDING if descending else Order.ASCENDING
        self.order_select.description = (
            self.order_select.tooltip
        ) = self.order.name.capitalize()
        self.order_select.icon = self._get_order_icon()
        self._toggle_sort_availability()

    def _sort_clicked(self, _: dict) -> None:
        """The Sort button has been clicked.

        Set value to current sorting settings.
        Any usage of this widget should "observe" the `value` attribute to toggle sorting.
        """
        self._update_latest_sorting()
        if self.field:
            self.value = f"{self.order.value}{self.field}"
        else:
            self.value = None
