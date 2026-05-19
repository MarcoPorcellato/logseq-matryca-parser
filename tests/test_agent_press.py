"""Tests for agent-native X-Ray exports and session alias registry."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from logseq_matryca_parser.agent_press import SessionAliasRegistry, to_xray_markdown
from logseq_matryca_parser.kinetic import app
from logseq_matryca_parser.logos_core import LogseqNode

runner = CliRunner()


def _make_node(
    uuid: str,
    clean_text: str,
    *,
    indent_level: int = 0,
    children: list[LogseqNode] | None = None,
    properties: dict[str, object] | None = None,
) -> LogseqNode:
    return LogseqNode(
        uuid=uuid,
        content=clean_text,
        clean_text=clean_text,
        indent_level=indent_level,
        properties=properties or {},
        children=children or [],
    )


def test_session_alias_registry_three_nodes() -> None:
    uuids = [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
    ]
    nodes = [_make_node(uuid, f"Block {index}") for index, uuid in enumerate(uuids)]
    registry = SessionAliasRegistry()

    mapping = registry.generate_aliases(nodes)

    assert mapping == {0: uuids[0], 1: uuids[1], 2: uuids[2]}
    assert registry.resolve_alias(1) == uuids[1]
    assert registry.resolve_alias(99) is None


def test_session_alias_registry_save_and_load_from_disk(tmp_path: Path) -> None:
    uuids = [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    ]
    nodes = [_make_node(uuid, f"Block {index}") for index, uuid in enumerate(uuids)]
    registry = SessionAliasRegistry()
    registry.generate_aliases(nodes)

    state_path = tmp_path / "alias_state.json"
    registry.save_to_disk(state_path)

    restored = SessionAliasRegistry.load_from_disk(state_path)

    assert restored.resolve_alias(0) == uuids[0]
    assert restored.resolve_alias(1) == uuids[1]
    assert restored.alias_for_uuid(uuids[1]) == 1


def test_to_xray_markdown_nested_properties_stripped() -> None:
    child_one = _make_node(
        "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "Child one",
        indent_level=1,
    )
    child_two = _make_node(
        "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "Child two",
        indent_level=1,
    )
    parent = _make_node(
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "Database Phase",
        indent_level=0,
        properties={"collapsed": True, "id": "legacy-id", "custom::drawer": "hidden"},
        children=[child_one, child_two],
    )
    registry = SessionAliasRegistry()
    registry.generate_aliases([parent])

    output = to_xray_markdown([parent], registry)
    lines = [line for line in output.split("\n") if line.strip()]

    assert len(lines) <= 3
    assert "[0] Database Phase" in lines[0]
    assert "  [1] Child one" in output
    assert "  [2] Child two" in output
    assert "collapsed" not in output
    assert "legacy-id" not in output
    assert "ffffffff" not in output


def test_agent_read_cli_plain_stdout(tmp_path: Path) -> None:
    graph_root = tmp_path / "graph"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (graph_root / "journals").mkdir()
    (pages / "agent.md").write_text("- X-Ray target #agent-xray\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent-read", str(graph_root), "--tag", "agent-xray"],
    )

    assert result.exit_code == 0
    assert "\x1b[" not in result.output
    assert "[0]" in result.output
    assert "X-Ray target" in result.output
