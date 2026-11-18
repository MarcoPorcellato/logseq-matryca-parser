"""Synthetic contracts for batched block-reference resolution."""

import logging
from pathlib import Path
from uuid import UUID

import pytest

from logseq_matryca_parser import graph as graph_module
from logseq_matryca_parser.graph import LogseqGraph
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

TARGET = "64c752b0-d33b-4448-a261-e4dc2bbe12d3"
MISSING = "00000000-0000-0000-0000-000000000099"


def _node(
    key: str,
    path: Path,
    *,
    source_uuid: str | None = None,
    prop_id: object = None,
    refs: tuple[str, ...] = (),
) -> LogseqNode:
    return LogseqNode(
        uuid=key,
        content="Synthetic",
        indent_level=0,
        source_uuid=source_uuid,
        source_path=str(path),
        properties={"id": prop_id} if prop_id is not None else {},
        block_refs=list(refs),
    )


def _graph(
    root: Path, nodes: list[LogseqNode], kind: type[LogseqGraph] = LogseqGraph
) -> LogseqGraph:
    path = root / "Attached.md"
    page = LogseqPage(title="Attached", raw_content="", source_path=str(path))
    return kind(graph_path=root, pages={page.title: page}, node_registry={n.uuid: n for n in nodes})


def test_batch_normalizes_registry_alias_once_for_many_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = tmp_path / "Attached.md"
    nodes = [
        _node("early", page, source_uuid="non-uuid-alias"),
        _node("target", page, source_uuid=TARGET),
    ]
    nodes.extend(_node(f"source-{i}", page, refs=(TARGET,)) for i in range(8))
    graph = _graph(tmp_path, nodes)
    alias_normalizations = 0

    def observed_uuid(value: str) -> UUID:
        nonlocal alias_normalizations
        if value == "non-uuid-alias":
            alias_normalizations += 1
        return UUID(value)

    monkeypatch.setattr(graph_module.uuid, "UUID", observed_uuid)
    assert graph.get_broken_references() == []
    assert alias_normalizations == 1


def test_batch_preserves_registry_targets_and_broken_source_order(tmp_path: Path) -> None:
    page = tmp_path / "Attached.md"
    detached = tmp_path / "Detached.md"
    nodes = [
        _node("direct", page),
        _node("target", detached, prop_id=TARGET.upper()),
        _node("literal", detached, source_uuid="literal-id"),
        _node("valid", page, refs=(" direct ", TARGET, "literal-id")),
        _node("first-broken", page, refs=(TARGET, MISSING, MISSING)),
        _node("detached-broken", detached, refs=(MISSING,)),
        _node("second-broken", page, refs=(" ",)),
    ]
    graph = _graph(tmp_path, nodes)

    assert [node.uuid for node in graph.get_broken_references()] == [
        "first-broken",
        "second-broken",
    ]


def test_batch_preserves_custom_resolver(tmp_path: Path) -> None:
    class CustomGraph(LogseqGraph):
        def get_node_by_embed_ref(self, block_ref: str) -> LogseqNode | None:
            return super().get_node_by_embed_ref(
                "custom-target" if block_ref == TARGET else block_ref
            )

    page = tmp_path / "Attached.md"
    nodes = [_node("custom-target", page), _node("source", page, refs=(TARGET,))]
    assert _graph(tmp_path, nodes, CustomGraph).get_broken_references() == []


def test_batch_retains_original_fallback_for_unusual_property_ids(tmp_path: Path) -> None:
    class ComparableId:
        def __eq__(self, other: object) -> bool:
            return other == TARGET

    page = tmp_path / "Attached.md"
    nodes = [
        _node("ordinary", page, source_uuid="ordinary"),
        _node("odd", page, prop_id=ComparableId()),
        _node("unhashable", page, prop_id=["not-an-id"]),
        _node("source", page, refs=(TARGET, MISSING)),
        _node("valid", page, refs=(TARGET,)),
    ]
    graph = _graph(tmp_path, nodes)

    assert [node.uuid for node in graph.get_broken_references()] == ["source"]


def test_batch_does_not_reuse_aliases_after_graph_changes(tmp_path: Path) -> None:
    page = tmp_path / "Attached.md"
    target = _node("target", page, prop_id=TARGET)
    graph = _graph(tmp_path, [target, _node("source", page, refs=(TARGET,))])
    assert graph.get_broken_references() == []

    target.properties["id"] = "different-id"
    assert [node.uuid for node in graph.get_broken_references()] == ["source"]


def test_batch_preserves_custom_registry_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = LogseqGraph.get_node_by_uuid

    def lookup(graph: LogseqGraph, ref: str) -> LogseqNode | None:
        return original(graph, "custom-target" if ref == TARGET else ref)

    page = tmp_path / "Attached.md"
    nodes = [_node("custom-target", page), _node("source", page, refs=(TARGET,))]
    graph = _graph(tmp_path, nodes)
    monkeypatch.setattr(LogseqGraph, "get_node_by_uuid", lookup)
    assert graph.get_broken_references() == []


def test_batch_discards_alias_index_after_dispatching_custom_reference(tmp_path: Path) -> None:
    page = tmp_path / "Attached.md"
    target = _node("target", page, prop_id=TARGET)

    class MutatingRef(str):
        def strip(self, chars: str | None = None) -> str:
            target.properties["id"] = "changed"
            return super().strip(chars)

    direct = _node("direct", page)
    source = _node("source", page, refs=(TARGET,))
    source.block_refs.extend((MutatingRef("direct"), TARGET))
    graph = _graph(tmp_path, [target, direct, source])
    assert [node.uuid for node in graph.get_broken_references()] == ["source"]


def test_batch_preserves_updates_from_synchronous_debug_handlers(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    page = tmp_path / "Attached.md"
    target = _node("target", page, prop_id=TARGET)
    first = _node("first", page, refs=(MISSING,))
    second = _node("second", page, refs=(TARGET,))
    graph = _graph(tmp_path, [target, first, second])

    class EditTarget(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.getMessage().startswith("get_broken_references origin=first "):
                target.properties["id"] = "changed"

    handler = EditTarget()
    graph_module.logger.addHandler(handler)
    try:
        with caplog.at_level(logging.DEBUG, logger=graph_module.logger.name):
            assert [node.uuid for node in graph.get_broken_references()] == ["first", "second"]
    finally:
        graph_module.logger.removeHandler(handler)
