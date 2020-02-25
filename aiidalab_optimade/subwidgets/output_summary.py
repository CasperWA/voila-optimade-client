import re
from typing import Match, List
import ipywidgets as ipw
import traitlets

import pandas as pd

from aiida.orm import StructureData


__all__ = ("StructureDataSummary", "StructureDataSites")


class StructureDataSummary(ipw.VBox):
    """StructureData Summary Output
    Show structure data as a set of HTML widgets in a VBox widget.
    """

    structure = traitlets.Instance(StructureData, allow_none=True)

    _output_format = "<b>{title}</b>: {value}"
    _widget_data = {
        "Chemical formula (hill)": ipw.HTMLMath(),
        "Elements": ipw.HTML(),
        "Number of sites": ipw.HTML(),
        "Unit cell": ipw.HTMLMath(),
        "Unit cell volume": ipw.HTML(),
    }

    def __init__(self, structure: StructureData = None, **kwargs):
        super().__init__(children=tuple(self._widget_data.values()), **kwargs)
        self.observe(self._on_change_structure, names="structure")
        self.structure = structure

    def _on_change_structure(self, change):
        """Update output according to change in `data`"""
        new_structure = change["new"]
        if new_structure is None:
            for widget in self._widget_data.values():
                widget.value = ""
            return
        self._update_output()

    def _update_output(self):
        """Update widget values in self._widget_data"""
        data = self._extract_data_from_structure()
        for field, widget in self._widget_data.items():
            widget.value = self._output_format.format(
                title=field, value=data.get(field, "")
            )

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.structure = None

    def _extract_data_from_structure(self) -> dict:
        """Extract and return desired data from StructureData"""
        return {
            "Chemical formula (hill)": self._chemical_formula(
                self.structure.get_formula(mode="hill_compact")
            ),
            "Elements": ", ".join(sorted(self.structure.get_symbols_set())),
            "Number of sites": str(len(self.structure.sites)),
            "Unit cell": self._unit_cell(self.structure.cell),
            "Unit cell volume": f"{self.structure.get_cell_volume():.2f} Å",
        }

    @staticmethod
    def _chemical_formula(formula: str) -> str:
        """Format chemical formula to look pretty with ipywidgets.HTMLMath"""

        def wrap_number(number: Match) -> str:
            return f"<sub>{number.group(0)}</sub>"

        return re.sub(r"[0-9]+", repl=wrap_number, string=formula)

    @staticmethod
    def _unit_cell(unitcell: list) -> str:
        """Format unit cell to look pretty with ipywidgets.HTMLMath"""
        out = r"$\Bigl(\begin{smallmatrix} "
        for i in range(len(unitcell[0]) - 1):
            row = list()
            for vector in unitcell:
                row.append(vector[i])
            out += r" & ".join([str(_) for _ in row])
            out += r" \\ "
        row = list()
        for vector in unitcell:
            row.append(vector[-1])
        out += r" & ".join([str(_) for _ in row])
        out += r" \end{smallmatrix} \Bigr)$"

        return out


class StructureDataSites(ipw.HTML):
    """StructureData Sites Output
    Reimplements the viewer for AiiDA Dicts
    """

    structure = traitlets.Instance(StructureData, allow_none=True)

    def __init__(self, structure: StructureData = None, **kwargs):
        # For more information on how to control the table appearance please visit:
        # https://css-tricks.com/complete-guide-table-element/
        self._style = """
        <style>
            .df { border: none; }
            .df tbody tr:nth-child(odd) { background-color: #e5e7e9; }
            .df tbody tr:nth-child(odd):hover { background-color:   #f5b7b1; }
            .df tbody tr:nth-child(even):hover { background-color:  #f5b7b1; }
            .df tbody td { min-width: 300px; text-align: center; border: none }
            .df th { text-align: center; border: none;  border-bottom: 1px solid black;}
        </style>
        """
        pd.set_option("max_colwidth", 100)

        super().__init__(layout=ipw.Layout(width="auto"), **kwargs)
        self.observe(self._on_change_structure, names="structure")
        self.structure = structure

    def _on_change_structure(self, change: dict):
        """When traitlet 'sites' is updated"""
        if change["new"] is None:
            self.value = ""
        else:
            self.value = self._style
            dataf = pd.DataFrame(
                self._format_sites(), columns=["Elements", "Occypancy", "Position"]
            )
            self.value += dataf.to_html(classes="df", index=False)

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.structure = None

    def _format_sites(self) -> List[str]:
        """Format AiiDA StructureData into list of formatted HTML strings"""
        res = []
        for site in self.structure.sites:
            for kind in self.structure.kinds:
                if kind.name == site.kind_name:
                    site_kind = kind
                    break
            else:
                raise Exception(
                    f"Kind cannot be found for site: {site}. Kinds: {self.structure.kinds}"
                )
            occupancies = site_kind.weights
            if re.match(r".*X[^e]", site.kind_name):
                occupancies.append(round(1.0 - sum(occupancies), 2))

            res.append(
                (
                    ", ".join([str(_) for _ in site_kind.symbols]),
                    ", ".join([str(_) for _ in occupancies]),
                    str(site.position),
                )
            )
        return res
