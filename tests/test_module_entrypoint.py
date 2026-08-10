import subprocess
import sys


def test_module_entrypoint_help() -> None:
    """Ensure `python -m logseq_matryca_parser --help` executes cleanly and outputs CLI help."""
    result = subprocess.run(
        [sys.executable, "-m", "logseq_matryca_parser", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "matryca-parse" in result.stdout
    assert "scan" in result.stdout