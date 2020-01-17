import json
from pathlib import Path

from setuptools import setup, find_packages

PATH_TO_METADATA = Path(__file__).parent.joinpath("metadata.json").resolve()
with open(PATH_TO_METADATA, "r") as fp:
    METADATA = json.load(fp)

TESTING = ["pytest~=3.6", "pytest-cov", "codecov"]
DEV = ["pylint", "black", "pre-commit"] + TESTING

setup(
    name="aiidalab-optimade",
    version=METADATA["version"],
    packages=find_packages(),
    license="MIT Licence",
    author="The AiiDA Lab team",
    install_requires=["aiidalab~=19.11.0a", "requests"],
    extras_require={"dev": DEV, "testing": TESTING},
)
