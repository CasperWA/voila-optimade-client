from typing import Dict

from optimade.models import Species as OptimadeStructureSpecies
from optimade.models import StructureResource as OptimadeStructure

from ase import Atoms, Atom


__all__ = ("get_ase_atoms",)


def get_ase_atoms(optimade_structure: OptimadeStructure) -> Atoms:
    """ Get ASE Atoms from OPTiMaDe structure

    NOTE: Cannot handle partial occupancies (this includes vacancies)

    :param optimade_structure: OPTiMaDe structure
    :return: ASE.Atoms
    """

    attributes = optimade_structure.attributes

    species: Dict[str, OptimadeStructureSpecies] = {
        species.name: species for species in attributes.species
    }

    atoms = []
    for site_number in range(attributes.nsites):
        species_name = attributes.species_at_sites[site_number]
        site = attributes.cartesian_site_positions[site_number]

        current_species = species[species_name]

        atoms.append(
            Atom(symbol=species_name, position=site, mass=current_species.mass)
        )

    return Atoms(
        symbols=atoms, cell=attributes.lattice_vectors, pbc=attributes.dimension_types
    )
