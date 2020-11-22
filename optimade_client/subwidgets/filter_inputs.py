# pylint: disable=too-many-arguments
from typing import Dict, List, Union, Tuple, Callable, Any

import ipywidgets as ipw
import traitlets

from optimade.models.utils import CHEMICAL_SYMBOLS

from optimade_client.exceptions import ParserError
from optimade_client.logger import LOGGER
from optimade_client.subwidgets.intrangeslider import CustomIntRangeSlider
from optimade_client.subwidgets.multi_checkbox import MultiCheckboxes
from optimade_client.subwidgets.periodic_table import PeriodicTable


__all__ = ("FilterTabs",)


class FilterTabs(ipw.Tab):
    """Separate filter inputs into tabs"""

    def __init__(self, show_large_filters: bool = True):
        sections: Tuple[Tuple[str, FilterTabSection]] = (
            ("Basic", FilterInputs(show_large_filters=show_large_filters)),
            # ("Advanced", ipw.HTML("This input tab has not yet been implemented.")),
            ("Raw", FilterRaw(show_large_filters=show_large_filters)),
        )

        super().__init__(
            children=tuple(_[1] for _ in sections),
            layout={"width": "auto", "height": "auto"},
        )
        for index, title in enumerate([_[0] for _ in sections]):
            self.set_title(index, title)

    def freeze(self):
        """Disable widget"""
        for widget in self.children:
            if not isinstance(widget, ipw.HTML):
                widget.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for widget in self.children:
            if not isinstance(widget, ipw.HTML):
                widget.unfreeze()

    def reset(self):
        """Reset widget"""
        for widget in self.children:
            if not isinstance(widget, ipw.HTML):
                widget.reset()

    def collect_value(self) -> str:
        """Collect inputs to a single OPTIMADE filter query string"""
        active_widget = self.children[self.selected_index]
        if not isinstance(active_widget, ipw.HTML):
            return active_widget.collect_value()
        return ""

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle text submission"""
        for section_widget in self.children:
            section_widget.on_submit(callback=callback, remove=remove)

    def update_range_filters(self, data: Dict[str, dict]):
        """Update filter widgets with a range (e.g., IntRangeSlider) according to `data`"""
        for section_widget in self.children:
            section_widget.range_nx = data


class FilterTabSection(ipw.VBox):
    """Base class for a filter tab section"""

    range_nx = traitlets.Dict(allow_none=True)

    def __init__(self, show_large_filters: bool = True, **kwargs):
        super().__init__(**kwargs)
        self._show_large_filters = show_large_filters

    @traitlets.observe("range_nx")
    def update_ranged_inputs(self, change: dict):
        """Update ranged inputs' min/max values"""

    def collect_value(self) -> str:
        """Collect inputs to a single OPTIMADE filter query string"""

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle user input submission"""


class FilterRaw(FilterTabSection):
    """Filter inputs for raw input"""

    def __init__(self, **kwargs):
        self.inputs = [
            FilterInput(
                description="Filter",
                hint="Raw 'filter' query string ...",
                description_width="50px",
            )
        ]

        super().__init__(children=self.inputs, layout={"width": "auto"}, **kwargs)

    def reset(self):
        """Reset widget"""
        for user_input in self.inputs:
            user_input.reset()

    def freeze(self):
        """Disable widget"""
        for user_input in self.inputs:
            user_input.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for user_input in self.inputs:
            user_input.unfreeze()

    def collect_value(self) -> str:
        """Collect inputs to a single OPTIMADE filter query string"""
        filter_ = self.inputs[0]
        return filter_.get_user_input.strip()

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle user input submission"""
        for user_input in self.inputs:
            user_input.on_submit(callback=callback, remove=remove)


class FilterInput(ipw.HBox):
    """Combination of HTML and input widget for filter inputs

    :param kwargs: Keyword arguments passed on to `input_widget`
    """

    def __init__(
        self,
        description: str,
        input_widget: Callable = None,
        hint: str = None,
        description_width: str = None,
        layout: dict = None,
        **kwargs,
    ):
        _description_width = (
            description_width if description_width is not None else "170px"
        )
        description = ipw.HTML(description, layout={"width": _description_width})
        _layout = layout if layout is not None else {"width": "100%"}

        self.input_widget = (
            input_widget(layout=_layout, **kwargs)
            if input_widget is not None
            else ipw.Text(layout=_layout)
        )

        if hint and isinstance(self.input_widget, ipw.widgets.widget_string._String):
            self.input_widget.placeholder = hint

        super().__init__(
            children=(description, self.input_widget), layout={"width": "auto"}
        )

    @property
    def get_user_input(self):
        """The Widget.value"""
        try:
            if not isinstance(self.input_widget, CustomIntRangeSlider):
                res = self.input_widget.value
            else:
                res = self.input_widget.get_value()
        except AttributeError as exc:
            raise ParserError(
                msg="Correct attribute can not be found to retrieve widget value",
                extras=[("Widget", self.input_widget)],
            ) from exc
        return res

    def reset(self):
        """Reset widget"""
        with self.hold_trait_notifications():
            self.input_widget.value = ""
        self.input_widget.disabled = False

    def freeze(self):
        """Disable widget"""
        self.input_widget.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.input_widget.disabled = False

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle text submission"""
        if isinstance(self.input_widget, ipw.Text):
            self.input_widget._submission_callbacks.register_callback(  # pylint: disable=protected-access
                callback, remove=remove
            )


class FilterInputParser:
    """Parse user input for filters"""

    def parse(self, key: str, value: Any) -> Tuple[Any, Union[None, str]]:
        """Reroute to self.<key>(value)"""
        func = getattr(self, key, None)
        if func is None:
            return self.__default__(value)
        return func(value)

    @staticmethod
    def __default__(value: Any) -> Tuple[Any, None]:
        """Default parsing fallback function"""
        return value, None

    @staticmethod
    def default_string_filter(value: str) -> Tuple[str, None]:
        """Default handling of string filters

        Remove any superfluous whitespace at the beginning and end of string values.
        Remove embedded `"` and wrap the value in `"` (if the value is supplied).
        """
        value = value.strip()
        value = value.replace('"', "")
        res = f'"{value}"' if value else ""
        return res, None

    def id(self, value: str) -> Tuple[str, None]:  # pylint: disable=invalid-name
        """id is a string input"""
        return self.default_string_filter(value)

    def chemical_formula_descriptive(self, value: str) -> Tuple[str, None]:
        """Chemical formula descriptive is a free form input"""
        return self.default_string_filter(value)

    @staticmethod
    def nperiodic_dimensions(value: List[bool]) -> Tuple[List[int], None]:
        """Return list of nperiodic_dimensions values according to checkbox choices"""
        res = []
        for include, periodicity in zip(value, range(4)):
            if include:
                res.append(periodicity)
        return res, None

    @staticmethod
    def ranged_int(
        field: str, value: Tuple[Union[int, None], Union[int, None]]
    ) -> Union[str, List[str]]:
        """Turn IntRangeSlider widget value into OPTIMADE filter string"""
        LOGGER.debug("ranged_int: Received value %r for field %r", value, field)

        low, high = value
        res = ""
        if low is None or high is None:
            if low is not None:
                res = f">={low}"
            if high is not None:
                res = f"<={high}"
        elif low == high:
            # Exactly N of property
            res = f"={low}"
        else:
            # Range of property
            res = [f">={low}", f"<={high}"]

        LOGGER.debug("ranged_int: Concluded the response is %r", res)

        return res

    def nsites(
        self, value: Tuple[Union[int, None], Union[int, None]]
    ) -> Tuple[Union[List[str], str], None]:
        """Operator with integer values"""
        return self.ranged_int("nsites", value), None

    def nelements(
        self, value: Tuple[Union[int, None], Union[int, None]]
    ) -> Tuple[Union[List[str], str], None]:
        """Operator with integer values"""
        return self.ranged_int("nelements", value), None

    @staticmethod
    def elements(
        value: Tuple[bool, Dict[str, int]]
    ) -> Tuple[Union[List[str], List[Tuple[str]]], List[str]]:
        """Extract included and excluded elements"""
        use_all = value[0]
        ptable_value = value[1]

        include = []
        exclude = []
        for element, state in ptable_value.items():
            if state == 0:
                # Include
                include.append(element)
            elif state == 1:
                # Exclude
                exclude.append(element)

        LOGGER.debug(
            "elements: With value %r the following are included: %r. And excluded: %r",
            value,
            include,
            exclude,
        )

        values = []
        operators = []
        if exclude:
            elements = ",".join([f'"{element}"' for element in exclude])
            values.append(("NOT", elements))
            operators.append(" HAS ANY ")
        if include:
            include_elements = ",".join([f'"{element}"' for element in include])
            values.append(include_elements)
            operators.append(" HAS ALL " if use_all else " HAS ANY ")

        LOGGER.debug(
            "elements: Resulting parsed operator(s): %r and value(s): %r",
            operators,
            values,
        )

        return values, operators


class FilterInputs(FilterTabSection):
    """Filter inputs in a single widget"""

    provider_section = traitlets.List()

    FILTER_SECTIONS = [
        (
            "Chemistry",
            [
                (
                    "chemical_formula_descriptive",
                    {
                        "description": "Chemical Formula",
                        "hint": "e.g., (H2O)2 Na",
                    },
                ),
                (
                    "elements",
                    {
                        "description": "Elements",
                        "input_widget": PeriodicTable,
                        "states": 2,  # Included/Excluded
                        "unselected_color": "#5096f1",  # Blue
                        "selected_colors": ["#66BB6A", "#EF5350"],  # Green, red
                        "border_color": "#000000",  # Black
                        "extended": "self._show_large_filters",
                    },
                ),
                (
                    "nelements",
                    {
                        "description": "Number of Elements",
                        "input_widget": CustomIntRangeSlider,
                        "min": 0,
                        "max": len(CHEMICAL_SYMBOLS),
                        "value": (0, len(CHEMICAL_SYMBOLS)),
                    },
                ),
            ],
        ),
        (
            "Cell",
            [
                (
                    "nperiodic_dimensions",
                    {
                        "description": "Dimensionality",
                        "input_widget": MultiCheckboxes,
                        "descriptions": ["Molecule", "Wire", "Planar", "Bulk"],
                    },
                ),
                (
                    "nsites",
                    {
                        "description": "Number of Sites",
                        "input_widget": CustomIntRangeSlider,
                        "min": 0,
                        "max": 10000,
                        "value": (0, 10000),
                    },
                ),
            ],
        ),
        (
            "Provider specific",
            [
                (
                    "id",
                    {
                        "description": "Provider ID",
                        "hint": "NB! Will take precedence",
                    },
                )
            ],
        ),
    ]

    OPERATOR_MAP = {
        "chemical_formula_descriptive": " CONTAINS ",
        "elements": " HAS ANY ",
        "nperiodic_dimensions": "=",
        "lattice_vectors": " HAS ANY ",
        "id": "=",
    }

    def __init__(self, **kwargs):
        self._show_large_filters = kwargs.get("show_large_filters", True)
        self.query_fields: Dict[str, FilterInput] = {}
        self._layout = ipw.Layout(width="auto")

        sections = [
            self.new_section(title, inputs) for title, inputs in self.FILTER_SECTIONS
        ]

        # Remove initial line-break
        sections[0].children[0].value = sections[0].children[0].value[len("<br>") :]

        super().__init__(children=sections, layout=self._layout, **kwargs)

    def reset(self):
        """Reset widget"""
        for user_input in self.query_fields.values():
            user_input.reset()

    def freeze(self):
        """Disable widget"""
        for user_input in self.query_fields.values():
            user_input.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for user_input in self.query_fields.values():
            user_input.unfreeze()

    @traitlets.observe("range_nx")
    def update_ranged_inputs(self, change: dict):
        """Update ranged inputs' min/max values"""
        ranges = change["new"]
        if not ranges or ranges is None:
            return

        for field, config in ranges.items():
            if field not in self.query_fields:
                raise ParserError(
                    field=field,
                    value="N/A",
                    extras=[
                        ("config", config),
                        ("self.query_fields.keys", self.query_fields.keys()),
                    ],
                    msg="Provided field is unknown. Can not update range for unknown field.",
                )

            widget = self.query_fields[field].input_widget
            cached_value: Tuple[int, int] = widget.value
            for attr in ("min", "max"):
                if attr in config:
                    try:
                        new_value = int(config[attr])
                    except (TypeError, ValueError) as exc:
                        raise ParserError(
                            field=field,
                            value=cached_value,
                            extras=[("attr", attr), ("config[attr]", config[attr])],
                            msg=f"Could not cast config[attr] to int. Exception: {exc!s}",
                        ) from exc

                    LOGGER.debug(
                        "Setting %s for %s to %d.\nWidget immediately before: %r",
                        attr,
                        field,
                        new_value,
                        widget,
                    )

                    # Since "min" is always set first, to be able to set "min" to a valid value,
                    # "max" is first set to the new "min" value + 1 IF the new "min" value is
                    # larger than the current "max" value, otherwise there is no reason,
                    # and it may indeed lead to invalid attribute setting, if this is done.
                    # For "max", coming last, this should then be fine, as the new "min" and "max"
                    # values should never be an invalid pair.
                    if attr == "min" and new_value > cached_value[1]:
                        widget.max = new_value + 1

                    setattr(widget, attr, new_value)

                    LOGGER.debug("Updated widget %r:\n%r", attr, widget)

            widget.value = (widget.min, widget.max)

            LOGGER.debug("Final state, updated widget:\n%r", widget)

    def update_provider_section(self):
        """Update the provider input section from the chosen provider"""
        # schema = get_structures_schema(self.base_url)

    def new_section(
        self, title: str, inputs: List[Tuple[str, Union[str, Dict[str, Any]]]]
    ) -> ipw.VBox:
        """Generate a new filter section"""
        header = ipw.HTML(f"<br><strong>{title}</strong>")
        user_inputs = []
        for user_input in inputs:
            input_config = user_input[1]
            if isinstance(input_config, dict):
                for key, value in input_config.items():
                    if isinstance(value, str) and value.startswith("self."):
                        input_config[key] = getattr(self, value[len("self.") :])
                new_input = FilterInput(**input_config)
            else:
                new_input = FilterInput(field=input_config)
            user_inputs.append(new_input)

            self.query_fields[user_input[0]] = new_input

        user_inputs.insert(0, header)
        return ipw.VBox(children=user_inputs, layout=self._layout)

    def _collect_value(self) -> str:
        """Collect inputs to a single OPTIMADE filter query string"""
        parser = FilterInputParser()

        result = []
        for field, user_input in self.query_fields.items():
            parsed_value, parsed_operator = parser.parse(
                field, user_input.get_user_input
            )
            if not parsed_value:
                # If the parsed value results in an empty value, skip field
                continue
            if not parsed_operator:
                # Use default operator if none is parsed
                parsed_operator = self.OPERATOR_MAP.get(field, "")

            if isinstance(parsed_value, (list, tuple, set)):
                for index, value in enumerate(parsed_value):
                    inverse = ""
                    if isinstance(value, tuple) and value[0] == "NOT":
                        inverse = "NOT "
                        value = value[1]
                    operator = (
                        parsed_operator[index]
                        if isinstance(parsed_operator, (list, tuple, set))
                        else parsed_operator
                    )
                    result.append(f"{inverse}{field}{operator}{value}")
            elif isinstance(parsed_value, str):
                operator = (
                    parsed_operator[0]
                    if isinstance(parsed_operator, (list, tuple, set))
                    else parsed_operator
                )
                result.append(f"{field}{operator}{parsed_value}")
            else:
                raise ParserError(
                    field=field,
                    value=user_input.get_user_input,
                    msg="Parsed value was neither a list, tuple, set nor str and it wasn't empty "
                    "or None.",
                    extras=(
                        "parsed_value",
                        parsed_value,
                        "parsed_operator",
                        parsed_operator,
                    ),
                )

        result = " AND ".join(result)
        return result.replace("'", '"')  # OPTIMADE Filter grammar only supports " not '

    def collect_value(self) -> str:
        """Collect inputs, while reporting if an error occurs"""
        try:
            res = self._collect_value()
        except ParserError:
            raise
        except Exception as exc:
            import traceback

            raise ParserError(
                msg=f"An exception occurred during collection of filter inputs: {exc!r}",
                extras=("traceback", traceback.print_exc(exc)),
            ) from exc
        else:
            return res

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle user input submission"""
        for user_input in self.query_fields.values():
            user_input.on_submit(callback=callback, remove=remove)
