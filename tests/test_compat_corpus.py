"""Contract tests for the offline, versioned Logseq compatibility corpus."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page
from scripts import update_compat_snapshots
from tests.parser_assurance.corpus import (
    CORPUS_ROOT,
    load_corpus_entries,
    load_exact_snapshot,
    validate_manifest,
)
from tests.parser_assurance.projection import IdentityPolicy, project_page

ROOT = Path(__file__).resolve().parents[1]


def _parse_entry(entry: dict[str, Any]) -> tuple[str, LogseqPage]:
    source_path = CORPUS_ROOT / entry["source"]["path"]
    source = source_path.read_text(encoding="utf-8")
    parse = entry["parse"]
    parser = StackMachineParser(tab_size=parse["tab_size"])
    if parse["entrypoint"] == "file":
        return source, parser.parse_page_file(source_path)
    return source, parser.parse(source, page_title=parse["page_title"])


def _walk(nodes: list[LogseqNode]) -> Iterator[LogseqNode]:
    for node in nodes:
        yield node
        yield from _walk(node.children)


def _assert_tree_invariants(page: LogseqPage) -> None:
    nodes = list(_walk(page.root_nodes))
    assert len({node.uuid for node in nodes}) == len(nodes)

    def visit(siblings: list[LogseqNode], parent: LogseqNode | None) -> None:
        for index, node in enumerate(siblings):
            assert node.parent_id == (parent.uuid if parent is not None else None)
            assert node.left_id == (siblings[index - 1].uuid if index else None)
            expected_path = [node.uuid] if parent is None else [*parent.path, node.uuid]
            assert node.path == expected_path
            expected_outline = [index + 1] if parent is None else [*parent.outline_path, index + 1]
            assert node.outline_path == expected_outline
            visit(node.children, node)

    visit(page.root_nodes, None)


def _identity_policy(entry: dict[str, Any]) -> IdentityPolicy:
    return cast(IdentityPolicy, entry["expectation"]["identity_policy"])


def test_manifest_is_strict_provenance_safe_and_deterministic() -> None:
    entries = load_corpus_entries()
    assert entries
    assert [entry["id"] for entry in entries] == sorted(entry["id"] for entry in entries)
    assert all(entry["fixture_schema_version"] == 1 for entry in entries)
    assert all(entry["snapshot_schema_version"] == 1 for entry in entries)

    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    reversed_manifest = copy.deepcopy(manifest)
    reversed_manifest["fixtures"].reverse()
    assert [entry["id"] for entry in validate_manifest(reversed_manifest)] == [
        entry["id"] for entry in entries
    ]


def _manifest_copy() -> dict[str, Any]:
    return json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_rejects_unknown_schema_versions() -> None:
    manifest = _manifest_copy()
    manifest["fixtures"][0]["fixture_schema_version"] = 2
    with pytest.raises(ValueError, match="unsupported fixture or snapshot schema version"):
        validate_manifest(manifest)


@pytest.mark.parametrize(
    ("path", "error"),
    [
        (("corpus_schema_version",), "unsupported corpus or snapshot schema version"),
        (("snapshot_schema_version",), "unsupported corpus or snapshot schema version"),
        (("fixtures", 0, "fixture_schema_version"), "unsupported fixture or snapshot schema version"),
        (("fixtures", 0, "snapshot_schema_version"), "unsupported fixture or snapshot schema version"),
        (("fixtures", 0, "parse", "tab_size"), "tab_size must be a positive integer"),
    ],
)
def test_manifest_rejects_boolean_integer_fields(
    path: tuple[str | int, ...],
    error: str,
) -> None:
    manifest = _manifest_copy()
    target: Any = manifest
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = True

    with pytest.raises(ValueError, match=error):
        validate_manifest(manifest)


def test_manifest_rejects_unverified_valid_fixture_diagnostics() -> None:
    manifest = _manifest_copy()
    manifest["fixtures"][0]["expectation"]["expected_diagnostics"] = ["unexpected"]

    with pytest.raises(ValueError, match="require no expected diagnostics"):
        validate_manifest(manifest)


def test_compatibility_fixture_bytes_are_forced_to_lf() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "tests/fixtures/compat/** text eol=lf" in attributes


def test_manifest_rejects_source_hash_drift() -> None:
    manifest = _manifest_copy()
    manifest["fixtures"][0]["source"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source SHA-256 mismatch"):
        validate_manifest(manifest)


def test_manifest_rejects_escaping_paths_and_unknown_keys() -> None:
    escaping = _manifest_copy()
    escaping["fixtures"][0]["source"]["path"] = "../outside.md"
    with pytest.raises(ValueError, match="escapes corpus root"):
        validate_manifest(escaping)

    unknown = _manifest_copy()
    unknown["fixtures"][0]["unexpected"] = True
    with pytest.raises(ValueError, match=r"unknown=\['unexpected'\]"):
        validate_manifest(unknown)


def test_manifest_confines_and_deduplicates_snapshot_destinations() -> None:
    outside_snapshots = _manifest_copy()
    outside_snapshots["fixtures"][0]["profiles"]["exact_parse"] = "manifest.json"
    with pytest.raises(ValueError, match="under snapshots"):
        validate_manifest(outside_snapshots)

    duplicate_snapshots = _manifest_copy()
    duplicate_snapshots["fixtures"][1]["profiles"]["exact_parse"] = duplicate_snapshots[
        "fixtures"
    ][0]["profiles"]["exact_parse"]
    with pytest.raises(ValueError, match="destinations must be unique"):
        validate_manifest(duplicate_snapshots)


def test_manifest_rejects_snapshot_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    source = CORPUS_ROOT / "hierarchy-identity.md"
    (root / source.name).write_bytes(source.read_bytes())
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "snapshots").symlink_to(outside, target_is_directory=True)
    manifest = _manifest_copy()
    manifest["fixtures"] = [manifest["fixtures"][0]]

    with pytest.raises(ValueError, match="escapes corpus root"):
        validate_manifest(manifest, root=root)


def test_manifest_rejects_source_snapshot_collision() -> None:
    manifest = _manifest_copy()
    manifest["fixtures"] = [manifest["fixtures"][0]]
    entry = manifest["fixtures"][0]
    snapshot_path = CORPUS_ROOT / entry["profiles"]["exact_parse"]
    entry["source"]["path"] = entry["profiles"]["exact_parse"]
    entry["source"]["sha256"] = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="source and snapshot paths must not collide"):
        validate_manifest(manifest)


def test_snapshot_cli_fails_closed_and_writes_only_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    snapshot = tmp_path / "snapshots" / "fixture.exact.json"
    entry = {"profiles": {"exact_parse": "snapshots/fixture.exact.json"}}
    expected = '{"snapshot_schema_version": 1}\n'
    monkeypatch.setattr(update_compat_snapshots, "CORPUS_ROOT", tmp_path)
    monkeypatch.setattr(update_compat_snapshots, "load_corpus_entries", lambda: (entry,))
    monkeypatch.setattr(update_compat_snapshots, "_render_snapshot", lambda _entry: expected)

    assert update_compat_snapshots.main([]) == 1
    assert not snapshot.exists()
    assert "stale compatibility snapshot" in capsys.readouterr().out

    assert update_compat_snapshots.main(["--write"]) == 0
    assert snapshot.read_text(encoding="utf-8") == expected
    assert not list(snapshot.parent.glob(".*.tmp"))
    assert "updated 1 compatibility snapshot(s)" in capsys.readouterr().out

    assert update_compat_snapshots.main([]) == 0


@pytest.mark.parametrize("property_key", ("tags", "page-tags", "alias", "aliases"))
def test_semantic_projection_canonicalizes_reference_property_sequences(property_key: str) -> None:
    page = StackMachineParser().parse(
        f"{property_key}:: [[Project Authored]], [[Fixture]]\n",
        page_title="Reference properties",
    )

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert projected["page"]["properties"][property_key] == ["Project Authored", "Fixture"]


def test_semantic_projection_preserves_commas_inside_wikilink_references() -> None:
    page = StackMachineParser().parse(
        "tags:: [[New York, NY]], Tech\n",
        page_title="Reference commas",
    )

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert projected["page"]["properties"]["tags"] == ["New York, NY", "Tech"]


def test_semantic_projection_preserves_content_wikilink_matching_property_tag() -> None:
    page = StackMachineParser().parse("- [[Foo]]\n  tags:: Foo\n", page_title="Content link")
    node = page.root_nodes[0]

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert node.wikilinks == ["Foo"]
    assert projected["page"]["root_nodes"][0]["wikilinks"] == ["Foo"]


@pytest.mark.parametrize(
    ("property_line",),
    [
        ("note:: `[[Foo]]`",),
        ("note:: ~~~[[Foo]]~~~",),
        ("note:: <!-- [[Foo]] -->",),
        ("note:: $\\text{[[Foo]]}$",),
        ("note:: {{query [[Foo]]}}",),
        ("note:: #+BEGIN_QUERY [[Foo]]",),
    ],
)
def test_semantic_projection_preserves_shielded_property_references(property_line: str) -> None:
    page = StackMachineParser().parse(
        f"- [[Foo]]\n  {property_line}\n",
        page_title="Shielded property references",
    )
    node = page.root_nodes[0]

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert node.wikilinks == ["Foo"]
    assert projected["page"]["root_nodes"][0]["wikilinks"] == ["Foo"]


def test_semantic_projection_canonicalizes_hash_tags_to_target() -> None:
    page = StackMachineParser().parse(
        "tags:: #[[Foo]]\n",
        page_title="Hashed tag property",
    )

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert projected["page"]["properties"]["tags"] == ["Foo"]


def test_semantic_projection_count_subtracts_duplicate_property_wikilinks() -> None:
    page = StackMachineParser().parse(
        "- [[Foo]] [[Foo]]\n  tags:: [[Foo]]\n",
        page_title="Duplicate links",
    )
    node = page.root_nodes[0]

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert node.wikilinks == ["Foo", "Foo", "Foo"]
    assert projected["page"]["root_nodes"][0]["wikilinks"] == ["Foo", "Foo"]


def test_semantic_projection_preserves_content_wikilink_order() -> None:
    page = StackMachineParser().parse(
        "- [[First]] [[Second]]\n  tags:: [[First]]\n",
        page_title="Ordered links",
    )

    projected = project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy={
            "synthetic_uuid": "stable",
            "source_uuid": "absent",
            "relations": "direct_ids",
        },
    )

    assert projected["page"]["root_nodes"][0]["wikilinks"] == ["First", "Second"]


@pytest.mark.parametrize("entry", load_corpus_entries(), ids=lambda entry: entry["id"])
def test_exact_parse_snapshot_and_same_input_determinism(entry: dict[str, Any]) -> None:
    source, page = _parse_entry(entry)
    _, repeated = _parse_entry(entry)

    assert page.raw_content == source
    _assert_tree_invariants(page)
    projected = project_page(page, profile="exact_parse_v1")
    assert projected == load_exact_snapshot(entry)
    assert project_page(repeated, profile="exact_parse_v1") == projected


@pytest.mark.parametrize("entry", load_corpus_entries(), ids=lambda entry: entry["id"])
def test_semantic_roundtrip_profile(entry: dict[str, Any]) -> None:
    _, page = _parse_entry(entry)
    policy = _identity_policy(entry)
    rendered = serialize_logseq_page(page)
    reparsed = StackMachineParser(tab_size=page.tab_size).parse(rendered, page_title=page.title)
    repeated_reparse = StackMachineParser(tab_size=page.tab_size).parse(
        rendered,
        page_title=page.title,
    )

    _assert_tree_invariants(reparsed)
    _assert_tree_invariants(repeated_reparse)
    assert project_page(repeated_reparse, profile="exact_parse_v1") == project_page(
        reparsed,
        profile="exact_parse_v1",
    )
    assert project_page(
        reparsed,
        profile="semantic_roundtrip_v1",
        identity_policy=policy,
    ) == project_page(
        page,
        profile="semantic_roundtrip_v1",
        identity_policy=policy,
    )
    original_source_uuids = [node.source_uuid for node in _walk(page.root_nodes)]
    reparsed_source_uuids = [node.source_uuid for node in _walk(reparsed.root_nodes)]
    if policy["source_uuid"] == "preserve":
        assert any(value is not None for value in original_source_uuids)
        assert reparsed_source_uuids == original_source_uuids
    else:
        assert all(value is None for value in original_source_uuids)
        assert all(value is None for value in reparsed_source_uuids)


def test_file_entrypoint_context_uses_relative_assertions() -> None:
    entry = next(
        fixture for fixture in load_corpus_entries() if fixture["parse"]["entrypoint"] == "file"
    )
    _, page = _parse_entry(entry)
    assert page.source_path is not None
    assert page.graph_root is not None
    relative_source = Path(page.source_path).relative_to(Path(page.graph_root))
    assert relative_source.parts[0] == "pages"
    assert page.title == "/".join(relative_source.with_suffix("").parts[1:])
    snapshot_text = json.dumps(project_page(page, profile="exact_parse_v1"), sort_keys=True)
    assert page.source_path not in snapshot_text
    assert page.graph_root not in snapshot_text
