# -*- coding: utf-8 -*-

# Python 2/3 compatibility
from __future__ import print_function
from __future__ import absolute_import

# Imports
# import requests
# pylint: disable=import-error
import tempfile
import ipywidgets as ipw
import nglview
import ase.io
from aiida.orm.data.structure import StructureData #, Kind
from aiida.orm.data.cif import CifData


class OptimadeWidget(ipw.VBox):

    DATA_FORMATS = ('StructureData', 'CifData')

    def __init__(self, node_class=None, **kwargs):
        """ OPTiMaDe Structure Retrieval Widget
        Upload a structure according to OPTiMaDe API, mininmum v0.9.7a

        :param text: Text to display on upload button
        :type text: str
        :param node_class: AiiDA node class for storing the structure.
            Possible values: 'StructureData', 'CifData' or None (let the user decide).
            Note: If your workflows require a specific node class, better fix it here.
        """

        self.viewer = nglview.NGLWidget()
        self.btn_store = ipw.Button(
            description='Store in AiiDA', disabled=True)
        self.structure_description = ipw.Text(
            placeholder="Description (optional)")
        self.filename = "test"

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

        children = [self.viewer, store]

        super(OptimadeWidget, self).__init__(
            children=children, **kwargs)

        self.btn_store.on_click(self._on_click_store)

        from aiida import load_dbenv, is_dbenv_loaded
        from aiida.backends import settings
        if not is_dbenv_loaded():
            load_dbenv(profile=settings.AIIDADB_PROFILE)

    # pylint: disable=unused-argument
    def _on_file_upload(self, change):
        self.tmp_folder = tempfile.mkdtemp()
        # tmp = self.tmp_folder + '/' + self.file_upload.filename
        # with open(tmp, 'w') as f:
        #     f.write(self.file_upload.data)
        # self.select_structure(name=self.file_upload.filename)
        self.select_structure(name=self.filename)

    def select_structure(self, name):
        structure_ase = self.get_ase(self.tmp_folder + '/' + name)
        self.btn_store.disabled = False
        if structure_ase is None:
            self.structure_ase = None
            self.btn_store.disabled = True
            self.refresh_view()
            return

        self.structure_description.value = self.get_description(
            structure_ase, name)
        self.structure_ase = structure_ase
        self.refresh_view()

    def get_ase(self, fname):
        try:
            traj = ase.io.read(fname, index=":")
        except AttributeError:
            print("Looks like {} file does not contain structure coordinates".
                  format(fname))
            return None
        if len(traj) > 1:
            print(
                "Warning: Uploaded file {} contained more than one structure. I take the first one."
                .format(fname))
        return traj[0]

    def get_description(self, structure_ase, name):
        formula = structure_ase.get_chemical_formula()
        return "{} ({})".format(formula, name)

    def refresh_view(self):
        viewer = self.viewer
        # Note: viewer.clear() only removes the 1st component
        # pylint: disable=protected-access
        for comp_id in viewer._ngl_component_ids:
            viewer.remove_component(comp_id)

        viewer.add_component(nglview.ASEStructure(
            self.structure_ase))  # adds ball+stick
        # viewer.add_unitcell()

    # pylint: disable=unused-argument
    def _on_click_store(self, change):
        self.store_structure(
            self.filename,
            # self.file_upload.filename,
            description=self.structure_description.value)

    def store_structure(self, name, description=None):
        structure_ase = self.get_ase(self.tmp_folder + '/' + name)
        if structure_ase is None:
            return

        # determine data source
        if name.endswith('.cif'):
            source_format = 'CIF'
        else:
            source_format = 'ASE'

        # perform conversion
        if self.data_format.value == 'CifData':
            if source_format == 'CIF':
                structure_node = CifData(
                    file=self.tmp_folder + '/' + name,
                    scan_type='flex',
                    parse_policy='lazy')
            else:
                structure_node = CifData()
                structure_node.set_ase(structure_ase)
        else:  # Target format is StructureData
            structure_node = StructureData(ase=structure_ase)

            #TODO: Figure out whether this is still necessary for StructureData
            # ensure that tags got correctly translated into kinds
            for t1, k in zip(structure_ase.get_tags(),
                             structure_node.get_site_kindnames()):
                t2 = int(k[-1]) if k[-1].isnumeric() else 0
                assert t1 == t2
        if description is None:
            structure_node.description = self.get_description(
                structure_ase, name)
        else:
            structure_node.description = description
        structure_node.label = ".".join(name.split('.')[:-1])
        structure_node.store()
        self.structure_node = structure_node
        print("Stored in AiiDA: " + repr(structure_node))

    @property
    def node_class(self):
        return self.data_format.value

    @node_class.setter
    def node_class(self, value):
        self.data_format.value = value



# for entry in response["data"]:
#     if not valid:
#         ### Not a valid API version: too old API version ###
#         # While there may be several entries in response["data"]
#         # they will not be considered here, since there is no guarantee
#         # that they are readable/parseable
#         # So break, do not continue.
#         break
        
#     elif old:
#         ### API version 0.9.5 (specifically for CoD) ###
        
#         cif_url = entry["links"]["self"]
#         fn = requests.get(cif_url)
#         with tempfile.NamedTemporaryFile(mode='w+') as f:
#             f.write(fn.text)
#             f.flush()
#             entry_cif = CifData(file=f.name, parse_policy='lazy')
            
#         formula = entry_cif.get_ase().get_chemical_formula()
        
#     else:
#         ### API version 0.9.7a ###
        
#         attr = entry["attributes"]
#         valid_entry = True
        
#         s = StructureData(cell=attr["lattice_vectors"])
#         # Add Kinds
#         for kind in attr["species"].values():
#             # ASE cannot handle vacancies, therefore:
#             #     if a vacancy is present, the structure will be skipped,
#             #     and a message will be relayed
#             for i in range(len(kind["chemical_symbols"])):
#                 symbol = kind["chemical_symbols"][i]
#                 if symbol == "vacancy": # Not allowed in AiiDA
#                     valid_entry = False
#                     kind["chemical_symbols"].pop(i)
#                     kind["concentration"].pop(i)
            
#             s.append_kind(Kind(
#                 symbols=kind["chemical_symbols"],
#                 weights=kind["concentration"],
#                 mass=kind["mass"],
#                 name=kind["original_name"]
#             ))
