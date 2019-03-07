# OPTiMaDe client for AiiDA Lab

AiiDA Lab App that implements an [OPTiMaDe](http://www.optimade.org) client

## Installation

This Jupyter-based app is intended to run in
[AiiDA Lab](https://aiidalab.materialscloud.org)
as well as inside a
[Quantum Mobile](https://materialscloud.org/work/quantum-mobile) Virtual Machine.

Use the App Store in the
[Home App](https://github.com/aiidalab/aiidalab-home)
to install it.

## Usage

### Default

To use the OPTiMaDe structure importer in your own Jupyter notebook / AiiDA Lab app write the following:

```python
from aiidalab_optimade import OptimadeStructureImport

structure_import = OptimadeStructureImport()
structure_import.display()
```

This will immediately display a Dropdown-widget of current structure databases with the OPTiMaDe API implemented.

Then you can filter to find a family of structures according to elements, number of elements, chemical formula, and more.
See the
[OPTiMaDe API documentation](https://github.com/Materials-Consortia/OPTiMaDe/blob/master/optimade.md)
for the full list and their description.

From another Dropdown-widget, you can single out a structure, view its unit cell and a list of relevant data will be shown.

Finally, the chosen structure can be safed in your local AiiDA Lab database as either `StructureData` or `CifData`.

### Detailed

#### Display parts

You can choose to only display certain parts of the structure importer.

As an example, if you want to pre-specify a specific OPTiMaDe database to query and do not want the user of your app to be able to choose another, you could write:

```python
from aiidalab_optimade import OptimadeStructureImport

structure_import = OptimadeStructureImport()
structure_import.database("COD")  # Use Crystallography Open Database
```

or simply

```python
structure_import = OptimadeStructureImport(database="COD")  # Use Crystallography Open Database
```

Then you can display the structure importer without the Dropdown-widget of databases by writing

```python
structure_import.display(no_host=True)
```

or you can choose the parts of the structure importer individually, leaving out `"host"`

```python
structure_import.display(parts=["filter", "select", "viewer", "store"])
```

> **Note**: If `"host"` is included in `parts`, `no_host` has no effect.

The included databases for now are:

* Crystallography Open Database (COD) - `"cod"`
* Your local AiiDA Lab database - `"aiida"`

To specify a custom database, one can use:

* Custom database - `"custom"`

> **Note**: When specifying a custom database, one *must* also provide a host URL.

#### Custom OPTiMaDe database - specify host

This can be done when instantiating an object of the `OptimadeStructureImport()` class

```python
structure_import = OptimadeStructureImport(database="Custom", host="localhost:5000")
```

or afterwards

```python
structure_import.host("localhost:5000")
structure_import.database("Custom")
```

Another way to do this in a single line:

```python
structure_import.database("Custom", host="localhost:5000")
```

## License

MIT. The terms of the license can be found in the LICENSE file.

## Contact

aiidalab@materialscloud.org
