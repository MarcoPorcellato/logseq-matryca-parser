"""Tests for agent-native X-Ray exports and session alias registry."""

from __future__ import annotations

from pathlib import Path

import pytest
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


def test_session_alias_registry_load_skips_duplicate_uuids(tmp_path: Path) -> None:
    """Duplicate UUID entries on disk keep the first alias mapping (BUG-009)."""
    state_path = tmp_path / "alias_state.json"
    state_path.write_text(
        '{"0": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "1": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}',
        encoding="utf-8",
    )

    registry = SessionAliasRegistry.load_from_disk(state_path)

    assert registry.resolve_alias(0) == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert registry.resolve_alias(1) is None
    assert registry.alias_for_uuid("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") == 0


def test_session_alias_registry_load_empty_file(tmp_path: Path) -> None:
    state_path = tmp_path / "alias_state.json"
    state_path.write_text("", encoding="utf-8")

    registry = SessionAliasRegistry.load_from_disk(state_path)

    assert registry.resolve_alias(0) is None


def test_session_alias_registry_load_invalid_json(tmp_path: Path) -> None:
    from logseq_matryca_parser.exceptions import SessionAliasRegistryError

    state_path = tmp_path / "alias_state.json"
    state_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(SessionAliasRegistryError, match="Invalid JSON"):
        SessionAliasRegistry.load_from_disk(state_path)


def test_session_alias_registry_load_skips_non_integer_alias_keys(tmp_path: Path) -> None:
    state_path = tmp_path / "alias_state.json"
    state_path.write_text(
        '{"abc": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "0": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}',
        encoding="utf-8",
    )

    registry = SessionAliasRegistry.load_from_disk(state_path)

    assert registry.resolve_alias(0) == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert registry.resolve_alias(1) is None


def test_session_alias_registry_load_unwraps_aliases_wrapper(tmp_path: Path) -> None:
    state_path = tmp_path / "alias_state.json"
    state_path.write_text(
        '{"aliases": {"0": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}}',
        encoding="utf-8",
    )

    registry = SessionAliasRegistry.load_from_disk(state_path)

    assert registry.resolve_alias(0) == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


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

    state_path = graph_root / ".matryca_xray_state.json"
    assert state_path.is_file()
    restored = SessionAliasRegistry.load_from_disk(state_path)
    assert restored.resolve_alias(0) is not None


def test_agent_write_cli_splices_via_alias_state(tmp_path: Path) -> None:
    graph_root = tmp_path / "graph"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (graph_root / "journals").mkdir()
    (pages / "Write.md").write_text("- Parent #parent-tag\n", encoding="utf-8")

    read_result = runner.invoke(
        app,
        ["agent-read", str(graph_root), "--tag", "parent-tag"],
    )
    assert read_result.exit_code == 0

    write_result = runner.invoke(
        app,
        [
            "agent-write",
            str(graph_root),
            "--alias",
            "0",
            "--content",
            "Child from agent-write",
        ],
    )
    assert write_result.exit_code == 0

    updated = (pages / "Write.md").read_text(encoding="utf-8")
    assert "Child from agent-write" in updated


def test_agent_read_cli_query_filter_finds_matching_blocks(tmp_path: Path) -> None:
    """``agent-read --query`` prints only blocks containing the search term."""
    graph_root = tmp_path / "graph"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (graph_root / "journals").mkdir()

    (pages / "alpha.md").write_text(
        "- Needle in a haystack #tag-a\n"
        "  - Nested needle block\n",
        encoding="utf-8",
    )
    (pages / "beta.md").write_text(
        "- Irrelevant content #tag-b\n"
        "  - Should not appear\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["agent-read", str(graph_root), "--query", "needle"],
    )

    assert result.exit_code == 0
    # Plain text — no Rich markup
    assert "\x1b[" not in result.output
    # X-Ray alias format [0], [1]
    assert "[0]" in result.output
    assert "Needle in a haystack" in result.output
    assert "Nested needle block" in result.output
    # Non-matching blocks are excluded
    assert "Irrelevant content" not in result.output
    assert "Should not appear" not in result.output

    # Alias state saved for agent-write chaining
    state_path = graph_root / ".matryca_xray_state.json"
    assert state_path.is_file()
    restored = SessionAliasRegistry.load_from_disk(state_path)
    assert restored.resolve_alias(0) is not None


def test_agent_read_cli_query_no_matches_exits_cleanly(tmp_path: Path) -> None:
    """``agent-read --query`` with no matches exits 0 and prints nothing."""
    graph_root = tmp_path / "graph"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (graph_root / "journals").mkdir()
    (pages / "only.md").write_text("- Just some text\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent-read", str(graph_root), "--query", "nonexistent"],
    )

    assert result.exit_code == 0
