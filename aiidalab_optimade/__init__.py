"""
OPTiMaDe

AiiDA Lab App that implements an OPTiMaDe client
"""
import json
from pathlib import Path

from aiidalab_optimade.importer import OptimadeImporter  # noqa
from aiidalab_optimade.optimade_query import OptimadeQueryWidget  # noqa

PATH_TO_METADATA = Path(__file__).parent.parent.joinpath("metadata.json").resolve()
with open(PATH_TO_METADATA, "r") as fp:
    METADATA = json.load(fp)

# In order to update version, change it in `metadata.json`
__version__ = METADATA["version"]
