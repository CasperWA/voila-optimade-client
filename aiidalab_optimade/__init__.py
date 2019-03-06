"""
OPTiMaDe

AiiDA Lab App that implements an OPTiMaDe client
"""

# pylint: disable=unused-import
from .importer import OptimadeImporter  # noqa
from .optimade import OptimadeStructureImport  # noqa

from json import loads

metadata = loads("metadata.json")

# In order to update version, change it in `metadata.json`
__version__ = metadata['version']
