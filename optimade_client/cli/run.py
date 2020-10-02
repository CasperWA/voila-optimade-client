import argparse
import os
from pathlib import Path
from shutil import copyfile
import subprocess

from voila.app import main as voila

from optimade_client import __version__
from optimade_client.cli.options import LOGGING_LEVELS


def main():
    """Run the OPTIMADE Client."""
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        help="Show the version and exit.",
        version=f"OPTIMADE Client version {__version__}",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        help="Set the log-level of the server.",
        choices=LOGGING_LEVELS,
        default="info",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Will set the log-level to DEBUG. Note, parameter log-level takes precedence "
        "if not 'info'!",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Attempt to open a browser upon starting the Voilà tornado server.",
    )

    args = parser.parse_args()
    log_level = args.log_level
    debug = args.debug
    open_browser = args.open_browser

    # Rename jupyter_config.json to voila.json and copy it Jupyter's config dir
    jupyter_config_dir = subprocess.getoutput("jupyter --config-dir")
    copyfile(
        Path(__file__).parent.parent.parent.joinpath("jupyter_config.json").resolve(),
        f"{jupyter_config_dir}/voila.json",
    )

    # "Trust" notebook
    subprocess.run(
        ["jupyter", "trust", "OPTIMADE Client.ipynb"],
        cwd=Path(__file__).parent.parent.parent.resolve(),
        check=False,
    )

    log_level = log_level.lower()
    if debug and log_level == "info":
        log_level = "debug"

    argv = ["OPTIMADE Client.ipynb"]

    if log_level == "debug":
        os.environ["OPTIMADE_CLIENT_DEBUG"] = "True"
        argv.append("--debug")
    else:
        os.environ.pop("OPTIMADE_CLIENT_DEBUG", None)

    if not open_browser:
        argv.append("--no-browser")

    voila(argv)
