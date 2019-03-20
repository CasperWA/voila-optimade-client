# -*- coding: utf-8 -*-
"""
OPTiMaDe

AiiDA Lab App that implements an OPTiMaDe client
"""

# Python 2/3 compatibility
from __future__ import print_function
from __future__ import absolute_import
from __future__ import with_statement

from os import path
from json import load
from io import open

# pylint: disable=unused-import
from .importer import OptimadeImporter  # noqa
from .optimade import OptimadeStructureImport  # noqa

path_to_metadata = path.join(
    path.abspath(__name__), path.pardir, "metadata.json")
with open(path_to_metadata, 'r') as fp:
    metadata = load(fp)

# In order to update version, change it in `metadata.json`
__version__ = metadata['version']
