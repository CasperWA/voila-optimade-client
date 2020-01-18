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
    python_requires=">=3.6",
    install_requires=["aiidalab~=19.11.0a", "optimade~=0.3.1", "requests",],
    extras_require={"dev": DEV, "testing": TESTING},
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
