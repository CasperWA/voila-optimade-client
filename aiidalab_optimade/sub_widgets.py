# -*- coding: utf-8 -*-

# Python 2/3 compatibility
from __future__ import print_function
from __future__ import absolute_import
from __future__ import with_statement

# Imports
# pylint: disable=import-error
import ipywidgets as ipw

class StructureDataOutput(ipw.VBox):

    def __init__(self, data=None, **kwargs):

        self.data = data
        children=None

        super(StructureDataOutput, self).__init__(children=children, **kwargs)
