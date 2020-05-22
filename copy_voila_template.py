#!/usr/bin/python3

import os
import json
import shutil
import sys


def get_voila_templates_dir() -> str:
    """Find absolute path to Jupyter's data dir that contains Voilà templates"""
    jupyter_dirs = os.popen("jupyter --paths --json")
    try:
        jupyter_dirs = json.loads(jupyter_dirs.read())
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Could not decode shell command 'jupyter --paths --json' as JSON."
            f"Original exception:\n{exc!s}"
        )

    for data_dir in jupyter_dirs.get("data", []):
        voila_templates_dir = os.path.join(data_dir, "voila/templates/")
        if os.path.exists(voila_templates_dir):
            break
    else:
        raise RuntimeError(
            f"No valid Voilà 'templates' folder found amongst: {jupyter_dirs.get('data', [])!r}"
        )

    return os.path.abspath(voila_templates_dir)


def copy_template(name: str):
    """Copy a Voilà template to Jupyter's first (and best) data dir"""
    src = os.path.abspath(name)
    if not os.path.exists(src):
        raise RuntimeError(f"Can not find provided template '{name}' at {src} !")

    dest = get_voila_templates_dir()
    new_dest = os.path.join(dest, name)
    if os.path.exists(new_dest):
        print(
            f"Template '{name}' has already been copied into {dest}, "
            "will first remove it, then copy it anew !"
        )
        shutil.rmtree(new_dest)
        print(f"Successfully removed {dest} !")

    shutil.copytree(src, new_dest, symlinks=False)
    print(f"Successfully copied {name} to {dest} !")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        template = sys.argv[1]
    else:
        print("No template supplied to be copied!")
        sys.exit(0)

    try:
        copy_template(template)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Exception while copying template!\nException: {exc!s}")
        sys.exit(1)
    else:
        sys.exit(0)
