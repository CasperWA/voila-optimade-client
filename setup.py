from pathlib import Path
from setuptools import setup, find_packages

MODULE_DIR = Path(__file__).resolve().parent

with open(MODULE_DIR.joinpath("requirements.txt")) as handle:
    REQUIREMENTS = [f"{_.strip()}" for _ in handle.readlines()]

with open(MODULE_DIR.joinpath("requirements_testing.txt")) as handle:
    TESTING = [f"{_.strip()}" for _ in handle.readlines()]

with open(MODULE_DIR.joinpath("requirements_dev.txt")) as handle:
    DEV = [f"{_.strip()}" for _ in handle.readlines()] + TESTING

setup(
    name="aiidalab-optimade",
    version="3.3.2",
    packages=find_packages(),
    license="MIT License",
    author="Casper Welzel Andersen",
    python_requires=">=3.6",
    install_requires=REQUIREMENTS,
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
        "Programming Language :: Python :: 3.8",
        "Topic :: Database :: Front-Ends",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
