import pytest

try:
    import voila as _  # noqa: F401
except ImportError:
    VOILA_INSTALLED = False
else:
    VOILA_INSTALLED = True

pytestmark = pytest.mark.skipif(
    VOILA_INSTALLED,
    reason="Voilà is installed. Tests in this module are rendered invalid.",
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
