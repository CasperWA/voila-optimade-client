import traitlets
import ipywidgets as ipw

try:
    from aiida.orm import StructureData
except ImportError:
    StructureData = object

from aiidalab_optimade.query_filter import OptimadeQueryFilterWidget
from aiidalab_optimade.query_provider import OptimadeQueryProviderWidget


class OptimadeQueryWidget(ipw.VBox):
    """Combined widget for OptimadeQuery*Widget"""

    structure = traitlets.Instance(StructureData, allow_none=True)

    def __init__(self, embedded: bool = True, **kwargs):
        providers = OptimadeQueryProviderWidget(embedded=embedded)
        filters = OptimadeQueryFilterWidget()

        ipw.dlink((providers, "database"), (filters, "database"))

        filters.observe(self.update_structure, names="structure")

        super().__init__(
            children=(providers, filters), layout={"width": "auto", "height": "auto"}
        )

    def update_structure(self, change: dict):
        """New structure chosen"""
        new_structure = change["new"]
        if new_structure is None:
            self.structure = None
        else:
            try:
                self.structure = new_structure.as_aiida_structuredata
            except AttributeError:
                raise
            except Exception:  # pylint: disable=broad-except
                self.structure = None
