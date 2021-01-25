from pathlib import Path
from setuptools import setup, find_packages

MODULE_DIR = Path(__file__).resolve().parent
REQUIREMENTS_DIR = MODULE_DIR / "requirements"

with open(MODULE_DIR.joinpath("README.md")) as handle:
    README = handle.read()

with open(REQUIREMENTS_DIR.joinpath("requirements_base.txt")) as handle:
    BASE = [f"{_.strip()}" for _ in handle.readlines() if " " not in _]

with open(REQUIREMENTS_DIR.joinpath("requirements_server.txt")) as handle:
    SERVER = [f"{_.strip()}" for _ in handle.readlines()]

with open(REQUIREMENTS_DIR.joinpath("requirements_testing.txt")) as handle:
    TESTING = [f"{_.strip()}" for _ in handle.readlines()]

with open(REQUIREMENTS_DIR.joinpath("requirements_dev.txt")) as handle:
    DEV = [f"{_.strip()}" for _ in handle.readlines()] + TESTING + SERVER

setup(
    name="optimade-client",
    version="2021.1.25",
    license="MIT License",
    author="Casper Welzel Andersen",
    author_email="casper.andersen@epfl.ch",
    description="Voilà/Jupyter client for searching through OPTIMADE databases.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/CasperWA/voila-optimade-client",
    python_requires=">=3.6",
    packages=find_packages(),
    include_package_data=True,
    package_data={"optimade_client": ["img/*.png", "*.json"]},
    install_requires=BASE,
    extras_require={"dev": DEV, "testing": TESTING, "server": SERVER},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: AiiDA",
        "Framework :: Jupyter",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Database :: Front-Ends",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Software Development :: Widget Sets",
    ],
    entry_points={
        "console_scripts": [
            "optimade-client = optimade_client.cli.run:main",
        ],
    },
)
