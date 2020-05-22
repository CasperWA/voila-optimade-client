from pathlib import Path
import re
import sys
from typing import Tuple

from invoke import task

from aiidalab_optimade import __version__


TOP_DIR = Path(__file__).parent.resolve()


def update_file(filename: str, sub_line: Tuple[str, str], strip: str = None):
    """Utility function for tasks to read, update, and write files"""
    with open(filename, "r") as handle:
        lines = [re.sub(sub_line[0], sub_line[1], l.rstrip(strip)) for l in handle]

    with open(filename, "w") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


@task
def update_version(_, patch=False, ver=""):
    """Update package version"""
    new_ver = ver

    if (not patch and not new_ver) or (patch and new_ver):
        sys.exit(
            "Error: Either use --patch or specify e.g. --new-ver='Major.Minor.Patch'"
        )
    if patch:
        ver = [int(x) for x in __version__.split(".")]
        ver[2] += 1
        new_ver = ".".join(map(str, ver))

    update_file(
        TOP_DIR.joinpath("aiidalab_optimade/__init__.py"),
        ("__version__ = .+", f'__version__ = "{new_ver}"'),
    )
    update_file(
        TOP_DIR.joinpath("setup.py"), ("version=([^,]+),", f'version="{new_ver}",')
    )
    update_file(
        TOP_DIR.joinpath("metadata.json"),
        ('"version": "([^,]+)",', f'"version": "{new_ver}",'),
    )

    print("Bumped version to {}".format(new_ver))
