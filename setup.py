# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from setuptools import setup, find_packages

from os import path
from json import load
from io import open

path_to_metadata = path.join(path.dirname(__file__), "metadata.json")
with open(path_to_metadata, 'r') as fp:
    metadata = load(fp)

setup(
    name="aiidalab-optimade",
    version=metadata['version'],
    packages=find_packages(),
    license="MIT Licence",
    author="The AiiDA Lab team",
    install_requires=["aiidalab>=19.1.2", "requests==2.21.0"])
