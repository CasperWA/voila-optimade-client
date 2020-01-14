import traitlets
import ipywidgets as widgets
import ase


class StructureWidgetTemplate(widgets.Widget):

    structure = traitlets.Instance(ase.atoms.Atoms, allow_none=True)
