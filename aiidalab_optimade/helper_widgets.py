from typing import List, Tuple, Dict, Union
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
                ("elements", ("Elements", '"H","O","Cl", ...')),
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
                (
                    "lattice_vectors",
                    (
                        "Lattice Vectors",
                        "e.g., [ [4.1, 0, 0], [0, 4.1, 0], [0, 0, 4.1] ]",
                    ),
                ),
                ("nsites", ("Number of Sites", "e.g., >5")),
            ],
        ),
        ("Provider specific", [("id", ("Provider ID", "NB! Will take precedence"))]),
    ]

    FIELD_MAP = {"dimension_types": "NOT dimension_types"}

    VALUE_MAP = {
        "dimension_types": {
            "0": "1",  # [0,0,0]
            "1": "ALL 0,1",  # [0,0,1]
            "2": "ALL 0,1",  # [1,0,1]
            "3": "0",  # [1,1,1]
        }
    }

    OPERATOR_MAP = {
        "chemical_formula_descriptive": " CONTAINS ",
        "elements": " HAS ALL ",
        "nelements": "",
        "dimension_types": " HAS ",
        "lattice_vectors": "=",
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
        import re

        result = " AND ".join(
            [
                f"{self.FIELD_MAP.get(field, field)}{self.OPERATOR_MAP[field]}"
                f"{self.VALUE_MAP.get(field, {}).get(text.user_input, text.user_input)}"
                for field, text in self.query_fields.items()
                if text.user_input != ""
            ]
        )
        return re.sub("'", '"', result)
