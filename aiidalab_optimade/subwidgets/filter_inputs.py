import re
from typing import Dict, List, Union, Tuple

import ipywidgets as ipw
import traitlets

from aiidalab_optimade.exceptions import ParserError


__all__ = ("FilterInputs",)


class FilterText(ipw.HBox):
    """Combination of HTML and Text for filter inputs"""

    def __init__(self, field: str, hint: str = None, field_width: str = None, **kwargs):
        _field_width = field_width if field_width is not None else "150px"
        description = ipw.HTML(field, layout=ipw.Layout(width=_field_width))
        self.text_input = ipw.Text(layout=ipw.Layout(width="100%"))
        if hint:
            self.text_input.placeholder = hint
        super().__init__(
            children=[description, self.text_input],
            layout=ipw.Layout(width="auto"),
            **kwargs,
        )

    @property
    def user_input(self):
        """The Text.value"""
        return self.text_input.value

    def reset(self):
        """Reset widget"""
        self.text_input.disabled = False

    def freeze(self):
        """Disable widget"""
        self.text_input.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)
        This is the same as self.reset() in this case,
        since we want to keep the already typed in filter inputs.
        """
        self.reset()

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle text submission"""
        self.text_input._submission_callbacks.register_callback(  # pylint: disable=protected-access
            callback, remove=remove
        )


class FilterInputParser:
    """Parse user input for filters"""

    def parse(self, key: str, value: str) -> str:
        """Reroute to self.<key>(value)"""
        func = getattr(self, key, None)
        if func is None:
            return self.__default__(value)
        return func(value)

    def __default__(self, value: str) -> str:  # pylint: disable=no-self-use
        """Default parsing fallback function"""
        return value

    @staticmethod
    def chemical_formula_descriptive(value: str) -> str:
        """Chemical formula descriptive is a free form input"""
        value = re.sub('"', "", value)
        return f'"{value}"'

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
                "lattica_vectors",
                value,
                msg="Wrong input. Should be e.g. (4.1, 0, 0) (0, 4.1, 0) (0, 0, 4.1)",
            )
        raise ParserError("lattice_vectors", value, msg="Not yet implemented.")
        # for vector in re.finditer(f"{wrappers[0]}.*{wrappers[1]}", value):
        #     vector.

    @staticmethod
    def operator_and_integer(field: str, value: str) -> str:
        """Handle operator for values with integers and a possible operator prefixed"""
        match_operator = re.findall(r"[<>]?=?", value)
        match_no_operator = re.findall(r"^\s*[0-9]+", value)
        if match_operator and any(match_operator):
            match_operator = [_ for _ in match_operator if _]
            if len(match_operator) != 1:
                raise ParserError(
                    field, value, msg="Multiple values given with operators."
                )
            number = re.findall(r"[0-9]+", value)[0]
            operator = re.sub(r"\s*", "", match_operator[0])
            return f"{operator}{number}"
        if match_no_operator and any(match_no_operator):
            match_no_operator = [_ for _ in match_no_operator if _]
            if len(match_no_operator) != 1:
                raise ParserError(
                    field,
                    value,
                    msg="Multiple values given, must be an integer, "
                    "either with or without an operator prefixed.",
                )
            result = re.sub(r"\s*", "", match_no_operator[0])
            return f"={result}"
        raise ParserError(
            field, value, msg="Not proper input. Should be, e.g., >=3 or 5"
        )

    def nsites(self, value: str) -> str:
        """OPTIONAL operator with integer value"""
        return self.operator_and_integer("nsites", value)

    def nelements(self, value: str) -> str:
        """OPTIONAL operator with integer value"""
        return self.operator_and_integer("nelements", value)

    @staticmethod
    def elements(value: str) -> str:
        """Check against optimade-python-tools list of elememnts"""
        from optimade.models.utils import CHEMICAL_SYMBOLS

        results = []
        symbols = re.findall(r",?\s*[\"']?\w*[\"']?,?\s*", value)
        for symbol in symbols:
            if symbol == "":
                continue
            escaped_symbol = re.sub(r"\W", "", symbol.strip())
            escaped_symbol = escaped_symbol.capitalize()
            if escaped_symbol not in CHEMICAL_SYMBOLS:
                raise ParserError(
                    "elements", value, msg=f"{escaped_symbol} is not a valid element."
                )
            results.append(escaped_symbol)
        return ",".join([f'"{symbol}"' for symbol in results])


class FilterInputs(ipw.VBox):
    """Filter inputs in a single widget"""

    provider_section = traitlets.List()

    FILTER_SECTIONS = [
        (
            "Chemistry",
            [
                (
                    "chemical_formula_descriptive",
                    ("Chemical Formula", "e.g., (H2O)2 Na"),
                ),
                ("elements", ("Elements", "H, O, Cl, ...")),
                ("nelements", ("Number of Elements", "e.g., 3 or >=5")),
            ],
        ),
        (
            "Cell",
            [
                (
                    "dimension_types",
                    (
                        "Dimensions",
                        "0: Molecule, 3: Bulk, (Not supported: 1: Wire, 2: Planar)",
                    ),
                ),
                # (
                #     "lattice_vectors",
                #     (
                #         "Lattice Vectors",
                #         "e.g., (4.1, 0, 0), (0, 4.1, 0), (0, 0, 4.1)",
                #     ),
                # ),
                ("nsites", ("Number of Sites", "e.g., >5")),
            ],
        ),
        ("Provider specific", [("id", ("Provider ID", "NB! Will take precedence"))]),
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
        self.query_fields: Dict[str, FilterText] = {}
        self._layout = ipw.Layout(width="auto")

        sections = [
            self.new_section(title, inputs) for title, inputs in self.FILTER_SECTIONS
        ]
        super().__init__(children=sections, layout=self._layout, **kwargs)

    def reset(self):
        """Reset widget"""
        for text in self.query_fields.values():
            text.reset()

    def freeze(self):
        """Disable widget"""
        for text in self.query_fields.values():
            text.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for text in self.query_fields.values():
            text.unfreeze()

    def update_provider_section(self):
        """Update the provider input section from the chosen provider"""
        # schema = get_structures_schema(self.base_url)

    def new_section(
        self, title: str, inputs: List[Dict[str, Union[str, Tuple]]]
    ) -> ipw.VBox:
        """Generate a new filter section"""
        header = ipw.HTML(f"<br><strong>{title}</strong>")
        text_inputs = []
        for text_input in inputs:
            text = text_input[1]
            if isinstance(text, tuple):
                new_input = FilterText(field=text[0], hint=text[1])
            else:
                new_input = FilterText(field=text)
            text_inputs.append(new_input)

            self.query_fields[text_input[0]] = new_input

        text_inputs.insert(0, header)
        return ipw.VBox(children=text_inputs, layout=self._layout)

    def collect_value(self) -> str:
        """Collect inputs to a single OPTiMaDe filter query string"""
        parser = FilterInputParser()

        result = " AND ".join(
            [
                f"{self.FIELD_MAP.get(field, field)}{self.OPERATOR_MAP[field]}"
                f"{parser.parse(field, text.user_input)}"
                for field, text in self.query_fields.items()
                if text.user_input != ""
            ]
        )
        return re.sub("'", '"', result)

    def on_submit(self, callback, remove=False):
        """(Un)Register a callback to handle text submission"""
        for text in self.query_fields.values():
            text.on_submit(callback=callback, remove=remove)
