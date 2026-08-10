"""Contract tests for the runnable LOGOS live demo script."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any


def test_run_demo_example_exercises_logos_parser_and_forge(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    """The example runs offline and prints the FORGE clean Markdown output."""
    script = Path(__file__).parents[1] / "examples" / "run_demo.py"
    monkeypatch.setattr("sys.argv", [str(script)])

    runpy.run_path(str(script), run_name="__main__")

    captured = capsys.readouterr()
    output = captured.out

    assert "Logos Protocol" in output
    assert "AST extracted: 1 root nodes." in output
    assert "Forge output" in output
    assert "Success: Hierarchy preserved" in output
    assert "Public Funding Consulting Session" in output
    assert "Met with [[Alpha Corp]]" in output
