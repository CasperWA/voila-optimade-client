from IPython.display import display
import ipywidgets as ipw
import traitlets

import nglview

from aiidalab_optimade.converters import Structure
from aiidalab_optimade.subwidgets import (
    StructureSummary,
    StructureSites,
)


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
    """Download chooser for structure download"""

    chosen_format = traitlets.Tuple(traitlets.Unicode(), traitlets.Dict())
    structure = traitlets.Instance(Structure, allow_none=True)

    _formats = [
        ("Select a format", {}),
        (
            "Crystallographic Information File v1.0 (.cif)",
            {"ext": "cif", "adapter_format": "cif"},
        ),
        ("Protein Data Bank (.pdb)", {"ext": "pdb", "adapter_format": "pdb"}),
        # Not yet implemented:
        # (
        #     "Protein Data Bank, macromolecular CIF v1.1 (PDBx/mmCIF) (.cif)",
        #     {"ext": "cif", "adapter_format": "pdbx_mmcif"},
        # ),
    ]

    def __init__(self, **kwargs):
        self.dropdown = ipw.Dropdown(options=self._formats, width="100px")
        self.button = ipw.Button(
            description="Download", tooltip="Download structure", width="50px"
        )

        self.children = (self.dropdown, self.button)
        super().__init__(children=self.children, layout={"width": "auto"})
        self.reset()

        self.button.on_click(self._on_download_request)

    @traitlets.observe("structure")
    def _on_change_structure(self, change: dict):
        """Update widget when a new structure is chosen"""
        if change["new"] is None:
            self.reset()
        self.unfreeze()

    def _on_download_request(self, _):
        """Initiate download"""
        import base64
        from IPython.display import Javascript

        desired_format = self.dropdown.value
        if not desired_format:
            return

        output = getattr(self.structure, f"get_{desired_format['adapter_format']}")
        encoding = "utf-8"

        # Specifically for CIF: v1.x CIF needs to be in "latin-1" formatting
        if desired_format["ext"] == "cif":
            encoding = "latin-1"

        filename = f"optimade_structure_{self.structure.id}.{desired_format['ext']}"

        javascript = Javascript(
            f"""
var link = document.createElement('a');
link.href = "data:charset={encoding};base64,{base64.b64encode(output.encode(encoding)).decode()}"
link.download = "{filename}"
document.body.appendChild(link);
link.click();
document.body.removeChild(link);
"""
        )
        display(javascript)

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
            nglview.TextStructure(change["new"].get_pdb)
        )
        self.viewer.add_representation("ball+stick", aspectRatio=4)
        self.viewer.add_representation("unitcell")

    @traitlets.observe("layout")
    def _on_change_layout(self, _):
        """Resize NGL viewer when the VBox changes size"""
        self.viewer.layout.width = "100%"
        self.viewer.layout.height = "100%"
        self.viewer.layout.width = "auto"
        self.viewer.layout.height = "auto"
        # self.viewer.handle_resize()
        component = self._current_view if self._current_view is not None else 0
        self.viewer.center(component=component)

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
            layout=ipw.Layout(width="auto", height="235px"),
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
