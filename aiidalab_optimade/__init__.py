"""
OPTiMaDe

AiiDA Lab App that implements an OPTiMaDe client
"""
from os import path
from json import load

# pylint: disable=unused-import
from aiidalab_optimade.importer import OptimadeImporter  # noqa
from aiidalab_optimade.optimade import OptimadeStructureImport  # noqa

path_to_metadata = path.join(path.dirname(__file__), path.pardir, "metadata.json")
with open(path_to_metadata, "r") as fp:
    metadata = load(fp)

# In order to update version, change it in `metadata.json`
__version__ = metadata["version"]
