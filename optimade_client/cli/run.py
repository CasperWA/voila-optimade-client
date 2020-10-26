import argparse
import logging
import os
from pathlib import Path
from shutil import copyfile
import subprocess
import sys

try:
    from voila.app import main as voila
except ImportError:
    voila = None


LOGGING_LEVELS = [logging.getLevelName(level).lower() for level in range(0, 51, 10)]
VERSION = "2020.10.26"  # Avoid importing optimade-client package


def main(args: list = None):
    """Run the OPTIMADE Client."""
    parser = argparse.ArgumentParser(
        description=main.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        help="Show the version and exit.",
        version=f"OPTIMADE Client version {VERSION}",
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
        help="Will overrule log-level option and set the log-level to 'debug'.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Attempt to open a browser upon starting the Voilà tornado server.",
    )

    args = parser.parse_args(args)
    log_level = args.log_level
    debug = args.debug
    open_browser = args.open_browser

    # Make sure Voilà is installed
    if voila is None:
        sys.exit(
            "Voilà is not installed.\nPlease run:\n\n     pip install optimade-client[server]\n\n"
            "Or the equivalent, matching the installation in your environment, to install Voilà "
            "(and ASE for a larger download format selection)."
        )

    # Rename jupyter_config.json to voila.json and copy it Jupyter's config dir
    jupyter_config_dir = subprocess.getoutput("jupyter --config-dir")
    Path(jupyter_config_dir).mkdir(parents=True, exist_ok=True)
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

    argv = ["OPTIMADE Client.ipynb"]

    if debug:
        if log_level not in ("debug", "info"):
            print("[OPTIMADE-Client] Overwriting requested log-level to: 'debug'")
        os.environ["OPTIMADE_CLIENT_DEBUG"] = "True"
        argv.append("--debug")
    else:
        os.environ.pop("OPTIMADE_CLIENT_DEBUG", None)

    if not open_browser:
        argv.append("--no-browser")

    if "--debug" not in argv:
        argv.append(f"--Voila.log_level={getattr(logging, log_level.upper())}")

    voila(argv)
