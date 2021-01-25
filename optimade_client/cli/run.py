import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys

try:
    from voila.app import main as voila
except ImportError:
    voila = None


LOGGING_LEVELS = [logging.getLevelName(level).lower() for level in range(0, 51, 10)]
VERSION = "2021.1.25"  # Avoid importing optimade-client package


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
    parser.add_argument(
        "--template",
        type=str,
        help="Use another template than the default.",
    )

    args = parser.parse_args(args)
    log_level = args.log_level
    debug = args.debug
    open_browser = args.open_browser
    template = args.template

    # Make sure Voilà is installed
    if voila is None:
        sys.exit(
            "Voilà is not installed.\nPlease run:\n\n     pip install optimade-client[server]\n\n"
            "Or the equivalent, matching the installation in your environment, to install Voilà "
            "(and ASE for a larger download format selection)."
        )

    notebook = str(
        Path(__file__).parent.joinpath("static/OPTIMADE-Client.ipynb").resolve()
    )
    config_path = str(Path(__file__).parent.joinpath("static").resolve())

    # "Trust" notebook
    subprocess.run(["jupyter", "trust", notebook], check=False)

    argv = [notebook]

    if sys.version_info.minor <= 6:
        # Python 3.6 and below (officially only supports Python 3.6+)
        argv.append(f'--Voila.config_file_paths=["{config_path}"]')
    else:
        argv.append(f"--Voila.config_file_paths={config_path}")

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

    if template:
        argv.append(f"--template={template}")

    voila(argv)
