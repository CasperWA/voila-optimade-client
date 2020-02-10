import ipywidgets as ipw
import traitlets

import ase
from aiida.orm import StructureData


class OptimadeResultsWidget(ipw.Tab):
    """Summarize OPTiMaDe entity"""

    entity = traitlets.Union(
        [traitlets.Instance(ase.Atoms), traitlets.Instance(StructureData)],
        allow_none=True,
    )

    def __init__(self, debug: bool = False, **kwargs):
        self.debug = debug

        sections = {"tab title": ipw.Widget()}

        super().__init__(
            children=list(sections.values()), layout=ipw.Layout(width="100%"), **kwargs
        )
        for index, title in enumerate(sections):
            self.set_title(index, title)
