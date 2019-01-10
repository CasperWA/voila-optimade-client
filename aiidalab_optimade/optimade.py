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
from IPython.display import display, clear_output
# import ase.io
from aiida.orm.data.structure import StructureData, Kind, Site
from aiida.orm.data.cif import CifData
from aiida.orm.calculation import Calculation # pylint: disable=no-name-in-module
from aiida.orm.querybuilder import QueryBuilder
from .importer import OptimadeImporter
from .exceptions import ApiVersionError, InputError, DisplayInputError

# TODO: Implement:
#       - Awareness of pagination

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
        ("Custom host:",{
            "name": "custom",
            "url": "",
            "importer": None
        })
    ]
    RESPONSE_LIMIT = 25

    def __init__(self, database=None, host=None, node_class=None):
        """ OPTiMaDe Structure Retrieval
        Upload a structure according to OPTiMaDe API, mininmum v0.9.7a (v0.9.5 accepted for COD)

        :param database: str: Structure database with implemented OPTiMaDe API.
        :param host: str: Must be specified if database is "custom".
            Must be the URL before "/optimade"
        :param node_class: str: AiiDA node class for storing the structure.
            Possible values: 'StructureData', 'CifData' or None (let the user decide).
            Note: If your workflows require a specific node class, better fix it here.
        """

        # Initial settings
        self.min_api_version = (0,9,5)          # Minimum acceptable OPTiMaDe API version
        self._clear_structures_dropdown()       # Set self.structure to 'select structure'
        self.atoms = None                       # Selected structure
        self.structure_data = self._init_structure_data()   # dict of structure data
        # self.structure_ase = None
        # self.structure_node = None

        # Sub-widgets / UI
        self.viewer = nglview.NGLWidget()

        self.btn_store = ipw.Button(
            description="Store in AiiDA",
            disabled=True,
            button_style="primary"
        )
        self.data_format = ipw.RadioButtons(
            options=self.DATA_FORMATS,
            description='Data type:'
        )
        self.structure_description = ipw.Text(
            description="",
            placeholder="Description (optional)"
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

        self._create_ui(store)                  # Create UI
        self.set_database(database, host)       # OPTiMaDe database to query

    def _create_ui(self, store):
        """ Create UI
        :param store: HBox widget based on specified AiiDA node class for storing
        :return: children widgets for initialization of main widget
        """
        ## UI
        # Header - list of OPTiMaDe databases
        head_dbs = ipw.HTML("<h4><strong>OPTiMaDe database:</strong></h4>")
        self.drop_dbs = ipw.Dropdown(
            description="",
            options=self.DATABASES
        )
        self.drop_dbs.observe(self._on_change_db, names="value")

        self.inp_host = ipw.Text(
            description="http://",
            placeholder="e.g. localhost:5000"
        )
        txt_host = ipw.HTML("/optimade")

        self.custom_host_widgets = ipw.HBox(
            children=[self.inp_host, txt_host],
            layout=ipw.Layout(visibility="hidden")
        )

        # Filters - Accordion
        # head_filters = ipw.HTML("<h4><strong>Filters:</strong></h4>")
        self.inp_id = ipw.Text(
            description="id:",
            value="",
            placeholder='e.g. 9009008 or 16'
        )

        btn_query = ipw.Button(description='Query in DB')
        btn_query.button_style = 'primary'
        btn_query.on_click(self._on_click_query)

        self.query_message = ipw.HTML("")

        # Select structure - List of results (structures dropdown)
        self.drop_structure = ipw.Dropdown(
            description="Results:",
            options=self.structures
        )
        self.drop_structure.observe(self._on_change_struct, names='value')

        self.data_output = ipw.Output(layout=ipw.Layout(
            visibility="hidden"
            # width="100%"
        ))
        
        # Store structure
        self.btn_store.on_click(self._on_click_store)
        self.store_out = ipw.Output()

        ## Display parts
        # Database header
        self.disp_host = ipw.VBox([
            head_dbs,
            ipw.HBox([self.drop_dbs, self.custom_host_widgets])
        ])

        # Database search filters
        self.disp_filters = ipw.VBox([
            self.inp_id
        ])
        self.disp_filters = ipw.Accordion(children=[self.disp_filters])
        self.disp_filters.set_title(0, "Filters")
        self.disp_filters.selected_index = None    # Close Accordion

        # Select structure
        self.disp_select_structure = ipw.VBox([
            btn_query,
            self.query_message,
            self.drop_structure,
        ])

        # View structure
        self.disp_view_structure = ipw.VBox([
            # ipw.HBox([self.data_output, self.viewer]),
            self.data_output,
            self.viewer
        ])

        # Store structure in AiiDA
        self.disp_store = ipw.VBox([
            store,
            self.store_out
        ])

    def display(self, parts=None, no_host=False):
        """ Display OPTiMaDe structure import parts
        
        parts may be: "host", "filters", "select", "viewer", "store".
        If parts is None, all parts will be displayed.

        NB! Since one may call the display method several times to display the same part multiple times,
        multiple instances of the same part in parts is allowed.

        NB! no_host has no effect if "host" is specified in parts.

        :param parts: list:  Display only chosen parts of the OPTiMaDe structure import app
                      str:   Display only chosen part of the OPTiMaDe structure import app
        :param no_host: bool: Leave out the host part. Default: False
        """

        # Checks
        if parts is not None:
            # Type - make parts a list
            if isinstance(parts, str):
                parts = [parts]
            elif not isinstance(parts, list):
                raise TypeError("parts must be either a list of strings or a string")


        # Initialize
        valid_parts = dict(
            host=self.disp_host,
            filters=self.disp_filters,
            select=self.disp_select_structure,
            viewer=self.disp_view_structure,
            store=self.disp_store
        )

        # Display all parts - Default
        if parts is None:
            if no_host:
                display(
                    self.disp_filters,
                    self.disp_select_structure,
                    self.disp_view_structure,
                    self.disp_store
                )
            else:
                display(
                    self.disp_host,
                    self.disp_filters,
                    self.disp_select_structure,
                    self.disp_view_structure,
                    self.disp_store
                )
        # Display specific parts
        else:
            for part in parts:
                # Check specified part(s) is/are valid
                if part not in valid_parts:
                    raise DisplayInputError("Unknown part. Valid parts: {}".format(",".join([p for p in valid_parts])))
                
                # Display
                display(valid_parts[part])

    @property
    def host(self):
        return self.inp_host.value

    @host.setter
    def host(self, value):
        self.inp_host.value = value

    @property
    def database(self):
        return self.query_db["name"]

    @database.setter
    def database(self, value):
        self.set_database(value, self.host)

    def set_database(self, database, host):
        """ Set OPTiMaDe database to query
        If database is None, COD will be chosen as the default database.
        If database is "custom", host must also be specified.

        :param database: str: OPTiMaDe database to be queried.
        :param host: str: Must be specified if database is "custom".
        :return: dict: Relevant information pertaining to the database of choice,
                       taken from self.DATABASES.
        """

        # User-specified database
        if database is not None:
            # Type check
            if not isinstance(database, str):
                raise TypeError("database must be a string")
            
            # Get database in lower case to be able to compare with DATABASES
            database = database.lower()
            
            # Set database
            valid_db = False
            for (_,db) in self.DATABASES:
                if database == db["name"]:
                    self.query_db = db
                    valid_db = True
                    break
            
            if not valid_db:
                raise InputError("Database input '{}' is not valid. Available inputs are: {}"
                                 .format(database, ",".join([db["name"] for (_,db) in self.DATABASES])))

            # Special case for custom database
            if database == "custom":
                # Check that host is specified if database is "custom"
                if host is None:
                    raise InputError("host must be specified, when a custom database is specified")
                
                # Type check
                if not isinstance(host, str):
                    raise TypeError("host must be a string")

                # Set host
                self.inp_host.value = host
        else:
            # COD is set as default database
            self.query_db = self.DATABASES[0][1]
        
        # Update UI
        for (v, db) in self.DATABASES:
            if self.query_db["name"] == db["name"]:
                self.drop_dbs.label = v
                self.drop_dbs.value = db

    @property
    def node_class(self):
        return self.data_format.value

    @node_class.setter
    def node_class(self, value):
        self.data_format.value = value

    def _init_structure_data(self):
        """ Initialize structure data
        A dict output that will be shown in an Output widget next to the nglview
        :return: Structure data
        """
        
        data = dict(
            formula="",
            elements="",
            number_of_elements="",
            number_of_sites_in_unit_cell="",
            unit_cell=""
        )

        return data

    def _on_change_db(self, dbs):
        """ Update database to be queried
        :param dbs: Dropdown widget containing list of OPTiMaDe databases
        """
        self.query_db = dbs['new']
        
        # Allow editing of text-field if "Custom" database is chosen
        if self.query_db["name"] == "custom":
            self.custom_host_widgets.layout.visibility = "visible"
        else:
            self.custom_host_widgets.layout.visibility = "hidden"

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
        
        # OPTiMaDe URI queries
        optimade_queries = dict(
            format_ = "json",
            email = None,
            fields = None,
            limit = self.RESPONSE_LIMIT
        )

        return importer.query(filter_, **optimade_queries), importer.api_version

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

    def get_attributes(self, entry):
        """ Get relevant structure data from entry attributes
        :param entry: OPTiMaDe structure entry from queried response
        :return: dict: Relevant attributes for output
        """

        # Initialization
        attr = entry["attributes"]
        out = dict()

        # Get formula, elements, number of elements, and number of sites in unit cell
        out.update(
            formula=attr["chemical_formula"],
            elements=attr["elements"],
            number_of_elements=int(attr["nelements"]),
            number_of_sites_in_unit_cell=len(attr["cartesian_site_positions"])
        )

        # Get unit cell
        uc = True
        for dim_type in attr["dimension_types"]:
            if dim_type != 1:
                uc = False
                break
        
        if uc:
            uc_matrix = [vector for vector in attr["lattice_vectors"]]
        else:
            uc_matrix = ""
        
        out.update(unit_cell=uc_matrix)

        return out

    def _update_custom_url(self):
        """ Update "url" key for custom host """
        if self.inp_host.value == "":
            # No host specified as input
            self.query_message.value = "You must specify a host URL, e.g. 'localhost:5000'"
            return
        self.query_db["url"] = "http://{}/optimade".format(self.inp_host.value)

    def _check_api_version(self, api_version):
        """ Check validity of returned OPTiMaDe API version
        :param api_version: tuple: integers, e.g. (0,9,5)
        :return: valid, old: booleans
        """
        old = False
        valid = api_version >= self.min_api_version
        if api_version < self.min_api_version:
            self.query_message.value = "OPTiMaDe API {} is not supported. " \
                                "Must be at least {}.".format(self.ver_to_str(api_version), self.ver_to_str(self.min_api_version))
        elif api_version == self.min_api_version:
            old = True
        
        return valid, old

    def _update_drop_structure(self):
        """ Update dropdown of structures with list of structures in self.structures """
        self.drop_structure.options = self.structures
        if len(self.structures) > 1:
            self.drop_structure.value = self.structures[1][1]

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
            self._update_custom_url()
        
        # Update status message and query database
        self.query_message.value = "Quering the database ... "
        response, api_version = self.query(idn=idn, formula=formula)
        
        # API version check
        valid, old = self._check_api_version(api_version)

        # Check number of results
        more_data = response["meta"]["more_data_available"]
        if more_data:
            avail = response["meta"]["data_available"]
            extra_msg = "<br/>{} results found, only providing the first {}. " \
                        "Please use filters to reduce the number of results found.".format(avail, self.RESPONSE_LIMIT)

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
                    
                try:
                    formula = entry_cif.get_ase().get_chemical_formula()
                except Exception:
                    count += 1
                    non_valid_count += 1
                    continue
                
                attributes = None
                
            else:
                ## API version 0.9.7a
                
                if self._valid_entry(entry):
                    structure = self.get_structure(entry)
                    attributes = self.get_attributes(entry)
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
                                "structure": attributes,
                                "url": cif_url,
                                "id": idn,
                            }
                        )
            self.structures.append(entry_add)
            count += 1
        
        if valid:
            self.query_message.value = "{} structure(s) found" \
                                       " ... {} non-valid structure(s) found " \
                                       "(partial occupancies are not allowed)".format(count, non_valid_count)
        if more_data:
            self.query_message.value += extra_msg

        self._update_drop_structure()

    def _update_structure_data(self, structure):
        """ Update structure data output
        Update dict output that will be shown in an Output widget next to the nglview
        :param structure: new structure, whose properties will be put into self.structure_data (None if from COD)
        """
        if structure:
            self.structure_data.update(structure)
        else:
            # COD
            self.structure_data.update(self._init_structure_data())

    def refresh_structure_data(self, structure):
        """ Output structure data
        Show dict defined in self.structure_data in an Output widget next to the nglview
        :param structure: new structure to be displayed (None if from COD)
        """
        # TODO: Make keys static, only change values
        
        self._update_structure_data(structure)

        with self.data_output:
            clear_output()
            
            for k, v in self.structure_data.items():
                if k != "unit_cell":
                    key = str(k).replace("_", " ")

                    out = ipw.HTML("<b>{}</b>: {}<br/>".format(key.capitalize(), v))

                    display(out)
            
            # Unit cell
            out = r"<b>Unit cell</b>: "
            if isinstance(self.structure_data["unit_cell"], list):
                uc = self.structure_data["unit_cell"]
                out += r"$\Bigl(\begin{smallmatrix} "
                for i in range(len(uc[0])-1):
                    row = list()
                    for vector in uc:
                        row.append(vector[i])
                    out += r" & ".join([str(x) for x in row])
                    out += r" \\ "
                row = list()
                for vector in uc:
                    row.append(vector[-1])
                out += r" & ".join([str(x) for x in row])
                out += r" \end{smallmatrix} \Bigr)$"
                
            out = ipw.HTMLMath(out)
            display(out)


    def refresh_structure_view(self):
        # pylint: disable=protected-access
        for comp_id in self.viewer._ngl_component_ids:
            self.viewer.remove_component(comp_id)

        self.viewer.add_component(nglview.ASEStructure(self.atoms.get_ase())) # adds ball+stick
        self.viewer.add_unitcell() # pylint: disable=no-member
        self.viewer.center()

    def _on_change_struct(self, structs):
        """ Update "result view" to chosen structure
        :param structs: Dropdown widget containing list of structure entries
        """
        # indx = structs['owner'].index
        new_element = structs['new']
        if new_element['status'] is False:
            self.btn_store.disabled = True
            return
        self.data_output.layout.visibility = "visible"
        self.btn_store.disabled = False
        self.atoms = new_element['cif']
        formula = self.atoms.get_ase().get_chemical_formula()
        
        # search for existing calculations using chosen structure
        qb = QueryBuilder()
        qb.append(StructureData)
        qb.append(Calculation, filters={'extras.formula':formula}, descendant_of=StructureData)
        qb.order_by({Calculation:{'ctime':'desc'}})
        for n in qb.iterall():
            calc = n[0]
            print("Found existing calculation: PK=%d | %s"%(calc.pk, calc.get_extra("structure_description")))
        #     thumbnail = b64decode(calc.get_extra("thumbnail"))
        #     display(Image(data=thumbnail))
        # struct_url = new_element['url'].split('.cif')[0]+'.html'
        # if new_element['url'] != "":
        #     self.link.value='<a href="{}" target="_blank">{} entry {}</a>'.format(struct_url, self.query_db["name"], new_element['id'])
        # else:
        #     self.link.value='{} entry {}'.format(self.query_db["name"], new_element['id'])
        self.refresh_structure_view()
        self.refresh_structure_data(new_element["structure"])

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

    # pylint: disable=unused-argument
    def _on_click_store(self, change):
        self.store_structure(
            description=self.structure_description.value)

    def store_structure(self, description=None):
        with self.store_out:
            clear_output()
            if self.atoms is None:
                print ("Specify a structure first!")
                return
            
            if self.data_format.value == "CifData":
                s=self.atoms.copy()
            elif self.data_format.value == "StructureData":
                s = StructureData(ase=self.atoms.get_ase())
                # ensure that tags got correctly translated into kinds 
                for t1, k in zip(self.atoms.get_ase().get_tags(), s.get_site_kindnames()):
                    t2 = int(k[-1]) if k[-1].isnumeric() else 0
                    assert t1==t2

                # Description
                if description is None:
                    s.description = s.get_chemical_formula()
                else:
                    s.description = description
            
            s.store()
            print("Stored in AiiDA: "+repr(s))

        # # determine data source
        # if name.endswith('.cif'):
        #     source_format = 'CIF'
        # else:
        #     source_format = 'ASE'

        # # perform conversion
        # if self.data_format.value == 'CifData':
        #     if source_format == 'CIF':
        #         structure_node = CifData(
        #             file=self.tmp_folder + '/' + name,
        #             scan_type='flex',
        #             parse_policy='lazy')
        #     else:
        #         structure_node = CifData()
        #         structure_node.set_ase(structure_ase)
        # else:  # Target format is StructureData
        #     structure_node = StructureData(ase=structure_ase)

        #     #TODO: Figure out whether this is still necessary for StructureData
        #     # ensure that tags got correctly translated into kinds
        #     for t1, k in zip(structure_ase.get_tags(),
        #                      structure_node.get_site_kindnames()):
        #         t2 = int(k[-1]) if k[-1].isnumeric() else 0
        #         assert t1 == t2
        # structure_node.label = ".".join(name.split('.')[:-1])
        # structure_node.store()
        # self.structure_node = structure_node
        # print("Stored in AiiDA: " + repr(structure_node))

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
