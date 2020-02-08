import re
from typing import List, Tuple, Dict, Union, Any
import traitlets
import ipywidgets as ipw

from aiidalab_optimade.utils import (
    get_list_of_valid_providers,
    get_list_of_provider_implementations,
    # get_structures_schema,
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

    def set_options(self, options: list):
        """Set options with hint at top/as first entry"""
        options.insert(0, (self.HINT, None))
        self.options = options
        with self.hold_trait_notifications():
            self.index = 0

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


class ParserError(Exception):
    """Error during FilterInputParser parsing"""

    def __init__(self, field: str = None, value: Any = None, msg: str = None):
        self.field = field if field is not None else "General"
        self.value = value if value is not None else ""
        self.msg = msg if msg is not None else "A general error occured during parsing."
        super().__init__(
            f"Field: {self.field}, Value: {self.value}, Message: {self.msg}"
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
        raise ParserError(field, value, msg="Not proper input. Should be, e.g., >=3")

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
                ("nelements", ("Number of Elements", "e.g., =3")),
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
        self.query_fields = {}
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


class ResultsPageChooser(ipw.HBox):
    """Flip through the OPTiMaDe 'pages'"""

    page_limit = traitlets.Int(0)
    data_returned = traitlets.Int(0)
    current_page = traitlets.Int(1)

    def __init__(self, **kwargs):
        self._layout = ipw.Layout(width="auto")

        self.pages: int

        self._button_layout = {
            "style": ipw.ButtonStyle(button_color="white"),
            "layout": ipw.Layout(height="auto", width="auto"),
        }
        self.button_sides = {
            "left": ipw.HBox(
                children=[
                    self._create_arrow_button("angle-double-left", "First results"),
                    self._create_arrow_button(
                        "angle-left", f"Previous {self.page_limit} results"
                    ),
                ]
            ),
            "right": ipw.HBox(
                children=[
                    self._create_arrow_button(
                        "angle-right", f"Next {self.page_limit} results"
                    ),
                    self._create_arrow_button("angle-double-right", "Last results"),
                ]
            ),
        }

        self.parts = [
            self.button_sides["left"],
            self.page_text(),
            self.button_sides["right"],
        ]
        super().__init__(children=self.parts, layout=self._layout, **kwargs)

    @traitlets.validate("page_limit", "data_returned")
    def _validate_non_negative_ints(self, proposal):  # pylint: disable=no-self-use
        """Traitlets must be >=0. Set value to 0 if <0."""
        value = proposal["value"]
        if value < 0:
            value = 0
        return value

    def reset(self):
        """Reset widget"""
        for side in self.button_sides.values():
            for button in side.children:
                button.disabled = False

    def freeze(self):
        """Disable widget"""
        for side in self.button_sides.values():
            for button in side.children:
                button.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.reset()

    def results_on_next_page(self) -> int:
        """Return the amount of results on the next page"""
        # if self.current_page

    def _create_arrow_button(self, icon: str, hover_text: str = None) -> ipw.Button:
        """Create an arrow button"""
        tooltip = hover_text if hover_text is not None else ""
        return ipw.Button(
            disabled=False, icon=icon, tooltip=tooltip, **self._button_layout
        )

    @staticmethod
    def page_text() -> ipw.HTML:
        """Create text between buttons"""
        return ipw.HTML("Showing 0-10 of 25 results")
