# OPTIMADE client (in Jupyter)

[![Materials Cloud](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/aiidalab/aiidalab-optimade/v3/docs/resources/mcloud_badge.json)](https://dev-tools.materialscloud.org/optimadeclient/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/aiidalab/aiidalab-optimade/v3?urlpath=%2Fvoila%2Frender%2FOPTIMADE_general.ipynb)

Query for and import structures from [OPTIMADE](https://www.optimade.org) providers (COD, Materials Cloud, NoMaD, Materials Project, OQMD, and more ...)  
Note, this application handles the structures by converting them to ASE `Atoms` or AiiDA `StructureData` objects.

Current OPTIMADE API version: `0.10.1`

## Installation

This Jupyter-based app is intended to run in [AiiDA Lab](https://aiidalab.materialscloud.org) as well as inside a [Quantum Mobile](https://materialscloud.org/work/quantum-mobile) Virtual Machine.

Use the App Store in the [Home App](https://github.com/aiidalab/aiidalab-home) to install it.

## Usage

### Default

To use the OPTIMADE structure importer in your own AiiDA Lab app write the following:

```python
from aiidalab_optimade import OptimadeQueryWidget
from aiidalab_widgets_base.viewers import StructureDataViewer
from ipywidgets import dlink

structure_query = OptimadeQueryWidget()
structure_viewer = StructureDataViewer()

_ = dlink((structure_query, 'structure'), (structure_viewer, 'structure'))  # Save to `_` in order to suppress output in App Mode

display(structure_query)
display(structure_viewer)
```

This will immediately display a query widget with a dropdown of current structure databases that implements the OPTIMADE API.

Then you can filter to find a family of structures according to elements, number of elements, chemical formula, and more.
See the [OPTIMADE API specification document](https://github.com/Materials-Consortia/OPTiMaDe/blob/master/optimade.rst) for the full list and their description.

In order to get tabs delving deeper into the details of a particular structure, you can also import and display `OptimadeResultsWidget`.
The link for this should then look like: `_ = dlink((structure_query, 'structure'), (structure_output, 'entity'))`, given that you initiate `OptimadeResultsWidget` in the variable `structure_output`.

See the notebook [`OPTIMADE general.ipynb`](OPTIMADE_general.ipynb) for an example of how to set up a general purpose OPTIMADE importer.

### Embedded

The query widget may also be embedded into another app.  
For this a more "minimalistic" version of the widget can be initiated by passing `embedded=True` upon initiating the widget, i.e., `structure_query = OptimadeQueryWidget(embedded=True)`.

Everything else works the same - so you would still have to link up the query widget to the rest of your app.

### Run general application

Note, you will need to install the package (see above) before being able to run the application.

To run the notebook [`OPTIMADE general.ipynb`](OPTIMADE_general.ipynb) you can simply run [`run.sh`](run.sh) in a terminal and go to the printed URL (usually <http://localhost:8866>).

The notebook will be run in Voilà using Voilà's own `tornado`-based server.
The configuration will automatically be copied to Jupyter's configuration directory before starting the server.

```shell
/path/to/aiidalab-optimade$ ./run.sh
...
[Voila] Voila is running at:
http://localhost:8866/
...
```

## Configuration (Voilà)

For running the application (in Voilà) on Binder, the configuration can be found in the root file [`jupyter_config.json`](jupyter_config.json).  
If you wish to start the Voilà server locally with the same configuration, either copy the [`jupyter_config.json`](jupyter_config.json) file to your Jupyter config directory, renaming it to `voila.json` or pass the configurations when you start the server using the CLI.

Locate your Jupyter config directory:

```shell
$ jupyter --config-dir
/path/to/jupyter/config/dir
```

Example of passing configurations when you start the Voilà server using the CLI:

```shell
$ voila --enable_nbextensions=True --VoilaExecutePreprocessor.timeout=180 OPTIMADE_general.ipynb
...
[Voila] Voila is running at:
http://localhost:8866/
...
```

To see the full list of configurations you can call `voila` and pass `--help-all`.

## License

MIT. The terms of the license can be found in the LICENSE file.

## Contact

aiidalab@materialscloud.org
casper.andersen@epfl.ch
