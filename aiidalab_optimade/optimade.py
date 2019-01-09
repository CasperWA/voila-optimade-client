# -*- CODing: utf-8 -*-

# Python 2/3 compatibility
from __future__ import print_function
from __future__ import absolute_import

# Load AiiDA database
# pylint: disable=import-error
from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

# Imports
# pylint: disable=import-error
# pylint: disable=wrong-import-position
import requests
import tempfile
import ipywidgets as ipw
import nglview
from IPython.display import display
# import ase.io
from aiida.orm.data.structure import StructureData, Kind, Site
from aiida.orm.data.cif import CifData
# from aiida.orm.calculation import Calculation # pylint: disable=no-name-in-module
# from aiida.orm.querybuilder import QueryBuilder
from .importer import OptimadeImporter
from .exceptions import ApiVersionError


# NB! The nglview is not displayed in an Accordion
class OptimadeStructureImport():

    DATA_FORMATS = ("StructureData", "CifData")

    DATABASES = [
        ("Crystallography Open Database (COD)",{
            "name": "cod",
            "url": "http://www.crystallography.net/cod/optimade",
            "importer": None
        }),
        ("AiiDA @ localhost:5000",{
            "name": "aiida",
            "url": "http://127.0.0.1:5000/optimade",
            "importer": None
        }),
        ("Custom",{
            "name": "custom",
            "url": "cc4f821d.ngrok.io",
            "importer": None
        })
    ]

    def __init__(self, node_class=None):
        """ OPTiMaDe Structure Retrieval Widget
        Upload a structure according to OPTiMaDe API, mininmum v0.9.7a (v0.9.5 accepted for COD)

        :param node_class: AiiDA node class for storing the structure.
            Possible values: 'StructureData', 'CifData' or None (let the user decide).
            Note: If your workflows require a specific node class, better fix it here.
        """

        # Initial settings
        self.query_db = self.DATABASES[0][1]    # COD is default
        self.min_api_version = (0,9,5)          # Minimum acceptable OPTiMaDe API version
        self._clear_structures_dropdown()       # Set self.structure to 'select structure'

        # Sub-widgets / UI
        self.viewer = nglview.NGLWidget()

        self.btn_store = ipw.Button(
            description="Store in AiiDA",
            disabled=True
        )
        self.structure_description = ipw.Text(
            placeholder="Description (optional)"
        )
        
        self.filename = None
        self.structure_ase = None
        self.structure_node = None
        self.data_format = ipw.RadioButtons(
            options=self.DATA_FORMATS,
            description='Data type:'
        )

        if node_class is None:
            store = ipw.HBox(
                [self.btn_store, self.data_format, self.structure_description])
        elif node_class not in self.DATA_FORMATS:
            raise ValueError("Unknown data format '{}'. Options: {}".format(
                node_class, self.DATA_FORMATS))
        else:
            self.data_format.value = node_class
            store = ipw.HBox([self.btn_store, self.structure_description])

        self._create_ui(store)
        # super(OptimadeWidget, self).__init__(children=self._create_ui(store), **kwargs)

        # self.btn_store.on_click(self._on_click_store)

    def _create_ui(self, store):
        """
        :param store: HBox widget based on specified AiiDA node class for storing
        :return: children widgets for initialization of main widget
        """
        ## UI
        # Header - list of OPTiMaDe databases
        head_dbs = ipw.HTML("<h4><strong>OPTiMaDe database:</strong></h4>")
        drop_dbs = ipw.Dropdown(
            description="",
            options=self.DATABASES
        )
        drop_dbs.observe(self._on_change_db, names="value")

        head_host = ipw.HTML("Custom host:")
        self.inp_host = ipw.Text(
            description="http://",
            value=self.DATABASES[-1][-1]["url"],
            placeholder="e.g.: localhost:5000",
            disabled=True
        )
        txt_host = ipw.HTML("/optimade")

        # Filters - Accordion
        # head_filters = ipw.HTML("<h4><strong>Filters:</strong></h4>")
        self.inp_id = ipw.Text(
            description="id:",
            value="",
            placeholder='e.g. 9009008'
        )

        btn_query = ipw.Button(description='Query in DB')
        btn_query.button_style = 'primary'
        btn_query.on_click(self._on_click_query)

        self.query_message = ipw.HTML("Waiting for input ...")

        # Select structure - List of results (structures dropdown)
        self.drop_structure = ipw.Dropdown(
            description="Results:",
            options=self.structures
        )
        self.drop_structure.observe(self._on_change_struct, names='value')

        ## Display
        # Database header
        header = [
            head_dbs,
            drop_dbs,
            ipw.HBox([head_host, self.inp_host, txt_host]),
        ]

        # Database search filters
        search_filters = ipw.VBox(children=[
            self.inp_id,
            btn_query,
            self.query_message
        ])
        search_filters = ipw.Accordion(children=[search_filters])
        search_filters.set_title(0, "Search for Structure")
        search_filters.selected_index = None    # Close Accordion

        # Select (and store) structure
        select_structure = [
            self.drop_structure,
            self.viewer,
            store
        ]

        # Summarize to single list of VBox children
        # children = header
        # children.append(search_filters)
        # children.append(select_structure)

        display(
            header,
            search_filters,
            select_structure
        )

    @property
    def node_class(self):
        return self.data_format.value

    @node_class.setter
    def node_class(self, value):
        self.data_format.value = value

    def _on_change_db(self, dbs):
        """ Update database to be queried
        :param dbs: Dropdown widget containing list of OPTiMaDe databases
        """
        self.query_db = dbs['new']
        
        # Allow editing of text-field if "Custom" database is chosen
        if self.query_db["name"] == "custom":
            self.inp_host.disabled = False
        else:
            self.inp_host.disabled = True

    def query(self, idn=None, formula=None):
        importer = self.query_db["importer"]
        if importer is None:
            importer = OptimadeImporter(**self.query_db)
            self.query_db["importer"] = importer
        
        filter_ = dict()
        
        if idn is not None:
            filter_["id"] = idn
        if formula is not None:
            filter_["formula"] = formula  # TODO: Implement 'filter' queries
        
        return importer.query(filter_), importer.api_version

    def _clear_structures_dropdown(self):
        """ Reset dropdown of structure results """
        self.structures = [("select structure",{"status":False})]

    def _valid_entry(self, entry):
        """ Check if OPTiMaDe structure entry is valid
        Validity is decided according to the existence of partial occupancies,
        since ASE cannot deal with this.
        :param entry: OPTiMaDe structure entry from queried response
        :return: boolean
        """

        # Initialization
        attr = entry["attributes"]

        # Check for "vacancy" in chemical symbols of species
        for kind in attr["species"].values():
            for symbol in kind["chemical_symbols"]:
                if symbol == "vacancy":
                    return False

        return True

    def get_structure(self, entry):
        """ Get StructureData from OPTiMaDe structure entry
        :param entry: OPTiMaDe structure entry from queried response
        :return: StructureData
        """

        # Initialization
        attr = entry["attributes"]
        s = StructureData(cell=attr["lattice_vectors"])

        # Add Kinds
        for kind in attr["species"].values():
            s.append_kind(Kind(
                symbols=kind["chemical_symbols"],
                weights=kind["concentration"],
                mass=kind["mass"],
                name=kind["original_name"]
            ))
        
        # Add Sites
        for idx in range(len(attr["cartesian_site_positions"])):
            # range() to ensure 1-to-1 between kind and site
            s.append_site(Site(
                kind_name=attr["species_at_sites"][idx],
                position=attr["cartesian_site_positions"][idx]
            ))

        return s

    # pylint: disable=too-many-locals
    # pylint: disable=unused-argument
    def _on_click_query(self, b):
        """ Query database
        :param b: 'Query in DB' button widget
        """
        # Clear list of structures (previously found) in dropdown widget
        self._clear_structures_dropdown()

        # Get 'id' user-input
        idn = None
        formula = None
        try:
            idn = int(self.inp_id.value)
        except ValueError:
            formula = str(self.inp_id.value)  # Not yet implemented
        
        # Define custom host URL
        # NB! There are no checks on the host input by user, only if empty or not.
        if self.query_db["name"] == "custom":
            if self.inp_host.value == "":
                # No host specified as input
                self.query_message.value = "You must specify a host URL, e.g. 'localhost:5000'"
                return
            self.query_db["url"] = "http://{}/optimade".format(self.inp_host.value)
        
        # Update status message and query database
        self.query_message.value = "Quering the database ... "
        response, api_version = self.query(idn=idn, formula=formula)
        
        # API version check
        old = False
        valid = api_version >= self.min_api_version
        if api_version < self.min_api_version:
            self.query_message.value = "OPTiMaDe API {} is not supported. " \
                                "Must be at least {}.".format(self.ver_to_str(api_version), self.ver_to_str(self.min_api_version))
        elif api_version == self.min_api_version:
            old = True

        # Initialization
        count = 0               # Count of structures found
        non_valid_count = 0     # Count of structures with partial occupancies found (not allowed due to ASE)
        
        # Go through data entries
        for entry in response["data"]:
            if not valid:
                ## Not a valid API version: too old API version
                # While there may be several entries in response["data"]
                # they will not be considered here, since there is no guarantee
                # that they are readable/parseable
                # So break, do not continue.
                break
                
            elif old:
                ## API version 0.9.5 (specifically for COD)
                
                cif_url = entry["links"]["self"]
                fn = requests.get(cif_url)
                with tempfile.NamedTemporaryFile(mode='w+') as f:
                    f.write(fn.text)
                    f.flush()
                    entry_cif = CifData(file=f.name, parse_policy='lazy')
                    
                formula = entry_cif.get_ase().get_chemical_formula()
                
            else:
                ## API version 0.9.7a
                
                if self._valid_entry(entry):
                    structure = self.get_structure(entry)
                else:
                    count += 1
                    non_valid_count += 1
                    continue
                
                entry_cif = structure._get_cif()  # pylint: disable=protected-access
                formula = structure.get_formula()
                cif_url = ""
                
            
            idn = entry["id"]
            entry_name = "{} (id: {})".format(formula, idn)
            entry_add = (entry_name,
                            {
                                "status": True,
                                "cif": entry_cif,
                                "url": cif_url,
                                "id": idn,
                            }
                        )
            self.structures.append(entry_add)
            count += 1
        
        if valid:
            self.query_message.value = "Quering the database ... {} structure(s) found" \
                                       " ... {} non-valid structure(s) found " \
                                       "(partial occupancies are not allowed)".format(count, non_valid_count)

        self.drop_structure.options = self.structures
        if len(self.structures) > 1:
            self.drop_structure.value = self.structures[1][1]

    def refresh_structure_view(self, atoms):
        if hasattr(self.viewer, "component_0"):
            self.viewer.clear_representations()
            self.viewer.component_0.remove_ball_and_stick()  # pylint: disable=no-member
            self.viewer.component_0.remove_ball_and_stick()  # pylint: disable=no-member
            self.viewer.component_0.remove_ball_and_stick()  # pylint: disable=no-member
            self.viewer.component_0.remove_unitcell()        # pylint: disable=no-member
            cid = self.viewer.component_0.id                 # pylint: disable=no-member
            self.viewer.remove_component(cid)

        self.viewer.add_component(nglview.ASEStructure(atoms.get_ase())) # adds ball+stick
        self.viewer.add_unitcell() # pylint: disable=no-member
        self.viewer.center()

    def _on_change_struct(self, structs):
        """ Update "result view" to chosen structure
        :param structs: Dropdown widget containing list of structure entries
        """
        # indx = structs['owner'].index
        new_element = structs['new']
        if new_element['status'] is False:
            return
        atoms = new_element['cif']
        # formula = atoms.get_ase().get_chemical_formula()
        
        # search for existing calculations using chosen structure
        # qb = QueryBuilder()
        # qb.append(StructureData)
        # qb.append(Calculation, filters={'extras.formula':formula}, descendant_of=StructureData)
        # qb.order_by({Calculation:{'ctime':'desc'}})
        # for n in qb.iterall():
        #     calc = n[0]
        #     print("Found existing calculation: PK=%d | %s"%(calc.pk, calc.get_extra("structure_description")))
        #     thumbnail = b64decode(calc.get_extra("thumbnail"))
        #     display(Image(data=thumbnail))
        # struct_url = new_element['url'].split('.cif')[0]+'.html'
        # if new_element['url'] != "":
        #     self.link.value='<a href="{}" target="_blank">{} entry {}</a>'.format(struct_url, self.query_db["name"], new_element['id'])
        # else:
        #     self.link.value='{} entry {}'.format(self.query_db["name"], new_element['id'])
        self.refresh_structure_view(atoms)

    # # pylint: disable=unused-argument
    # def _on_file_upload(self, change):
    #     self.tmp_folder = tempfile.mkdtemp()
    #     # tmp = self.tmp_folder + '/' + self.file_upload.filename
    #     # with open(tmp, 'w') as f:
    #     #     f.write(self.file_upload.data)
    #     # self.select_structure(name=self.file_upload.filename)
    #     self.select_structure(name=self.filename)

    # def select_structure(self, name):
    #     structure_ase = self.get_ase(self.tmp_folder + '/' + name)
    #     self.btn_store.disabled = False
    #     if structure_ase is None:
    #         self.structure_ase = None
    #         self.btn_store.disabled = True
    #         self.refresh_view()
    #         return

    #     self.structure_description.value = self.get_description(
    #         structure_ase, name)
    #     self.structure_ase = structure_ase
    #     self.refresh_view()

    # def get_ase(self, fname):
    #     try:
    #         traj = ase.io.read(fname, index=":")
    #     except AttributeError:
    #         print("Looks like {} file does not contain structure coordinates".
    #               format(fname))
    #         return None
    #     if len(traj) > 1:
    #         print(
    #             "Warning: Uploaded file {} contained more than one structure. The first one will be taken."
    #             .format(fname))
    #     return traj[0]

    # def get_description(self, structure_ase, name):
    #     formula = structure_ase.get_chemical_formula()
    #     return "{} ({})".format(formula, name)

    # def refresh_view(self):
    #     viewer = self.viewer
    #     # Note: viewer.clear() only removes the 1st component
    #     # pylint: disable=protected-access
    #     for comp_id in viewer._ngl_component_ids:
    #         viewer.remove_component(comp_id)

    #     viewer.add_component(nglview.ASEStructure(
    #         self.structure_ase))  # adds ball+stick
    #     viewer.add_unitcell() # pylint: disable=no-member

    # pylint: disable=unused-argument
    # def _on_click_store(self, change):
    #     self.store_structure(
    #         self.filename,
    #         # self.file_upload.filename,
    #         description=self.structure_description.value)

    # def store_structure(self, name, description=None):
    #     structure_ase = self.get_ase(self.tmp_folder + '/' + name)
    #     if structure_ase is None:
    #         return

    #     # determine data source
    #     if name.endswith('.cif'):
    #         source_format = 'CIF'
    #     else:
    #         source_format = 'ASE'

    #     # perform conversion
    #     if self.data_format.value == 'CifData':
    #         if source_format == 'CIF':
    #             structure_node = CifData(
    #                 file=self.tmp_folder + '/' + name,
    #                 scan_type='flex',
    #                 parse_policy='lazy')
    #         else:
    #             structure_node = CifData()
    #             structure_node.set_ase(structure_ase)
    #     else:  # Target format is StructureData
    #         structure_node = StructureData(ase=structure_ase)

    #         #TODO: Figure out whether this is still necessary for StructureData
    #         # ensure that tags got correctly translated into kinds
    #         for t1, k in zip(structure_ase.get_tags(),
    #                          structure_node.get_site_kindnames()):
    #             t2 = int(k[-1]) if k[-1].isnumeric() else 0
    #             assert t1 == t2
    #     if description is None:
    #         structure_node.description = self.get_description(
    #             structure_ase, name)
    #     else:
    #         structure_node.description = description
    #     structure_node.label = ".".join(name.split('.')[:-1])
    #     structure_node.store()
    #     self.structure_node = structure_node
    #     print("Stored in AiiDA: " + repr(structure_node))

    @staticmethod
    def ver_to_str(api_version):
        """
        Convert api_version from tuple of integers to string.
        
        :param api_version: Tuple of integers representing API version: (MAJOR,MINOR,PATCH)
        :return: String representing API version: "vMAJOR.MINOR.PATCH"
        """
        
        # Perform check(s)
        if not isinstance(api_version, tuple):
            raise TypeError("api_version must be of type 'tuple'.")
        if len(api_version) > 3:  # Shouldn't be necessary to check
            raise ApiVersionError("Too many arguments for api_version. "
                                "API version is defined as maximum (MAJOR,MINOR,PATCH).")
        if len(api_version) == 1 and api_version[0] == 0:  # Shouldn't be necessary to check
            raise ApiVersionError("When API MAJOR version is 0, MINOR version MUST be specified.")
        
        # Convert
        version = "v"
        version += ".".join([str(v) for v in api_version])
        
        return version
