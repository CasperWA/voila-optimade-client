# OPTIMADE client (in Voilà)

[![MaterialsCloud](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/CasperWA/voila-optimade-client/develop/docs/resources/mcloud_badge.json)](https://materialscloud.org/optimadeclient/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/CasperWA/voila-optimade-client/develop?urlpath=%2Fvoila%2Frender%2FOPTIMADE-Client.ipynb)

Query for and import structures from [OPTIMADE](https://www.optimade.org) providers (COD, MaterialsCloud, NoMaD, Materials Project, ODBX, OQMD, and more ...).

Current supported OPTIMADE API versions: `1.0.0`, `1.0.0-rc.2`, `1.0.0-rc.1`, `0.10.1`

## Run the client

This Jupyter-based app is intended to run either:

- In [AiiDAlab](https://aiidalab.materialscloud.org) as well as inside a [Quantum Mobile](https://materialscloud.org/work/quantum-mobile) Virtual Machine;
- As a [MaterialsCloud tool](https://materialscloud.org/optimadeclient/);
- As a standalone [MyBinder application](https://mybinder.org/v2/gh/CasperWA/voila-optimade-client/develop?urlpath=%2Fvoila%2Frender%2FOPTIMADE-Client.ipynb); or
- As a standalone local application (see more information about this below).

For AiiDAlab, use the App Store in the [Home App](https://github.com/aiidalab/aiidalab-home) to install it.

## Usage

### AiiDAlab

To use the OPTIMADE structure importer in your own AiiDAlab application write the following:

```python
from aiidalab_widget_base import OptimadeQueryWidget
from aiidalab_widgets_base.viewers import StructureDataViewer
from ipywidgets import dlink

structure_query = OptimadeQueryWidget()
structure_viewer = StructureDataViewer()

# Save to `_` in order to suppress output
_ = dlink((structure_query, 'structure'), (structure_viewer, 'structure'))

display(structure_query)
display(structure_viewer)
```

This will immediately display a query widget with a dropdown of current structure databases that implements the OPTIMADE API.

Then you can filter to find a family of structures according to elements, number of elements, chemical formula, and more.
See the [OPTIMADE API specification](https://github.com/Materials-Consortia/OPTiMaDe/blob/master/optimade.rst) for the full list of filter options and their description.

In order to delve deeper into the details of a particular structure, you can also import and display `OptimadeResultsWidget`.  
See the notebook [`OPTIMADE-Client.ipynb`](OPTIMADE-Client.ipynb) for an example of how to set up a general purpose OPTIMADE importer.

#### Embedded

The query widget may also be embedded into another app.  
For this a more "minimalistic" version of the widget can be used by passing `embedded=True` upon initiating the widget, i.e., `structure_query = OptimadeQueryWidget(embedded=True)`.

Everything else works the same - so you would still have to link up the query widget to the rest of your app.

### General Jupyter notebook

The package's widgets can be used in any general Jupyter notebook as well as AiiDAlab.
Example:

```python
from optimade_client import
    OptimadeQueryProviderWidget,
    OptimadeQueryFilterWidget,
    OptimadeSummaryWidget
from ipywidgets import dlink

database_selector = OptimadeQueryProviderWidget()
structure_query = OptimadeQueryFilterWidget()
structure_viewer = OptimadeSummaryWidget()

# Save to `_` in order to suppress output
_ = dlink((database_selector, 'database'), (structure_query, 'database'))
_ = dlink((structure_query, 'structure'), (structure_viewer, 'entity'))

display(database_selector, structure_query, structure_viewer)
```

This will use the package's own structure viewer and summary widget.

Note, the `OptimadeQueryWidget` mentioned above is a special wrapper widget in AiiDAlab for the `OptimadeQueryProviderWidget` and `OptimadeQueryFilterWidget` widgets.

### Running application locally

First, you will need to install the package either from [PyPI](https://pypi.org/project/optimade-client) or by retrieving the git repository hosted on [GitHub](https://github.com/CasperWA/voila-optimade-client).

#### PyPI

```shell
$ pip install optimade-client[server]
```

#### GitHub

```shell
$ git clone https://github.com/CasperWA/voila-optimade-client.git
$ cd voila-optimade-client
voila-optimade-client$ pip install .[server]
```

Note, it is important to install the `server` extra in order to also install the `voila` package (and the `ase` package for a wider variety of download formats).

To now run the application (notebook) [`OPTIMADE-Client.ipynb`](OPTIMADE-Client.ipynb) you can simply run the command `optimade-client` in a terminal and go to the printed URL (usually <http://localhost:8866>) or pass the `--open-browser` option to let the program try to automatically open your default browser.

The application will be run in Voilà using Voilà's own `tornado`-based server.
The configuration will automatically be copied to Jupyter's configuration directory before starting the server.

```shell
$ optimade-client
...
[Voila] Voilà is running at:
http://localhost:8866/
...
```

For a list of all options that can be passed to `optimade-client` use the `-h/--help` option.

## Contribute

If you wish to contribute to the application, you can install it in "editable" mode by using the `-e` flag: `pip install -e .[dev]`.
It is recommended that you use the GitHub-route mentioned above.

You should also install `pre-commit` in the cloned git repository by running:

```shell
voila-optimade-client$ pre-commit install
```

To start making contributions, fork the repository and create PRs.

## Configuration (Voilà)

For running the application (in Voilà) on Binder, the configuration file [`jupyter_config.json`](optimade_client/jupyter_config.json) can be used.  
If you wish to start the Voilà server locally with the same configuration, either copy the [`jupyter_config.json`](optimade_client/jupyter_config.json) file to your Jupyter config directory, renaming it to `voila.json` or pass the configurations when you start the server using the CLI.

> **Note**: `jupyter_config.json` is automatically copied over as `voila.json` when running the application using the `optimade-client` command.

Locate your Jupyter config directory:

```shell
$ jupyter --config-dir
/path/to/jupyter/config/dir
```

Example of passing configurations when you start the Voilà server using the CLI:

```shell
$ voila --enable_nbextensions=True --VoilaExecutePreprocessor.timeout=180 "OPTIMADE-Client.ipynb"
...
[Voila] Voilà is running at:
http://localhost:8866/
...
```

To see the full list of configurations you can call `voila` and pass `--help-all`.

## License

MIT. The terms of the license can be found in the [LICENSE](LICENSE) file.

## Contact

casper.andersen@epfl.ch  
aiidalab@materialscloud.org
