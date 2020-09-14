from datetime import date
from pathlib import Path
import re
from typing import Tuple

from invoke import task


TOP_DIR = Path(__file__).parent.resolve()


def update_file(filename: str, sub_line: Tuple[str, str], strip: str = None):
    """Utility function for tasks to read, update, and write files"""
    with open(filename, "r") as handle:
        lines = [re.sub(sub_line[0], sub_line[1], l.rstrip(strip)) for l in handle]

    with open(filename, "w") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


@task
def update_version(_, version=""):
    """Update package version to today's date using CalVer"""
    if not version:
        # Use today's date
        today = date.today()
        version = f"{today.year}.{today.month}.{today.day}"

    update_file(
        TOP_DIR.joinpath("optimade_client/version.py"),
        ("__version__ = .+", f'__version__ = "{version}"'),
    )
    update_file(
        TOP_DIR.joinpath("setup.py"), ("version=([^,]+),", f'version="{version}",')
    )

    print(f"Bumped version to {version} !")
