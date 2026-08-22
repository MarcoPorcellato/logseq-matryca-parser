import subprocess
import sys


def test_module_entrypoint_help(tmp_path) -> None:
    """Ensure `python -m logseq_matryca_parser --help` executes cleanly and outputs CLI help."""
    result = subprocess.run(
        [sys.executable, "-m", "logseq_matryca_parser", "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "matryca-parse" in result.stdout
    assert "scan" in result.stdout