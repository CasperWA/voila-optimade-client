"""
OPTiMaDe

AiiDA Lab App that implements an OPTiMaDe client
"""
from os import path
from json import load

# pylint: disable=unused-import
from aiidalab_optimade.importer import OptimadeImporter  # noqa
from aiidalab_optimade.optimade import OptimadeQueryWidget  # noqa

PATH_TO_METADATA = path.join(path.dirname(__file__), path.pardir, "metadata.json")
with open(PATH_TO_METADATA, "r") as fp:
    METADATA = load(fp)

# In order to update version, change it in `metadata.json`
__version__ = METADATA["version"]
