import json
from pathlib import Path

from setuptools import setup, find_packages

PATH_TO_METADATA = Path(__file__).parent.joinpath("metadata.json").resolve()
with open(PATH_TO_METADATA, "r") as fp:
    METADATA = json.load(fp)

AIIDALAB = ["aiidalab-widgets-base~=1.0.0b2"]
TESTING = ["pytest", "pytest-cov", "codecov"]
DEV = ["pylint", "black", "pre-commit"] + TESTING

setup(
    name="aiidalab-optimade",
    version=METADATA["version"],
    packages=find_packages(),
    license="MIT Licence",
    author="The AiiDA Lab team",
    python_requires=">=3.6",
    install_requires=["optimade~=0.7", "requests~=2.23"],
    extras_require={"aiidalab": AIIDALAB, "dev": DEV, "testing": TESTING},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AiiDA",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Database :: Front-Ends",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
