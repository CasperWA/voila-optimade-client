import base64
import tempfile
from typing import Union
import warnings

import ipywidgets as ipw
import traitlets

import nglview

from ase import Atoms as aseAtoms

try:
    from pymatgen import Molecule as pymatgenMolecule, Structure as pymatgenStructure
except ImportError:
    pymatgenMolecule = None
    pymatgenStructure = None

from optimade.adapters import Structure

from optimade_client import exceptions
from optimade_client.subwidgets import (
    StructureSummary,
    StructureSites,
)
from optimade_client.warnings import OptimadeClientWarning


class OptimadeSummaryWidget(ipw.VBox):
    """Overview of OPTIMADE entity (focusing on structure)
    Combined view of structure viewer on the left and tabs on the right for detailed information
    """

    entity = traitlets.Instance(Structure, allow_none=True)

    def __init__(self, **kwargs):
        self.viewer = StructureViewer(**kwargs)
        self.summary = SummaryTabs(**kwargs)

        self.children = (self.viewer, self.summary)
        super().__init__(
            children=self.children,
            layout=ipw.Layout(width="auto", height="auto"),
            **kwargs,
        )

        self.observe(self._on_change_entity, names="entity")

    def _on_change_entity(self, change):
        """Handle if entity is None"""
        new_entity = change["new"]
        if new_entity is None:
            self.reset()
        else:
            self.viewer.structure = new_entity
            self.summary.entity = new_entity

    def freeze(self):
        """Disable widget"""
        for widget in self.children:
            widget.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for widget in self.children:
            widget.unfreeze()

    def reset(self):
        """Reset widget"""
        for widget in self.children:
            widget.reset()


class DownloadChooser(ipw.HBox):
    """Download chooser for structure download

    To be able to have the download button work no matter the widget's final environment,
    (as long as it supports JavaScript), the very helpful insight from the following page is used:
    https://stackoverflow.com/questions/2906582/how-to-create-an-html-button-that-acts-like-a-link
    """

    chosen_format = traitlets.Tuple(traitlets.Unicode(), traitlets.Dict())
    structure = traitlets.Instance(Structure, allow_none=True)

    _formats = [
        (
            "Crystallographic Information File v1.0 (.cif)",
            {"ext": ".cif", "adapter_format": "cif"},
        ),
        ("Protein Data Bank (.pdb)", {"ext": ".pdb", "adapter_format": "pdb"}),
        (
            "Crystallographic Information File v1.0 [via ASE] (.cif)",
            {"ext": ".cif", "adapter_format": "ase", "final_format": "cif"},
        ),
        (
            "Protein Data Bank [via ASE] (.pdb)",
            {"ext": ".pdb", "adapter_format": "ase", "final_format": "proteindatabank"},
        ),
        (
            "XMol XYZ File [via ASE] (.xyz)",
            {"ext": ".xyz", "adapter_format": "ase", "final_format": "xyz"},
        ),
        (
            "XCrySDen Structure File [via ASE] (.xsf)",
            {"ext": ".xsf", "adapter_format": "ase", "final_format": "xsf"},
        ),
        (
            "WIEN2k Structure File [via ASE] (.struct)",
            {"ext": ".struct", "adapter_format": "ase", "final_format": "struct"},
        ),
        (
            "VASP POSCAR File [via ASE]",
            {"ext": "", "adapter_format": "ase", "final_format": "vasp"},
        ),
        (
            "Quantum ESPRESSO File [via ASE] (.in)",
            {"ext": ".in", "adapter_format": "ase", "final_format": "espresso-in"},
        ),
        # Not yet implemented:
        # (
        #     "Protein Data Bank, macromolecular CIF v1.1 (PDBx/mmCIF) (.cif)",
        #     {"ext": "cif", "adapter_format": "pdbx_mmcif"},
        # ),
    ]
    _download_button_format = """
<input type="button" class="jupyter-widgets jupyter-button widget-button" value="Download" title="Download structure" style="width:auto;" {disabled}
onclick="var link = document.createElement('a');
link.href = 'data:charset={encoding};base64,{data}';
link.download = '{filename}';
document.body.appendChild(link);
link.click();
document.body.removeChild(link);" />
"""

    def __init__(self, **kwargs):
        self.dropdown = ipw.Dropdown(options=("Select a format", {}), width="auto")
        self.download_button = ipw.HTML(
            self._download_button_format.format(
                disabled="disabled", encoding="", data="", filename=""
            )
        )

        self.children = (self.dropdown, self.download_button)
        super().__init__(children=self.children, layout={"width": "auto"})
        self.reset()

        self.dropdown.observe(self._update_download_button, names="value")

    @traitlets.observe("structure")
    def _on_change_structure(self, change: dict):
        """Update widget when a new structure is chosen"""
        if change["new"] is None:
            self.reset()
        else:
            self._update_options()
            self.unfreeze()

    def _update_options(self):
        """Update options according to chosen structure"""
        # Disordered structures not usable with ASE
        if "disorder" in self.structure.structure_features:
            options = sorted(
                [
                    option
                    for option in self._formats
                    if option[1].get("adapter_format", "") != "ase"
                ]
            )
            options.insert(0, ("Select a format", {}))
        else:
            options = sorted(self._formats)
            options.insert(0, ("Select a format", {}))
        self.dropdown.options = options

    def _update_download_button(self, change: dict):
        """Update Download button with correct onclick value

        The whole parsing process from `Structure` to desired format, is wrapped in a try/except,
        which is further wrapped in a `warnings.catch_warnings()`.
        This is in order to be able to log any warnings that might be thrown by the adapter in
        `optimade-python-tools` and/or any related exceptions.
        """
        desired_format = change["new"]
        if not desired_format or desired_format is None:
            self.download_button.value = self._download_button_format.format(
                disabled="disabled", encoding="", data="", filename=""
            )
            return

        with warnings.catch_warnings():
            warnings.filterwarnings("error")

            try:
                output = getattr(
                    self.structure, f"as_{desired_format['adapter_format']}"
                )

                if desired_format["adapter_format"] in (
                    "ase",
                    "pymatgen",
                    "aiida_structuredata",
                ):
                    # output is not a file, but a proxy Python class
                    func = getattr(self, f"_get_via_{desired_format['adapter_format']}")
                    output = func(output, desired_format=desired_format["final_format"])
                encoding = "utf-8"

                # Specifically for CIF: v1.x CIF needs to be in "latin-1" formatting
                if desired_format["ext"] == ".cif":
                    encoding = "latin-1"

                filename = (
                    f"optimade_structure_{self.structure.id}{desired_format['ext']}"
                )

                if isinstance(output, str):
                    output = output.encode(encoding)
                data = base64.b64encode(output).decode()
            except RuntimeWarning as warn:
                if "numpy.ufunc size changed" in str(warn):
                    # This is an issue that may occur if using pre-built binaries for numpy and scipy.
                    # It can be resolved by uninstalling scipy and reinstalling it with `--no-binary :all:`
                    # when using pip. This will recompile all related binaries using the currently
                    # installed numpy version.
                    # However, it shouldn't be critical, hence here the warning will be ignored.
                    pass
                else:
                    self.download_button.value = self._download_button_format.format(
                        disabled="disabled", encoding="", data="", filename=""
                    )
                    warnings.warn(OptimadeClientWarning(warn))
            except Warning as warn:
                self.download_button.value = self._download_button_format.format(
                    disabled="disabled", encoding="", data="", filename=""
                )
                warnings.warn(OptimadeClientWarning(warn))
            except Exception as exc:
                self.download_button.value = self._download_button_format.format(
                    disabled="disabled", encoding="", data="", filename=""
                )
                if isinstance(exc, exceptions.OptimadeClientError):
                    raise exc
                # Else wrap the exception to make sure to log it.
                raise exceptions.OptimadeClientError(exc)
            else:
                self.download_button.value = self._download_button_format.format(
                    disabled="", encoding=encoding, data=data, filename=filename
                )

    @staticmethod
    def _get_via_pymatgen(
        structure_molecule: Union[pymatgenStructure, pymatgenMolecule],
        desired_format: str,
    ) -> str:
        """Use pymatgen.[Structure,Molecule].to() method"""
        molecule_only_formats = ["xyz", "pdb"]
        structure_only_formats = ["xsf", "cif"]
        if desired_format in molecule_only_formats and not isinstance(
            structure_molecule, pymatgenMolecule
        ):
            raise exceptions.WrongPymatgenType(
                f"Converting to '{desired_format}' format is only possible with a pymatgen."
                f"Molecule, instead got {type(structure_molecule)}"
            )
        if desired_format in structure_only_formats and not isinstance(
            structure_molecule, pymatgenStructure
        ):
            raise exceptions.WrongPymatgenType(
                f"Converting to '{desired_format}' format is only possible with a pymatgen."
                f"Structure, instead got {type(structure_molecule)}."
            )

        return structure_molecule.to(fmt=desired_format)

    @staticmethod
    def _get_via_ase(atoms: aseAtoms, desired_format: str) -> Union[str, bytes]:
        """Use ase.Atoms.write() method"""
        with tempfile.NamedTemporaryFile(mode="w+b") as temp_file:
            atoms.write(temp_file.name, format=desired_format)
            res = temp_file.read()
        return res

    def freeze(self):
        """Disable widget"""
        for widget in self.children:
            widget.disabled = True

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for widget in self.children:
            widget.disabled = False

    def reset(self):
        """Reset widget"""
        self.dropdown.index = 0
        self.freeze()


class StructureViewer(ipw.VBox):
    """NGL structure viewer including download button"""

    structure = traitlets.Instance(Structure, allow_none=True)

    def __init__(self, **kwargs):
        self._current_view = None

        self.viewer = nglview.NGLWidget()
        self.viewer.camera = "orthographic"
        self.viewer.stage.set_parameters(mouse_preset="pymol")
        self.viewer_box = ipw.Box(
            children=(self.viewer,),
            layout={
                "width": "auto",
                "height": "auto",
                "border": "solid 0.5px darkgrey",
                "margin": "0px",
                "padding": "0.5px",
            },
        )

        self.download = DownloadChooser(**kwargs)

        super().__init__(
            children=(self.viewer_box, self.download),
            layout={
                "width": "auto",
                "height": "auto",
                "margin": "0px 0px 0px 0px",
                "padding": "0px 0px 10px 0px",
            },
        )

        self.observe(self._on_change_structure, names="structure")

        traitlets.dlink((self, "structure"), (self.download, "structure"))

    def _on_change_structure(self, change):
        """Update viewer for new structure"""
        self.reset()
        self._current_view = self.viewer.add_structure(
            nglview.TextStructure(change["new"].as_pdb)
        )
        self.viewer.add_representation("ball+stick", aspectRatio=4)
        self.viewer.add_representation("unitcell")

    def freeze(self):
        """Disable widget"""
        self.download.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        self.download.unfreeze()

    def reset(self):
        """Reset widget"""
        self.download.reset()
        if self._current_view is not None:
            self.viewer.clear()
            self.viewer.remove_component(self._current_view)
            self._current_view = None


class SummaryTabs(ipw.Tab):
    """Summarize OPTIMADE entity details in tabs"""

    entity = traitlets.Instance(Structure, allow_none=True)

    def __init__(self, **kwargs):
        self.sections = (
            ("Structure details", StructureSummary()),
            ("Sites", StructureSites()),
        )

        super().__init__(
            children=tuple(_[1] for _ in self.sections),
            layout=ipw.Layout(width="auto", height="345px"),
            **kwargs,
        )
        for index, title in enumerate([_[0] for _ in self.sections]):
            self.set_title(index, title)

        for widget in self.children:
            ipw.dlink((self, "entity"), (widget, "structure"))

    def freeze(self):
        """Disable widget"""
        for widget in self.children:
            widget.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for widget in self.children:
            widget.unfreeze()

    def reset(self):
        """Reset widget"""
        for widget in self.children:
            widget.reset()
