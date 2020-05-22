from setuptools import setup, find_packages

TESTING = [
    "pytest",
    "pytest-cov",
    "codecov",
    "requests~=2.23",
    "jupyterlab~=2.1",
    "ipywidgets~=7.5",
    "nglview~=2.7",
    "numpy~=1.18",
    "pandas~=1.0",
    "ase~=3.19",
    "appmode",
    "voila",
]
DEV = ["pylint", "black", "pre-commit", "invoke"] + TESTING

setup(
    name="aiidalab-optimade",
    version="3.2.0",
    packages=find_packages(),
    license="MIT License",
    author="Casper Welzel Andersen",
    python_requires=">=3.6",
    install_requires=["optimade~=0.9.1"],
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
