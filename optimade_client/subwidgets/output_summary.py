import re
from typing import Match, List, Dict
import ipywidgets as ipw
import traitlets

import pandas as pd

from optimade.adapters import Structure
from optimade.models import Species
from optimade.models.structures import Vector3D


__all__ = ("StructureSummary", "StructureSites")


def calc_cell_volume(cell: List[Vector3D]):
    """
    Calculates the volume of a cell given the three lattice vectors.

    It is calculated as cell[0] . (cell[1] x cell[2]), where . represents
    a dot product and x a cross product.

    NOTE: Taken from `aiida-core` at aiida.orm.nodes.data.structure

    :param cell: the cell vectors; the must be a 3x3 list of lists of floats,
            no other checks are done.

    :returns: the cell volume.
    """
    # returns the volume of the primitive cell: |a_1 . (a_2 x a_3)|
    a_1 = cell[0]
    a_2 = cell[1]
    a_3 = cell[2]
    a_mid_0 = a_2[1] * a_3[2] - a_2[2] * a_3[1]
    a_mid_1 = a_2[2] * a_3[0] - a_2[0] * a_3[2]
    a_mid_2 = a_2[0] * a_3[1] - a_2[1] * a_3[0]
    return abs(a_1[0] * a_mid_0 + a_1[1] * a_mid_1 + a_1[2] * a_mid_2)


class StructureSummary(ipw.VBox):
    """Structure Summary Output
    Show structure data as a set of HTML widgets in a VBox widget.
    """

    structure = traitlets.Instance(Structure, allow_none=True)

    _output_format = "<b>{title}</b>: {value}"
    _widget_data = {
        "Chemical formula": ipw.HTML(),
        "Elements": ipw.HTML(),
        "Number of sites": ipw.HTML(),
        "Unit cell volume": ipw.HTML(),
        "Unit cell": ipw.HTML(),
    }

    def __init__(self, structure: Structure = None, **kwargs):
        super().__init__(children=tuple(self._widget_data.values()), **kwargs)
        self.observe(self._on_change_structure, names="structure")
        self.structure = structure

    def _on_change_structure(self, change: dict):
        """Update output according to change in `data`"""
        if change["new"] is None:
            self.reset()
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
        for widget in self._widget_data.values():
            widget.value = ""

    def _extract_data_from_structure(self) -> dict:
        """Extract and return desired data from Structure"""
        return {
            "Chemical formula": self._add_style(
                self._chemical_formula(self.structure.chemical_formula_reduced)
            ),
            "Elements": self._add_style(", ".join(sorted(self.structure.elements))),
            "Number of sites": self._add_style(str(self.structure.nsites)),
            "Unit cell": self._unit_cell(self.structure.lattice_vectors),
            "Unit cell volume": (
                f"{self._add_style('%.2f' % calc_cell_volume(self.structure.lattice_vectors))}"
                " Å<sup>3</sup>"
            ),
        }

    @staticmethod
    def _add_style(html_value: str) -> str:
        """Wrap 'html_value' with HTML CSS style"""
        return (
            f'<span style="font-family:Courier New,Courier,monospace;">'
            f"{html_value}</span>"
        )

    @staticmethod
    def _chemical_formula(formula: str) -> str:
        """Format chemical formula to look pretty with ipywidgets.HTMLMath"""

        def wrap_number(number: Match) -> str:
            return f"<sub>{number.group(0)}</sub>"

        return re.sub(r"[0-9]+", repl=wrap_number, string=formula)

    @staticmethod
    def _unit_cell(unitcell: List[Vector3D]) -> str:
        """Format unit cell to HTML table"""
        style = """
<style>
    .df_uc { border: none; width: auto; display: inline; }
    .df_uc tbody tr:nth-child(odd) { background-color: #e5e7e9; }
    .df_uc tbody tr { font-family: "Courier New", Courier, monospace; font-style: normal; font-size: 12px; }
    .df_uc tbody td {
        min-width: 50px;
        text-align: center;
        border: 0px solid white;
        padding: 0px;
        padding-left: 5px;
        padding-right: 5px;
    }
    .df_uc th { text-align: center; border: none; border-bottom: 1px solid black; }
</style>
"""
        pd.set_option("max_colwidth", 100)

        format_unit_cell = []
        for number, vector in enumerate(unitcell):
            format_unit_cell.append(
                (
                    f"v<sub>{number + 1}</sub>",
                    f"{vector[0]:.5f}",
                    f"{vector[1]:.5f}",
                    f"{vector[2]:.5f}",
                )
            )

        data_frame = pd.DataFrame(
            format_unit_cell, columns=["v", "x (Å)", "y (Å)", "z (Å)"]
        )
        return style + data_frame.to_html(
            classes="df_uc",
            index=False,
            table_id="unit_cell",
            notebook=False,
            escape=False,
        )

    @staticmethod
    def _unit_cell_mathjax(unitcell: list) -> str:
        """Format unit cell to look pretty with ipywidgets.HTMLMath"""
        out = r"$\Bigl(\begin{smallmatrix} "
        for i in range(len(unitcell[0]) - 1):
            row = []
            for vector in unitcell:
                row.append(vector[i])
            out += r" & ".join([f"{_:.5f}" for _ in row])
            out += r" \\ "
        row = []
        for vector in unitcell:
            row.append(vector[-1])
        out += r" & ".join([str(_) for _ in row])
        out += r" \end{smallmatrix} \Bigr)$"

        return out


class StructureSites(ipw.HTML):
    """Structure Sites Output
    Reimplements the viewer for AiiDA Dicts (from AiiDAlab)
    """

    structure = traitlets.Instance(Structure, allow_none=True)

    def __init__(self, structure: Structure = None, **kwargs):
        # For more information on how to control the table appearance please visit:
        # https://css-tricks.com/complete-guide-table-element/
        #
        # Voila doesn't run the scripts, which should set a color upon choosing a row.
        # Furthermore, if it will ever work, one can remove the hover definition in the css styling.
        self._script = """
var row_color;

function index(el) {
  if (!el) return -1;
  var i = 0;
  do {
    i++;
  } while (el = el.previousElementSibling);
  return i;
}

function updateRowBackground(row) {
    if (row_color != 'rgb(244, 151, 184)') {
        row.style.backgroundColor = '#f497b8';
    } else {
        if ( index(row) % 2 == 0) {
            // even
            row.style.backgroundColor = 'white';
        } else {
            // odd
            row.style.backgroundColor = '#e5e7e9';
        }
    }
    row_color = getComputedStyle(row)['backgroundColor'];
}

function doYourStuff() {
    [].forEach.call( document.querySelectorAll('tbody > tr'), function(el) {
        el.addEventListener('click', function() {
            updateRowBackground(el);
        }, false);
    });
    [].forEach.call( document.querySelectorAll('tbody > tr'), function(el) {
        el.addEventListener('mouseover', function() {
            row_color = getComputedStyle(el)['backgroundColor'];
            this.style.backgroundColor = '#f5b7b1';
        }, false);
    });
    [].forEach.call( document.querySelectorAll('tbody > tr'), function(el) {
        el.addEventListener('mouseout', function() {
            el.style.backgroundColor = row_color;
        }, false);
    });
};

document.addEventListener('DOMContentLoaded', function() {
    doYourStuff();
});
// doYourStuff()
"""
        self._style = """
<style>
    .df { border: none; width: 100%; }
    .df tbody tr:nth-child(odd) { background-color: #e5e7e9; }
    .df tbody tr { font-family: "Courier New", Courier, monospace; font-style: normal; font-size: 12px; }
    .df tbody td {
        min-width: 50px;
        text-align: center;
        border: 0px solid white;
        padding: 0px;
        padding-left: 1px;
        padding-right: 1px;
    }
    .df th { text-align: center; border: none;  border-bottom: 1px solid black; }
</style>
"""
        pd.set_option("max_colwidth", 100)

        super().__init__(layout=ipw.Layout(width="auto", height="auto"), **kwargs)
        self.observe(self._on_change_structure, names="structure")
        self.structure = structure

    def _on_change_structure(self, change: dict):
        """When traitlet 'structure' is updated"""
        if change["new"] is None:
            self.reset()
        else:
            self.value = self._style
            dataf = pd.DataFrame(
                self._format_sites(),
                columns=["Elements", "Occupancy", "x (Å)", "y (Å)", "z (Å)"],
            )
            self.value += dataf.to_html(
                classes="df", index=False, table_id="sites", notebook=False
            )

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.value = ""

    def _format_sites(self) -> List[str]:
        """Format OPTIMADE Structure into list of formatted HTML strings
        Columns:
        - Elements
        - Occupancy
        - Position (x)
        - Position (y)
        - Position (z)
        """
        species: Dict[str, Species] = {_.name: _ for _ in self.structure.species.copy()}

        res = []
        for site_number in range(self.structure.nsites):
            symbol_name = self.structure.species_at_sites[site_number]

            for index, symbol in enumerate(species[symbol_name].chemical_symbols):
                if symbol == "vacancy":
                    species[symbol_name].chemical_symbols.pop(index)
                    species[symbol_name].concentration.pop(index)
                    break

            res.append(
                (
                    ", ".join(species[symbol_name].chemical_symbols),
                    ", ".join(
                        [
                            f"{occupation:.2f}"
                            for occupation in species[symbol_name].concentration
                        ]
                    ),
                    f"{self.structure.cartesian_site_positions[site_number][0]:.5f}",
                    f"{self.structure.cartesian_site_positions[site_number][1]:.5f}",
                    f"{self.structure.cartesian_site_positions[site_number][2]:.5f}",
                )
            )
        return res
