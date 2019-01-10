# OPTiMaDe client for AiiDA Lab

AiiDA Lab App that implements an OPTiMaDe client

## Installation

This jupyter-based app is intended to run in
[AiiDA Lab](https://aiidalab.materialscloud.org)
as well as inside the
[Quantum Mobile](https://materialscloud.org/work/quantum-mobile) Virtual Machine.

Use the App Store in the [Home App](https://github.com/aiidalab/aiidalab-home) to install it.

## Usage

### Default

To use the OPTiMaDe structure importer in your own Jupyter notebook / AiiDA Lab app write the following:

```python
from aiidalab_optimade import OptimadeStructureImport

structure_import = OptimadeStructureImport()
structure_import.display()
```

### Detailed

If you only want certain parts of the importer displayed, e.g. you want to pre-specify the OPTiMaDe database to use and do not want the user of your app to choose another, you could write:

```python
from aiidalab_optimade import OptimadeStructureImport

structure_import = OptimadeStructureImport()
structure_import.set_database("COD")
```

or

```python
structure_import = OptimadeStructureImport(database="COD")
```

Then you can display the importer:

```python
structure_import.display(no_host=True)
```

or you can choose the parts individually, leaving out `"host"`:

```python
structure_import.display(parts=["filter", "select", "viewer", "store"])
```

> **Note**: If `"host"` is included in `parts`, `no_host` has no effect.

## License

MIT. The terms of the license can be found in the LICENSE file.

## Contact

aiidalab@materialscloud.org
