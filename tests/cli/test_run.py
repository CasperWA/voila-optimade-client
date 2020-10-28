import pytest


_ = pytest.importorskip("voila")


def test_default(run_cli):
    """Run `optimade-client` with default settings"""
    output = run_cli()
    assert "[Voila] Voilà is running at:" in output, f"output:\n{output}"


def test_version(run_cli):
    """Check `--version` flag"""
    from optimade_client import __version__

    output = run_cli(["--version"])
    assert output == f"OPTIMADE Client version {__version__}\n"


def test_log_level(run_cli):
    """Check `--log-level` option

    Levels:
    - `warning`: Above normal setting (INFO). There shouldn't be any output.
    - `info`: Normal setting. There should be minimal output.
    - `debug`: Below normal setting (INFO). There should be maximum output.
    """
    from pathlib import Path

    path_to_notebook = (
        Path(__file__)
        .parent.parent.parent.joinpath(
            "optimade_client/cli/static/OPTIMADE-Client.ipynb"
        )
        .resolve()
    )
    signed_text = f"Notebook already signed: {path_to_notebook}\n"

    log_level = "warning"

    output = run_cli(["--log-level", log_level])
    assert output == signed_text

    log_level = "info"

    output = run_cli(["--log-level", log_level])
    assert output != signed_text
    assert signed_text in output
    assert "[Voila]" in output
    assert "[Voila] template paths:" not in output

    log_level = "debug"
    output = run_cli(["--log-level", log_level])
    assert output != signed_text
    assert signed_text in output
    assert "[Voila] template paths:" in output


def test_debug(run_cli):
    """Check `--debug` flag

    This forcefully sets the log-level to `debug`.
    """
    output = run_cli(["--debug"])
    assert "[Voila] template paths:" in output

    log_level = "info"
    output = run_cli(["--log-level", log_level, "--debug"])
    assert "[OPTIMADE-Client] Overwriting requested log-level to: 'debug'" not in output
    assert "[Voila] template paths:" in output

    log_level = "warning"
    output = run_cli(["--log-level", log_level, "--debug"])
    assert "[OPTIMADE-Client] Overwriting requested log-level to: 'debug'" in output
    assert "[Voila] template paths:" in output

    log_level = "debug"
    output = run_cli(["--log-level", log_level, "--debug"])
    assert "[OPTIMADE-Client] Overwriting requested log-level to: 'debug'" not in output
    assert "[Voila] template paths:" in output


def test_open_browser(run_cli, monkeypatch):
    """Check `--open-browser` flag"""
    check_text = "Testing: webbrowser.get has been overwritten"
    monkeypatch.setattr("webbrowser.get", lambda *args, **kwargs: print(check_text))

    output = run_cli(["--open-browser"])
    assert check_text in output, f"output:\n{output}"

    output = run_cli()
    assert check_text not in output, f"output:\n{output}"
