from os import path
from json import load

from setuptools import setup, find_packages

path_to_metadata = path.join(path.dirname(__file__), "metadata.json")
with open(path_to_metadata, "r") as fp:
    metadata = load(fp)

TESTING = ["pytest~=3.6", "pytest-cov", "codecov"]
DEV = ["pylint", "black", "pre-commit"] + TESTING

setup(
    name="aiidalab-optimade",
    version=metadata["version"],
    packages=find_packages(),
    license="MIT Licence",
    author="The AiiDA Lab team",
    install_requires=["aiidalab~=19.11.0a", "requests"],
    extras_require={"dev": DEV, "testing": TESTING},
)
