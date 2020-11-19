import base64
import tempfile
from typing import Union
import warnings

import ipywidgets as ipw
import traitlets

from ipywidgets_extended import DropdownExtended
import nglview

try:
    from ase import Atoms as aseAtoms
except ImportError:
    aseAtoms = None

try:
    from pymatgen import Molecule as pymatgenMolecule, Structure as pymatgenStructure
except ImportError:
    pymatgenMolecule = None
    pymatgenStructure = None

from optimade.adapters import Structure
from optimade.models import StructureFeatures

from optimade_client import exceptions
from optimade_client.logger import LOGGER
from optimade_client.subwidgets import (
    StructureSummary,
    StructureSites,
)
from optimade_client.utils import ButtonStyle
from optimade_client.warnings import OptimadeClientWarning


class OptimadeSummaryWidget(ipw.Box):
    """Overview of OPTIMADE entity (focusing on structure)
    Combined view of structure viewer and tabs for detailed information.

    Set `direction` to "horizontal" or "vertical" to show the two widgets either
    horizontally or vertically, respectively.
    """

    entity = traitlets.Instance(Structure, allow_none=True)

    def __init__(
        self,
        direction: str = None,
        button_style: Union[ButtonStyle, str] = None,
        **kwargs,
    ):
        if direction and direction == "horizontal":
            direction = "row"
            layout_viewer = {
                "width": "50%",
                "height": "auto",
                "margin": "0px 0px 0px 0px",
                "padding": "0px 0px 10px 0px",
            }
            layout_tabs = {
                "width": "50%",
                "height": "345px",
            }
        else:
            direction = "column"
            layout_viewer = {
                "width": "auto",
                "height": "auto",
                "margin": "0px 0px 0px 0px",
                "padding": "0px 0px 10px 0px",
            }
            layout_tabs = {
                "width": "auto",
                "height": "345px",
            }

        if button_style:
            if isinstance(button_style, str):
                button_style = ButtonStyle[button_style.upper()]
            elif isinstance(button_style, ButtonStyle):
                pass
            else:
                raise TypeError(
                    "button_style should be either a string or a ButtonStyle Enum. "
                    f"You passed type {type(button_style)!r}."
                )
        else:
            button_style = ButtonStyle.DEFAULT

        kwargs.pop("layout", None)

        self.viewer = StructureViewer(
            layout=layout_viewer, button_style=button_style, **kwargs
        )
        self.summary = SummaryTabs(layout=layout_tabs, **kwargs)

        self.children = (self.viewer, self.summary)

        super().__init__(
            children=self.children,
            layout={
                "display": "flex",
                "flex_flow": direction,
                "align_items": "stretch",
                "width": "100%",
                "height": "auto",
            },
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
<input type="button" class="p-Widget jupyter-widgets jupyter-button widget-button mod-{button_style}" value="Download" title="Download structure" style="width:auto;" {disabled}
onclick="var link = document.createElement('a');
link.href = 'data:charset={encoding};base64,{data}';
link.download = '{filename}';
document.body.appendChild(link);
link.click();
document.body.removeChild(link);" />
"""

    def __init__(self, button_style: Union[ButtonStyle, str] = None, **kwargs):
        if button_style:
            if isinstance(button_style, str):
                self._button_style = ButtonStyle[button_style.upper()]
            elif isinstance(button_style, ButtonStyle):
                self._button_style = button_style
            else:
                raise TypeError(
                    "button_style should be either a string or a ButtonStyle Enum. "
                    f"You passed type {type(button_style)!r}."
                )
        else:
            self._button_style = ButtonStyle.DEFAULT

        self._initialize_options()
        options = self._formats
        options.insert(0, ("Select a format", {}))
        self.dropdown = DropdownExtended(options=options, layout={"width": "auto"})
        self.download_button = ipw.HTML(
            self._download_button_format.format(
                button_style=self._button_style.value,
                disabled="disabled",
                encoding="",
                data="",
                filename="",
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
            LOGGER.debug(
                "Got no new structure for DownloadChooser (change['new']=%s).",
                change["new"],
            )
            self.reset()
        else:
            LOGGER.debug(
                "Got new structure for DownloadChooser: id=%s", change["new"].id
            )
            self._update_options()
            self.unfreeze()

    def _initialize_options(self) -> None:
        """Initialize options according to installed packages"""
        for imported_object, adapter_format in [
            (aseAtoms, "ase"),
            (pymatgenStructure, "pymatgen"),
        ]:
            if imported_object is None:
                LOGGER.debug("%s not recognized to be installed.", adapter_format)
                self._formats = [
                    option
                    for option in self._formats
                    if option[1].get("adapter_format", "") != adapter_format
                ]

    def _update_options(self) -> None:
        """Update options according to chosen structure"""
        disabled_options = []
        if StructureFeatures.DISORDER in self.structure.structure_features:
            # Disordered structures not usable with ASE
            LOGGER.debug(
                "'disorder' found in the structure's structure_features (%s)",
                self.structure.structure_features,
            )
            disabled_options = [
                label
                for label, value in self._formats
                if value.get("adapter_format", "") == "ase"
            ]
        LOGGER.debug(
            "Will disable the following dropdown options: %s", disabled_options
        )
        self.dropdown.disabled_options = disabled_options

    def _update_download_button(self, change: dict):
        """Update Download button with correct onclick value

        The whole parsing process from `Structure` to desired format, is wrapped in a try/except,
        which is further wrapped in a `warnings.catch_warnings()`.
        This is in order to be able to log any warnings that might be thrown by the adapter in
        `optimade-python-tools` and/or any related exceptions.
        """
        desired_format = change["new"]
        LOGGER.debug(
            "Updating the download button with desired format: %s", desired_format
        )
        if not desired_format or desired_format is None:
            self.download_button.value = self._download_button_format.format(
                button_style=self._button_style.value,
                disabled="disabled",
                encoding="",
                data="",
                filename="",
            )
            return

        output = None
        with warnings.catch_warnings():
            warnings.filterwarnings("error")

            try:
                output = getattr(
                    self.structure, f"as_{desired_format['adapter_format']}"
                )
            except RuntimeWarning as warn:
                if "numpy.ufunc size changed" in str(warn):
                    # This is an issue that may occur if using pre-built binaries for numpy and
                    # scipy. It can be resolved by uninstalling scipy and reinstalling it with
                    # `--no-binary :all:` when using pip. This will recompile all related binaries
                    # using the currently installed numpy version.
                    # However, it shouldn't be critical, hence here the warning will be ignored.
                    warnings.filterwarnings("default")
                    output = getattr(
                        self.structure, f"as_{desired_format['adapter_format']}"
                    )
                else:
                    self.download_button.value = self._download_button_format.format(
                        button_style=self._button_style.value,
                        disabled="disabled",
                        encoding="",
                        data="",
                        filename="",
                    )
                    warnings.warn(OptimadeClientWarning(warn))
            except Warning as warn:
                self.download_button.value = self._download_button_format.format(
                    button_style=self._button_style.value,
                    disabled="disabled",
                    encoding="",
                    data="",
                    filename="",
                )
                warnings.warn(OptimadeClientWarning(warn))
            except Exception as exc:
                self.download_button.value = self._download_button_format.format(
                    button_style=self._button_style.value,
                    disabled="disabled",
                    encoding="",
                    data="",
                    filename="",
                )
                if isinstance(exc, exceptions.OptimadeClientError):
                    raise exc
                # Else wrap the exception to make sure to log it.
                raise exceptions.OptimadeClientError(exc)

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

        filename = f"optimade_structure_{self.structure.id}{desired_format['ext']}"

        if isinstance(output, str):
            output = output.encode(encoding)
        data = base64.b64encode(output).decode()

        self.download_button.value = self._download_button_format.format(
            button_style=self._button_style.value,
            disabled="",
            encoding=encoding,
            data=data,
            filename=filename,
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
        LOGGER.debug("Will unfreeze %s", self.__class__.__name__)
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

        button_style = kwargs.pop("button_style", None)
        self.download = DownloadChooser(button_style=button_style, **kwargs)

        layout = kwargs.pop(
            "layout",
            {
                "width": "auto",
                "height": "auto",
                "margin": "0px 0px 0px 0px",
                "padding": "0px 0px 10px 0px",
            },
        )

        super().__init__(
            children=(self.viewer_box, self.download),
            layout=layout,
            **kwargs,
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

        layout = kwargs.pop(
            "layout",
            {
                "width": "auto",
                "height": "345px",
            },
        )

        super().__init__(
            children=tuple(_[1] for _ in self.sections),
            layout=layout,
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
