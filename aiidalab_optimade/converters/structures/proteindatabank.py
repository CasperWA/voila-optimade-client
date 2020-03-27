from typing import Dict

import numpy as np

from optimade.models import Species as OptimadeStructureSpecies
from optimade.models import StructureResource as OptimadeStructure


__all__ = ("get_pdb", "get_pdbx_mmcif")


def get_pdbx_mmcif(optimade_structure: OptimadeStructure) -> str:
    """ Write Protein Data Bank (PDB) structure in the new PDBx/mmCIF format from OPTIMADE structure

    Inspired by `ase.io.proteindatabank.write_proteindatabank()` in the ASE package.

    :param optimade_structure: OPTIMADE structure
    :return: str
    """
    # attributes = optimade_structure.attributes
    raise NotImplementedError(
        "get_pdbx_mmcif has not yet been implemented, sorry. "
        "Try instead get_pdb or get_cif for now."
    )


def get_pdb(  # pylint: disable=too-many-locals
    optimade_structure: OptimadeStructure,
) -> str:
    """ Write Protein Data Bank (PDB) structure in the old PDB format from OPTIMADE structure

    Inspired by `ase.io.proteindatabank.write_proteindatabank()` in the ASE package.

    :param optimade_structure: OPTIMADE structure
    :return: str
    """
    pdb = ""

    attributes = optimade_structure.attributes

    rotation = None
    if any(attributes.dimension_types):
        from aiidalab_optimade.converters.structures.utils import (
            cell_to_cellpar,
            cellpar_to_cell,
        )

        currentcell = np.asarray(attributes.lattice_vectors)
        cellpar = cell_to_cellpar(currentcell)
        exportedcell = cellpar_to_cell(cellpar)
        rotation = np.linalg.solve(currentcell, exportedcell)
        # ignoring Z-value, using P1 since we have all atoms defined explicitly
        pdb += (
            f"CRYST1{cellpar[0]:9.3f}{cellpar[1]:9.3f}{cellpar[2]:9.3f}"
            f"{cellpar[3]:7.2f}{cellpar[4]:7.2f}{cellpar[5]:7.2f} P 1\n"
        )

    # RasMol complains if the atom index exceeds 100000. There might
    # be a limit of 5 digit numbers in this field.
    pdb_maxnum = 100000
    bfactor = 1.0

    pdb += "MODEL     1\n"

    species: Dict[str, OptimadeStructureSpecies] = {
        species.name: species for species in attributes.species
    }

    sites = np.asarray(attributes.cartesian_site_positions)
    if rotation is not None:
        sites = sites.dot(rotation)

    for site_number in range(attributes.nsites):
        species_name = attributes.species_at_sites[site_number]
        site = sites[site_number]

        current_species = species[species_name]

        for index, symbol in enumerate(current_species.chemical_symbols):
            if symbol == "vacancy":
                continue

            label = species_name
            if len(current_species.chemical_symbols) > 1:
                if (
                    "vacancy" in current_species.chemical_symbols
                    and len(current_species.chemical_symbols) == 2
                ):
                    pass
                else:
                    label = f"{symbol}{index + 1}"

            pdb += (
                f"ATOM  {site_number % pdb_maxnum:5d} {label:4} MOL     1    "
                f"{site[0]:8.3f}{site[1]:8.3f}{site[2]:8.3f}"
                f"{current_species.concentration[index]:6.2f}"
                f"{bfactor:6.2f}          {symbol.upper():2}  \n"
            )
    pdb += "ENDMDL\n"

    return pdb
