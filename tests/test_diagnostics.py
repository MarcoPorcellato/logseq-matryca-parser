from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from logseq_matryca_parser import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    LogseqGraph,
    collect_graph_diagnostics,
)


def _graph_with_broken_reference(tmp_path: Path) -> LogseqGraph:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Broken.md").write_text(
        "- origin\n"
        "  id:: 00000000-0000-0000-0000-000000000001\n"
        "  - ((00000000-0000-0000-0000-000000000099))\n",
        encoding="utf-8",
    )
    return LogseqGraph.load_directory(graph_root)


def test_diagnostic_is_immutable_and_json_compatible() -> None:
    diagnostic = Diagnostic(
        code=DiagnosticCode.GRAPH_BROKEN_BLOCK_REFERENCE,
        severity=DiagnosticSeverity.ERROR,
        source_path="pages/Broken.md",
        line=2,
        message="broken",
        context={"z": "last", "a": "first"},
    )

    assert diagnostic.to_dict() == {
        "code": "graph.broken_block_reference",
        "severity": "error",
        "source_path": "pages/Broken.md",
        "line": 2,
        "message": "broken",
        "context": {"a": "first", "z": "last"},
    }
    with pytest.raises(FrozenInstanceError):
        diagnostic.message = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        diagnostic.context["a"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    "source_path",
    ["/tmp/secret.md", "../secret.md", r"..\secret.md", r"C:\secret.md"],
)
def test_diagnostic_rejects_paths_outside_the_vault(source_path: str) -> None:
    with pytest.raises(ValueError, match="vault-relative"):
        Diagnostic(
            code="test.code",
            severity=DiagnosticSeverity.WARNING,
            source_path=source_path,
            message="unsafe path",
        )


def test_collect_graph_diagnostics_uses_stable_code_and_relative_path(tmp_path: Path) -> None:
    graph = _graph_with_broken_reference(tmp_path)

    diagnostics = collect_graph_diagnostics(graph)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == DiagnosticCode.GRAPH_BROKEN_BLOCK_REFERENCE
    assert diagnostic.severity is DiagnosticSeverity.ERROR
    assert diagnostic.source_path == "pages/Broken.md"
    assert diagnostic.line == 3
    assert diagnostic.context["missing_ref"] == "00000000-0000-0000-0000-000000000099"


def test_collect_graph_diagnostics_omits_external_source_path(tmp_path: Path) -> None:
    graph = _graph_with_broken_reference(tmp_path)
    broken = graph.get_broken_references()[0]
    external_node = broken.model_copy(update={"source_path": str(tmp_path.parent / "outside.md")})
    external_page = graph.pages["Broken"].model_copy(
        update={
            "source_path": str(tmp_path.parent / "outside.md"),
            "root_nodes": [external_node],
        }
    )
    external_graph = LogseqGraph(
        graph_path=graph.graph_path,
        pages={"Broken": external_page},
        node_registry={external_node.uuid: external_node},
    )

    diagnostic = collect_graph_diagnostics(external_graph)[0]

    assert diagnostic.source_path is None
