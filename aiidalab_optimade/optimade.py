import traitlets
import ipywidgets as ipw

import ase

from aiida.orm.nodes.data.structure import Site, Kind, StructureData

from aiidalab_optimade.exceptions import ApiVersionError
from aiidalab_optimade.importer import OptimadeImporter
from aiidalab_optimade.utils import (
    get_list_of_valid_providers,
    get_list_of_provider_implementations,
)


__api_version__ = "v0.10.1"


DEFAULT_FILTER_VALUE = (
    'chemical_formula_descriptive CONTAINS "Al" OR (chemical_formula_anonymous = "AB" AND '
    'elements HAS ALL "Si","Al","O")'
)


class OptimadeProvidersWidget(ipw.VBox):
    """List all OPTiMaDe providers and their implementations"""

    database = traitlets.Tuple(traitlets.Unicode(), traitlets.Dict(allow_none=True))

    def __init__(self, **kwargs):
        providers = get_list_of_valid_providers()
        providers.insert(0, ("Select a provider", None))
        implementations = [("No provider chosen", None)]

        self.providers = ipw.Dropdown(options=providers)
        self.child_dbs = ipw.Dropdown(options=implementations, disabled=True)

        self.providers.observe(self._observe_providers, names="index")
        self.child_dbs.observe(self._observe_child_dbs, names="index")

        super().__init__(children=[self.providers, self.child_dbs], **kwargs)

    def _observe_providers(self, change):
        """Update child database dropdown upon changing provider"""
        index = change["new"]
        if index is None or self.providers.options[index][1] is None:
            self.child_dbs.options = [("No provider chosen", None)]
            self.child_dbs.disabled = True
            with self.hold_trait_notifications():
                self.providers.index = 0
                self.child_dbs.index = 0
        else:
            provider = self.providers.options[index][1]
            implementations = get_list_of_provider_implementations(provider)
            implementations.insert(0, ("Select a database", None))
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

            self.child_dbs.options = [("No provider chosen", None)]
            self.child_dbs.disabled = True


class SelectionStructureUploadWidget(ipw.Dropdown):
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


class OptimadeQueryWidget(ipw.VBox):  # pylint: disable=too-many-instance-attributes
    """Structure search and import widget for OPTiMaDe"""

    structure = traitlets.Instance(ase.Atoms, allow_none=True)
    database = traitlets.Tuple(traitlets.Unicode(), traitlets.Dict(allow_none=True))

    def __init__(self, **kwargs):
        self.header = ipw.HTML(
            "<h4><strong>Search for a structure in an OPTiMaDe database</h4></strong>"
        )
        self.base_url = OptimadeProvidersWidget()
        self.base_url.observe(self._on_database_select, names="database")

        self.filter_header = ipw.HTML("<br><strong>Apply query filter</strong>")
        self.filter = ipw.Textarea(
            description="filter:",
            value=DEFAULT_FILTER_VALUE,
            placeholder='e.g., elements HAS "Si","Al"',
        )
        self.query_button = ipw.Button(
            description="Search", button_style="primary", icon="search", disabled=True
        )
        self.query_button.on_click(self.query)

        self.structures_header = ipw.HTML("<br><strong>Choose a structure</strong>")
        self.structure_drop = SelectionStructureUploadWidget(
            description="Results:", disabled=True
        )
        self.structure_drop.observe(self._on_structure_select, names="value")

        super().__init__(
            children=[
                self.header,
                self.base_url,
                self.filter_header,
                self.filter,
                self.query_button,
                self.structures_header,
                self.structure_drop,
            ],
            **kwargs,
        )

    def _on_database_select(self, change):
        """Load chosen database"""
        self.database = change["new"]
        if self.database[1] is None or self.database[1].get("base_url", None) is None:
            self.query_button.disabled = True
        else:
            self.query_button.disabled = False
        self.structure_drop.reset()

    def _on_structure_select(self, change):
        """Update structure trait with chosen structure dropdown value"""
        chosen_structure = change["new"]
        if chosen_structure is None:
            self.structure = None
            with self.hold_trait_notifications():
                self.structure_drop.index = 0
        else:
            self.structure = chosen_structure["ase_atoms"]

    def freeze(self):
        """Disable widget"""
        self.query_button.disabled = True
        self.filter.disabled = True
        self.base_url.freeze()
        self.structure_drop.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.query_button.disabled = False
        self.filter.disabled = False
        self.base_url.unfreeze()
        self.structure_drop.unfreeze()

    def reset(self):
        """Reset widget"""
        with self.hold_trait_notifications():
            self.query_button.disabled = False
            self.base_url.reset()
            self.structure_drop.reset()

    @staticmethod
    def _get_structure_data(optimade_structure: dict) -> StructureData:
        """ Get StructureData from OPTiMaDe structure entry
        :param optimade_structure: OPTiMaDe structure entry from queried response
        :return: StructureData
        """

        attributes = optimade_structure["attributes"]
        structure = StructureData(cell=attributes["lattice_vectors"])

        # Add Kinds
        for kind in attributes["species"]:
            # NOTE: This should technically never happen,
            # since we are permanently adding to the filter
            # that we do not want structures with "disorder" or "unknown_positions"
            symbols = []
            for chemical_symbol in kind["chemical_symbols"]:
                if chemical_symbol == "vacancy":
                    symbols.append("X")
                else:
                    symbols.append(chemical_symbol)

            structure.append_kind(
                Kind(
                    symbols=symbols,
                    weights=kind["concentration"],
                    mass=kind["mass"],
                    name=kind["name"],
                )
            )

        # Add Sites
        for index in range(len(attributes["cartesian_site_positions"])):
            # range() to ensure 1-to-1 between kind and site
            structure.append_site(
                Site(
                    kind_name=attributes["species_at_sites"][index],
                    position=attributes["cartesian_site_positions"][index],
                )
            )

        return structure

    def _query(self):
        """Query helper function"""
        importer = OptimadeImporter(base_url=self.database[1]["base_url"])

        # Avoid structures that cannot be converted to an ASE.Atoms instance
        add_to_filter = 'NOT structure_features HAS ANY "disorder","unknown_positions"'

        # OPTiMaDe queries
        queries = {
            "filter_": "( {} ) AND ( {} )".format(self.filter.value, add_to_filter),
            "format_": "json",
            "email": None,
            "fields": None,
            "limit": 10,
        }

        return importer.query(**queries)

    def query(self, _):
        """Perform query"""
        try:
            # Freeze/disable list of structures in dropdown widget
            # We don't want changes leading to weird things happening prior to the query ending
            self.freeze()

            # Update button text and icon
            self.query_button.description = "Querying ... "
            self.query_button.icon = "cog"

            # Query database
            response = self._query()

            # Check implementation API version
            if response["meta"]["api_version"] != __api_version__:
                raise ApiVersionError(
                    "Only OPTiMaDe {} is supported. Chosen implementation has {}".format(
                        __api_version__, response["meta"]["api_version"]
                    )
                )

            # Go through data entries
            structures = []
            for entry in response["data"]:
                structure = self._get_structure_data(entry)

                if structure.has_vacancies or structure.is_alloy:
                    continue

                formula = structure.get_formula()

                optimade_id = entry["id"]
                entry_name = "{} (id={})".format(formula, optimade_id)
                entry_add = (
                    entry_name,
                    {"structure": structure, "ase_atoms": structure.get_ase()},
                )
                structures.append(entry_add)

            # Update list of structures in dropdown widget
            structures.insert(0, ("Choose a structure", None))
            self.structure_drop.reset()
            self.structure_drop.options = structures
            with self.hold_trait_notifications():
                self.structure_drop.index = 0

        finally:
            self.query_button.description = "Search"
            self.query_button.icon = "search"
            self.unfreeze()
