import re
from typing import Dict, List, Union, Tuple, Callable, Any

import ipywidgets as ipw
import traitlets

from optimade.models.utils import CHEMICAL_SYMBOLS

from optimade_client.exceptions import ParserError
from optimade_client.logger import LOGGER


__all__ = ("FilterTabs",)


class FilterTabs(ipw.Tab):
    """Separate filter inputs into tabs"""

    def __init__(self, **kwargs):
        sections: Tuple[Tuple[str, FilterTabSection]] = (
            ("Basic", FilterInputs()),
            # ("Advanced", ipw.HTML("This input tab has not yet been implemented.")),
            ("Raw", FilterRaw()),
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
        **kwargs,
    ):
        _description_width = (
            description_width if description_width is not None else "170px"
        )
        description = ipw.HTML(description, layout={"width": _description_width})

        _layout = {"width": "100%"}
        self.input_widget = (
            input_widget(layout=_layout, **kwargs)
            if input_widget is not None
            else ipw.Text(layout=_layout)
        )

        if hint and isinstance(self.input_widget, ipw.widgets.widget_string._String):
            self.input_widget.placeholder = hint

        super().__init__(
            children=[description, self.input_widget], layout=ipw.Layout(width="auto")
        )

    @property
    def get_user_input(self):
        """The Widget.value"""
        return self.input_widget.value

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

    def __default__(self, value: Any) -> Any:  # pylint: disable=no-self-use
        """Default parsing fallback function"""
        return value

    def parse(self, key: str, value: Any) -> Any:
        """Reroute to self.<key>(value)"""
        if isinstance(value, str):
            # Remove any superfluous whitespace at the beginning and end of string values
            value = value.strip()
        func = getattr(self, key, None)
        if func is None:
            return self.__default__(value)
        return func(value)

    @staticmethod
    def chemical_formula_descriptive(value: str) -> str:
        """Chemical formula descriptive is a free form input"""
        value = value.replace('"', "")
        return f'"{value}"' if value else ""

    @staticmethod
    def dimension_types(value: str) -> str:
        """Map to correct dimension_types value"""
        mapping = {
            "0": "1",  # [0,0,0]
            "1": "ALL 0,1",  # [0,0,1] not working at the moment
            "2": "ALL 0,1",  # [1,0,1] not working at the moment
            "3": "0",  # [1,1,1]
        }
        return mapping.get(value, value)

    @staticmethod
    def lattice_vectors(value: str) -> str:
        """Wrap in query list of values"""
        if value.find("(") != -1 and value.find(")") != -1:
            pass
            # wrappers = ("(", ")")
        elif value.find("[") != -1 and value.find("]") != -1:
            pass
            # wrappers = ("[", "]")
        else:
            raise ParserError(
                "Wrong input. Should be e.g. (4.1, 0, 0) (0, 4.1, 0) (0, 0, 4.1)",
                "lattica_vectors",
                value,
            )
        raise ParserError("Not yet implemented.", "lattice_vectors", value)
        # for vector in re.finditer(f"{wrappers[0]}.*{wrappers[1]}", value):
        #     vector.

    @staticmethod
    def operator_and_integer(field: str, value: str) -> str:
        """Handle operator for values with integers and a possible operator prefixed"""
        LOGGER.debug(
            "Parsing input with operator_and_integer. <field: %r>, <value: %r>",
            field,
            value,
        )

        match_operator = re.findall(r"[<>]?=?", value)
        match_no_operator = re.findall(r"^\s*[0-9]+", value)

        LOGGER.debug(
            "Finding all operators (or none):\nmatch_operator: %r\nmatch_no_operator: %r",
            match_operator,
            match_no_operator,
        )

        if match_operator and any(match_operator):
            match_operator = [_ for _ in match_operator if _]
            if len(match_operator) != 1:
                raise ParserError(
                    "Multiple values given with operators.",
                    field,
                    value,
                    extras=("match_operator", match_operator),
                )
            number = re.findall(r"[0-9]+", value)[0]
            operator = match_operator[0].replace(r"\s*", "")
            return f"{operator}{number}"
        if match_no_operator and any(match_no_operator):
            match_no_operator = [_ for _ in match_no_operator if _]
            if len(match_no_operator) != 1:
                raise ParserError(
                    "Multiple values given, must be an integer, "
                    "either with or without an operator prefixed.",
                    field,
                    value,
                    extras=("match_no_operator", match_no_operator),
                )
            result = match_no_operator[0].replace(r"\s*", "")
            return f"={result}"
        raise ParserError(
            "Not proper input. Should be, e.g., '>=3' or '5'",
            field,
            value,
            extras=[
                ("match_operator", match_operator),
                ("match_no_operator", match_no_operator),
            ],
        )

    @staticmethod
    def ranged_int(field: str, value: Tuple[int, int]) -> str:
        """Turn IntRangeSlider widget value into OPTIMADE filter string"""
        LOGGER.debug("ranged_int: Received value %r for field %r", value, field)

        low, high = value
        if low == high:
            # Exactly N of property
            res = f"={low}"
        else:
            # Range of property
            res = [f">={low}", f"<={high}"]

        LOGGER.debug("ranged_int: Concluded the response is %r", res)

        return res

    def nsites(self, value: Tuple[int, int]) -> Union[List[str], str]:
        """Operator with integer values"""
        return self.ranged_int("nsites", value)

    def nelements(self, value: Tuple[int, int]) -> Union[List[str], str]:
        """Operator with integer values"""
        return self.ranged_int("nelements", value)

    @staticmethod
    def elements(value: str) -> str:
        """Check against optimade-python-tools list of elememnts"""
        results = []
        symbols = re.findall(r",?\s*[\"']?([A-Za-z]+)[\"']?,?\s*", value)
        for symbol in symbols:
            if symbol == "":
                continue
            escaped_symbol = symbol.strip().replace(r"\W", "")
            escaped_symbol = escaped_symbol.capitalize()
            if escaped_symbol not in CHEMICAL_SYMBOLS:
                raise ParserError(
                    f"{escaped_symbol} is not a valid element.", "elements", value
                )
            results.append(escaped_symbol)
        return ",".join([f'"{symbol}"' for symbol in results])


class FilterInputs(FilterTabSection):
    """Filter inputs in a single widget"""

    provider_section = traitlets.List()

    FILTER_SECTIONS = [
        (
            "Chemistry",
            [
                (
                    "chemical_formula_descriptive",
                    {"description": "Chemical Formula", "hint": "e.g., (H2O)2 Na"},
                ),
                ("elements", {"description": "Elements", "hint": "H, O, Cl, ..."}),
                (
                    "nelements",
                    {
                        "description": "Number of Elements",
                        "input_widget": ipw.IntRangeSlider,
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
                    "dimension_types",
                    {
                        "description": "Dimensions",
                        "hint": "0: Molecule, 3: Bulk, (Not supported: 1: Wire, 2: Planar)",
                    },
                ),
                (
                    "nsites",
                    {
                        "description": "Number of Sites",
                        "input_widget": ipw.IntRangeSlider,
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
                    {"description": "Provider ID", "hint": "NB! Will take precedence"},
                )
            ],
        ),
    ]

    FIELD_MAP = {"dimension_types": "NOT dimension_types"}

    OPERATOR_MAP = {
        "chemical_formula_descriptive": " CONTAINS ",
        "elements": " HAS ALL ",
        "nelements": "",
        "dimension_types": " HAS ",
        "lattice_vectors": " HAS ANY ",
        "nsites": "",
        "id": "=",
    }

    def __init__(self, **kwargs):
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
                        )

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
                new_input = FilterInput(**input_config)
            else:
                new_input = FilterInput(field=input_config)
            user_inputs.append(new_input)

            self.query_fields[user_input[0]] = new_input

        user_inputs.insert(0, header)
        return ipw.VBox(children=user_inputs, layout=self._layout)

    def collect_value(self) -> str:
        """Collect inputs to a single OPTIMADE filter query string"""
        parser = FilterInputParser()

        result = []
        for field, user_input in self.query_fields.items():
            parsed_value = parser.parse(field, user_input.get_user_input)
            if not parsed_value:
                # If the parsed value results in an empty value, skip field
                continue

            if isinstance(parsed_value, (list, tuple, set)):
                result.extend(
                    [
                        f"{self.FIELD_MAP.get(field, field)}{self.OPERATOR_MAP[field]}{value}"
                        for value in parsed_value
                    ]
                )
            elif isinstance(parsed_value, str):
                result.append(
                    f"{self.FIELD_MAP.get(field, field)}{self.OPERATOR_MAP[field]}{parsed_value}"
                )
            else:
                raise ParserError(
                    field=field,
                    value=user_input.get_user_input,
                    msg="Parsed value was neither a list, tuple, set nor str and it wasn't empty "
                    "or None.",
                    extras=("parsed_value", parsed_value),
                )

        result = " AND ".join(result)
        return result.replace("'", '"')  # OPTIMADE Filter grammar only supports " not '

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle user input submission"""
        for user_input in self.query_fields.values():
            user_input.on_submit(callback=callback, remove=remove)
