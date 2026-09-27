"""Contract tests for the runnable SYNAPSE RAG example."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
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

    def flatten(nodes: list[Any]) -> list[object]:
        result: list[object] = []
        for node in nodes:
            result.append(object())
            result.extend(flatten(node.children))
        return result

    companion = SimpleNamespace(to_llamaindex_nodes=lambda nodes, **_kwargs: flatten(nodes))
    monkeypatch.setitem(sys.modules, "logseq_matryca_parser_llamaindex", companion)

    runpy.run_path(str(script), run_name="__main__")

    output = capsys.readouterr().out
    assert "LangChain documents: 2" in output
    assert "LlamaIndex nodes: 2" in output
    assert "Context-enriched chunks: 2" in output
    assert "Matryca preserves Logseq hierarchy and provenance." in output
    assert "{{embed" not in output


def test_synapse_rag_example_explains_missing_ai_dependencies(capsys: Any) -> None:
    """A missing LangChain dependency produces its own actionable message."""
    script = Path(__file__).parents[1] / "examples" / "run_synapse_rag.py"

    with patch("logseq_matryca_parser.synapse.Document", None):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(script), run_name="__main__")

    assert exc_info.value.code == 1
    error = capsys.readouterr().err
    assert "LangChain dependencies are missing" in error
    assert "uv sync --extra ai" in error


def test_synapse_rag_example_explains_missing_companion(capsys: Any, monkeypatch: Any) -> None:
    """The example names the separate LlamaIndex companion when it is absent."""
    script = Path(__file__).parents[1] / "examples" / "run_synapse_rag.py"
    monkeypatch.setattr("sys.argv", [str(script)])
    monkeypatch.delitem(sys.modules, "logseq_matryca_parser_llamaindex", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(script), run_name="__main__")

    assert exc_info.value.code == 1
    error = capsys.readouterr().err
    assert "pip install logseq-matryca-parser-llamaindex" in error
    assert "uv sync --extra ai" not in error


def test_migration_docs_distinguish_parser_and_companion() -> None:
    root = Path(__file__).parents[1]
    documents = (
        root / "README.md",
        root / "docs" / "COOKBOOK.md",
        root / "docs" / "reference" / "CONFORMANCE_SUPPORT_MATRIX.md",
    )

    for path in documents:
        text = " ".join(path.read_text(encoding="utf-8").casefold().split())
        assert "logseq-matryca-parser-llamaindex" in text
        assert "not yet published" in text

    readme = (root / "README.md").read_text(encoding="utf-8").casefold()
    assert "[ai]" in readme and "[all]" in readme
    assert "do not install llamaindex" in readme

    security_policy = (
        (root / "docs" / "security" / "DEPENDENCY_ADVISORY_EXCEPTIONS.md")
        .read_text(encoding="utf-8")
        .casefold()
    )
    assert "resolved historical exception" in security_policy
    assert "active exception: nltk" not in security_policy
