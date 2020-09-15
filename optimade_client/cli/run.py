import os
from pathlib import Path
from shutil import copyfile
import subprocess

import click

from optimade_client.cli.options import LOGGING_LEVELS


@click.command()
@click.help_option("-h", "--help")
@click.version_option(
    None, "-v", "--version", message="OPTIMADE Client version %(version)s"
)
@click.option(
    "--log-level",
    type=click.Choice(LOGGING_LEVELS, case_sensitive=False),
    default="info",
    show_default=True,
    help="Set the log-level of the server.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    show_default=True,
    help="Will set the log-level to DEBUG. Note, parameter log-level takes precedence "
    "if not 'info'!",
)
@click.option(
    "--open-browser",
    is_flag=True,
    default=False,
    show_default=True,
    help="Attempt to open a browser upon starting the Voilà tornado server.",
)
def cli(log_level: str, debug: bool, open_browser: bool):
    """Run OPTIMADE Client."""
    from voila.app import main

    # Rename jupyter_config.json to voila.json and copy it Jupyter's config dir
    jupyter_config_dir = subprocess.getoutput("jupyter --config-dir")
    copyfile(
        Path(__file__).parent.joinpath("static/jupyter_config.json").resolve(),
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

    main(argv)
