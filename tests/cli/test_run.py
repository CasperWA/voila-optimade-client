import pytest

try:
    import voila as _
except ImportError:
    VOILA_PACKAGE_EXISTS = False
else:
    VOILA_PACKAGE_EXISTS = True


@pytest.mark.skipif(
    not VOILA_PACKAGE_EXISTS,
    reason="Voilà is not installed. This test is rendered invalid.",
)
def test_default(run_cli):
    """Run `optimade-client` with default settings"""
    output = run_cli()
    assert "[Voila] Voilà is running at:" in output, f"output:\n{output}"


@pytest.mark.skipif(
    VOILA_PACKAGE_EXISTS, reason="Voilà is installed. This test is rendered invalid."
)
def test_voila_not_installed(run_cli):
    """Ensure the CLI can handle Voilà not being installed."""
    output = run_cli(raises=True)
    exit_text = (
        "Voilà is not installed.\nPlease run:\n\n     pip install optimade-client[server]\n\n"
        "Or the equivalent, matching the installation in your environment, to install Voilà "
        "(and ASE for a larger download format selection)."
    )
    assert exit_text in output
    assert "[Voila]" not in output
