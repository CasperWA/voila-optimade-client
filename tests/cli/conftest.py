from multiprocessing import Process
import os
import signal
from time import sleep
from typing import List

import pytest


@pytest.fixture
def run_cli(capfd):
    """Run a command in the `optimade-client` CLI (through the Python API)."""

    def _run_cli(options: List[str] = None, raises: bool = False) -> str:
        """Run a command in the `optimade-client` CLI (through the Python API)."""
        from optimade_client.cli import run

        if options is None:
            options = []

        try:
            cli = Process(target=run.main, args=(options,))
            cli.start()
            sleep(5)  # Startup time
            output = capfd.readouterr()
        finally:
            os.kill(cli.pid, signal.SIGINT)
            timeout = 10  # seconds
            while cli.is_alive() and timeout:
                sleep(1)
                timeout -= 1
            if cli.is_alive():
                cli.kill()
                cli.join()
                sleep(1)

        assert not cli.is_alive(), f"Could not stop CLI subprocess <PID={cli.pid}>"

        if raises:
            assert (
                cli.exitcode != 0
            ), f"\nstdout:\n{output.out}\n\nstderr:\n{output.err}"
        else:
            assert (
                cli.exitcode == 0
            ), f"\nstdout:\n{output.out}\n\nstderr:\n{output.err}"

        return output.out + output.err

    return _run_cli
