import ipywidgets as ipw
import traitlets

import nglview

from aiidalab_optimade.converters import Structure
from aiidalab_optimade.subwidgets import (
    StructureSummary,
    StructureSites,
)


class OptimadeSummaryWidget(ipw.GridspecLayout):
    """Overview of OPTIMADE entity (focusing on structure)
    Combined view of structure viewer on the left and tabs on the right for detailed information
    """

    entity = traitlets.Instance(Structure, allow_none=True)

    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug

        self.viewer = StructureViewer(debug=self.debug, **kwargs)
        self.summary = SummaryTabs(debug=self.debug, **kwargs)

        super().__init__(
            n_rows=2,
            n_columns=1,
            layout={"width": "100%", "height": "auto", "min-width": "200px"},
            **kwargs,
        )
        self[0, :] = self.viewer
        self[1, :] = self.summary

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


class StructureViewer(ipw.VBox):
    """NGL structure viewer including download button"""

    structure = traitlets.Instance(Structure)

    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug
        self._current_view = None

        self.viewer = nglview.NGLWidget()
        self.viewer.camera = "orthographic"
        self.viewer.stage.set_parameters(mouse_preset="pymol")
        self.viewer_box = ipw.Box(
            children=(self.viewer,),
            layout={
                "width": "auto",
                "height": "auto",
                "border": "solid 0.5px",
                "margin": "0px",
                "padding": "0.5px",
            },
        )

        self.download_button = ipw.Button(
            description="Download", tooltip="Download structure"
        )

        super().__init__(children=(self.viewer_box, self.download_button))

        self.observe(self._on_change_structure, names="structure")

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

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        if self._current_view is not None:
            self.viewer.remove_component(self._current_view)
            self._current_view = None


class SummaryTabs(ipw.Tab):
    """Summarize OPTIMADE entity details in tabs"""

    entity = traitlets.Instance(Structure, allow_none=True)

    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug

        self.sections = (
            ("Structure details", StructureSummary()),
            ("Sites", StructureSites()),
        )

        super().__init__(
            children=tuple(_[1] for _ in self.sections),
            layout=ipw.Layout(width="auto", height="300px"),
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
