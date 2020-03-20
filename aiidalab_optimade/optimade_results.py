import ipywidgets as ipw
import traitlets

from aiidalab_optimade.converters import Structure

from aiidalab_optimade.subwidgets import (
    # StructureDataSummary,
    # StructureDataSites,
    StructureSummary,
    StructureSites,
)


class OptimadeResultsWidget(ipw.Tab):
    """Summarize OPTiMaDe entity"""

    entity = traitlets.Instance(Structure, allow_none=True,)

    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug

        self.sections = (
            ("Structure details", StructureSummary()),
            ("Sites", StructureSites()),
        )

        super().__init__(
            children=tuple(_[1] for _ in self.sections),
            layout=ipw.Layout(width="100%"),
            **kwargs
        )
        for index, title in enumerate([_[0] for _ in self.sections]):
            self.set_title(index, title)

        self.observe(self._on_change_entity, names="entity")

    def _on_change_entity(self, change):
        """Update sections according to entity"""
        new_entity = change["new"]
        if new_entity is None:
            self.reset()
        else:
            for _, widgets in self.sections:
                widgets.structure = new_entity

    def freeze(self):
        """Disable widget"""
        for _, widgets in self.sections:
            widgets.freeze()

    def unfreeze(self):
        """Activate widget (in its current state)"""
        for _, widgets in self.sections:
            widgets.unfreeze()

    def reset(self):
        """Reset widget"""
        for _, widgets in self.sections:
            widgets.reset()
