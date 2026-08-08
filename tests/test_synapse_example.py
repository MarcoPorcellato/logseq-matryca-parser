"""Contract tests for the runnable SYNAPSE RAG example."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


def test_synapse_rag_example_exercises_all_public_exports(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    """The example runs offline and proves that its page embed is expanded."""
    script = Path(__file__).parents[1] / "examples" / "run_synapse_rag.py"
    monkeypatch.setattr("sys.argv", [str(script)])

    runpy.run_path(str(script), run_name="__main__")

    output = capsys.readouterr().out
    assert "LangChain documents: 2" in output
    assert "LlamaIndex nodes: 2" in output
    assert "Context-enriched chunks: 2" in output
    assert "Matryca preserves Logseq hierarchy and provenance." in output
    assert "{{embed" not in output


def test_synapse_rag_example_explains_missing_ai_dependencies(capsys: Any) -> None:
    """A missing optional integration produces an actionable operator message."""
    script = Path(__file__).parents[1] / "examples" / "run_synapse_rag.py"

    with patch("logseq_matryca_parser.synapse.Document", None):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(script), run_name="__main__")

    assert exc_info.value.code == 1
    error = capsys.readouterr().err
    assert "SYNAPSE AI dependencies are missing" in error
    assert "uv sync --extra ai" in error
