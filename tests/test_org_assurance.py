"""Strict contract tests for the test-only Org corpus manifest loader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.org_assurance.manifest import (
    CorpusManifestError,
    load_corpus_manifest,
)


def _write_corpus(root: Path, fixtures: list[dict[str, Any]] | None = None) -> None:
    source = root / "tests/fixtures/org/source.org"
    exact = root / "tests/org_assurance/exact_v1/source.json"
    semantic = root / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    for path in (source, exact, semantic):
        path.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"* Synthetic page\n")
    exact.write_text(
        '{"schema_version": 1, "source_text": "* Synthetic page\\n", "elements": []}\n',
        encoding="utf-8",
    )
    semantic.write_text(
        '{"schema_version": 1, "page_title": "Synthetic page", "blocks": [], '
        '"page_properties": [], "references": [], "timestamps": [], '
        '"opaque": [], "diagnostics": []}\n',
        encoding="utf-8",
    )
    fixture: dict[str, Any] = {
        "id": "synthetic-page",
        "source_path": "tests/fixtures/org/source.org",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "provenance": "project-authored",
        "license": "Apache-2.0",
        "parse": {"entrypoint": "text", "page_title": "Synthetic page"},
        "exact_expectation": "tests/org_assurance/exact_v1/source.json",
        "semantic_expectation": ("tests/org_assurance/logseq_org_semantic_v1/source.json"),
        "protected_invariant": "Source bytes remain unchanged.",
    }
    manifest = {
        "schema_version": 1,
        "exact_profile": "org_exact_v1",
        "semantic_profile": "logseq_org_semantic_v1",
        "fixtures": [fixture] if fixtures is None else fixtures,
    }
    manifest_path = root / "tests/org_assurance/manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def _manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / "tests/org_assurance/manifest.json").read_text(encoding="utf-8"))


def _save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    (root / "tests/org_assurance/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _assert_code(root: Path, code: str) -> None:
    with pytest.raises(CorpusManifestError) as caught:
        load_corpus_manifest(root)
    assert caught.value.code == code


def test_loads_manifest_and_returns_repo_relative_cases_deterministically(
    tmp_path: Path,
) -> None:
    _write_corpus(tmp_path)

    first = load_corpus_manifest(tmp_path)
    second = load_corpus_manifest(tmp_path)

    assert first == second
    assert len(first) == 1
    case = first[0]
    assert case.id == "synthetic-page"
    assert case.source_path == Path("tests/fixtures/org/source.org")
    assert case.source_sha256 == hashlib.sha256(b"* Synthetic page\n").hexdigest()
    assert case.entrypoint == "text"
    assert case.page_title == "Synthetic page"
    assert case.exact_expectation == Path("tests/org_assurance/exact_v1/source.json")
    assert case.semantic_expectation == Path(
        "tests/org_assurance/logseq_org_semantic_v1/source.json"
    )
    assert case.protected_invariant == "Source bytes remain unchanged."
    with pytest.raises((AttributeError, TypeError)):
        case.id = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda data: data.update(extra=True), "manifest_schema_invalid"),
        (lambda data: data.pop("fixtures"), "manifest_schema_invalid"),
        (lambda data: data.update(schema_version=True), "profile_version_unsupported"),
        (lambda data: data.update(schema_version=2), "profile_version_unsupported"),
        (lambda data: data.update(exact_profile="other"), "profile_version_unsupported"),
        (
            lambda data: data.update(semantic_profile="other"),
            "profile_version_unsupported",
        ),
    ],
)
def test_rejects_invalid_manifest_schema_and_profiles(
    tmp_path: Path, mutate: Any, code: str
) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    mutate(manifest)
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, code)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda fixture: fixture.update(extra=True), "manifest_schema_invalid"),
        (lambda fixture: fixture.pop("id"), "manifest_schema_invalid"),
        (
            lambda fixture: fixture.update(provenance="upstream-copy"),
            "fixture_provenance_invalid",
        ),
        (
            lambda fixture: fixture.update(license="GPL-3.0-only"),
            "fixture_license_invalid",
        ),
        (
            lambda fixture: fixture.update(source_sha256="A" * 64),
            "fixture_hash_mismatch",
        ),
        (
            lambda fixture: fixture.update(protected_invariant=""),
            "manifest_schema_invalid",
        ),
    ],
)
def test_rejects_invalid_fixture_fields(tmp_path: Path, mutate: Any, code: str) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    mutate(manifest["fixtures"][0])
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, code)


def test_rejects_source_hash_drift(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    source = tmp_path / "tests/fixtures/org/source.org"
    source.write_bytes(source.read_bytes() + b"changed\n")

    _assert_code(tmp_path, "fixture_hash_mismatch")


@pytest.mark.parametrize(
    "source_path",
    [
        "/tmp/source.org",
        "tests/fixtures/org/../outside.org",
        "tests/fixtures/org/./source.org",
        "tests\\fixtures\\org\\source.org",
        "tests/fixtures/other/source.org",
        "tests/fixtures/org/source.md",
        "tests/fixtures/org",
    ],
)
def test_rejects_noncanonical_or_out_of_scope_source_paths(
    tmp_path: Path, source_path: str
) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["fixtures"][0]["source_path"] = source_path
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, "fixture_path_invalid")


def test_rejects_symlink_source_component(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    org_root = tmp_path / "tests/fixtures/org"
    source = org_root / "source.org"
    source.unlink()
    source.symlink_to(tmp_path / "tests/org_assurance/manifest.json")

    _assert_code(tmp_path, "fixture_path_invalid")


def test_rejects_symlink_directory_component(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    fixtures = tmp_path / "tests/fixtures"
    (fixtures / "org").rename(fixtures / "org-real")
    (fixtures / "org").symlink_to(fixtures / "org-real", target_is_directory=True)

    _assert_code(tmp_path, "fixture_path_invalid")


def test_rejects_non_regular_source_file(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    source = tmp_path / "tests/fixtures/org/source.org"
    source.unlink()
    source.mkdir()

    _assert_code(tmp_path, "fixture_path_invalid")


def test_maps_source_read_failure_to_fixture_path_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_corpus(tmp_path)
    source = tmp_path / "tests/fixtures/org/source.org"
    original_read_bytes = Path.read_bytes

    def read_bytes(path: Path) -> bytes:
        if path == source:
            raise PermissionError("synthetic read denial")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)

    _assert_code(tmp_path, "fixture_path_invalid")


@pytest.mark.parametrize(
    ("parse", "code"),
    [
        ({"entrypoint": "unknown"}, "fixture_parse_invalid"),
        ({"entrypoint": "text"}, "fixture_parse_invalid"),
        ({"entrypoint": "text", "page_title": "  "}, "fixture_parse_invalid"),
        ({"entrypoint": "text", "page_title": "Title", "extra": True}, "fixture_parse_invalid"),
        ({"entrypoint": "file"}, "fixture_parse_invalid"),
        ({"entrypoint": "file", "page_title": "  "}, "fixture_parse_invalid"),
        ({"entrypoint": "file", "extra": True}, "fixture_parse_invalid"),
    ],
)
def test_rejects_invalid_parse_modes_and_page_titles(
    tmp_path: Path, parse: dict[str, Any], code: str
) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["fixtures"][0]["parse"] = parse
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, code)


def test_rejects_file_entrypoint_without_page_title(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["fixtures"][0]["parse"] = {"entrypoint": "file"}
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, "fixture_parse_invalid")


def test_accepts_file_entrypoint_with_explicit_page_title(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["fixtures"][0]["parse"] = {
        "entrypoint": "file",
        "page_title": "Caller-selected file title",
    }
    _save_manifest(tmp_path, manifest)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["page_title"] = "Caller-selected file title"
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    cases = load_corpus_manifest(tmp_path)

    assert cases[0].entrypoint == "file"
    assert cases[0].page_title == "Caller-selected file title"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exact_expectation", "/tmp/exact.json"),
        ("exact_expectation", "tests/org_assurance/exact_v1/../outside.json"),
        ("exact_expectation", "tests/org_assurance/exact_v1/source.yaml"),
        (
            "semantic_expectation",
            "tests/org_assurance/exact_v1/source.json",
        ),
        (
            "semantic_expectation",
            "tests/org_assurance/logseq_org_semantic_v1/missing.json",
        ),
    ],
)
def test_rejects_invalid_projection_paths(tmp_path: Path, field: str, value: str) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["fixtures"][0][field] = value
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, "projection_path_invalid")


def test_rejects_symlink_projection_component(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    exact_dir = tmp_path / "tests/org_assurance/exact_v1"
    (exact_dir / "source.json").unlink()
    (exact_dir / "source.json").symlink_to(tmp_path / "tests/org_assurance/manifest.json")

    _assert_code(tmp_path, "projection_path_invalid")


@pytest.mark.parametrize(
    ("profile", "payload", "code"),
    [
        (
            "exact",
            {"schema_version": 1, "source_text": "source", "elements": [], "extra": 1},
            "projection_path_invalid",
        ),
        (
            "exact",
            {"schema_version": 1, "elements": []},
            "projection_path_invalid",
        ),
        (
            "exact",
            {"schema_version": 2, "source_text": "source", "elements": []},
            "profile_version_unsupported",
        ),
        (
            "exact",
            {"schema_version": True, "source_text": "source", "elements": []},
            "profile_version_unsupported",
        ),
        (
            "semantic",
            {
                "schema_version": 1,
                "page_title": "Title",
                "blocks": [],
                "page_properties": [],
                "references": [],
                "timestamps": [],
                "opaque": [],
            },
            "projection_path_invalid",
        ),
        (
            "semantic",
            {
                "schema_version": 1,
                "page_title": " ",
                "blocks": [],
                "page_properties": [],
                "references": [],
                "timestamps": [],
                "opaque": [],
                "diagnostics": [],
            },
            "projection_path_invalid",
        ),
    ],
)
def test_rejects_invalid_projection_json_shape_or_schema(
    tmp_path: Path, profile: str, payload: dict[str, Any], code: str
) -> None:
    _write_corpus(tmp_path)
    path = (
        tmp_path / "tests/org_assurance/exact_v1/source.json"
        if profile == "exact"
        else tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    _assert_code(tmp_path, code)


@pytest.mark.parametrize(
    "element",
    [
        {"kind": "unknown", "line_start": 1, "line_end": 1},
        {
            "kind": "paragraph",
            "line_start": 1,
            "line_end": 1,
            "text": "body",
            "extra": True,
        },
        {"kind": "paragraph", "line_start": True, "line_end": 1, "text": "body"},
        {"kind": "paragraph", "line_start": 2, "line_end": 1, "text": "body"},
        {
            "kind": "heading",
            "line_start": 1,
            "line_end": 1,
            "level": 1,
            "title": "Heading",
            "marker": None,
            "priority": None,
            "tags": ["org", 1],
        },
        {
            "kind": "list",
            "line_start": 1,
            "line_end": 1,
            "ordered": False,
            "items": [{"text": "parent", "items": [{"text": "child", "items": [], "extra": 1}]}],
        },
    ],
)
def test_rejects_malformed_nested_exact_elements(tmp_path: Path, element: dict[str, Any]) -> None:
    _write_corpus(tmp_path)
    exact_path = tmp_path / "tests/org_assurance/exact_v1/source.json"
    exact = json.loads(exact_path.read_text(encoding="utf-8"))
    exact["elements"] = [element]
    exact_path.write_text(json.dumps(exact), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_rejects_exact_element_span_after_source_end(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    exact_path = tmp_path / "tests/org_assurance/exact_v1/source.json"
    exact = json.loads(exact_path.read_text(encoding="utf-8"))
    exact["elements"] = [{"kind": "paragraph", "line_start": 2, "line_end": 2, "text": "body"}]
    exact_path.write_text(json.dumps(exact), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


@pytest.mark.parametrize(
    ("field", "record"),
    [
        (
            "blocks",
            {
                "ordinal": True,
                "title": "Heading",
                "marker": None,
                "priority": None,
                "tags": [],
                "parent_ordinal": None,
                "line_start": 1,
            },
        ),
        (
            "blocks",
            {
                "ordinal": 0,
                "title": "Heading",
                "marker": None,
                "priority": None,
                "tags": [],
                "parent_ordinal": 1,
                "line_start": 1,
            },
        ),
        ("page_properties", {"scope": "heading:9", "name": "ALIAS", "value": "Other"}),
        ("references", {"kind": "page", "target": "Other", "resolution": "resolved"}),
        (
            "timestamps",
            {"kind": "scheduled", "date": "2026-02-30", "raw": "SCHEDULED"},
        ),
        (
            "opaque",
            {"kind": "file_link", "line_start": 1, "resolution": "resolved"},
        ),
        (
            "diagnostics",
            {"code": "ORG_UNCLOSED_DRAWER", "severity": "warning", "line": 1},
        ),
    ],
)
def test_rejects_malformed_nested_semantic_records(
    tmp_path: Path, field: str, record: dict[str, Any]
) -> None:
    _write_corpus(tmp_path)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic[field] = [record]
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


@pytest.mark.parametrize(
    ("diagnostic_code", "severity"),
    [
        ("ORG_PAGE_TITLE_REQUIRED", "error"),
        ("ORG_PAGE_TITLE_TOO_LARGE", "error"),
        ("ORG_INVALID_UNICODE", "error"),
        ("ORG_SOURCE_TOO_LARGE", "error"),
        ("ORG_LINE_LIMIT_EXCEEDED", "error"),
        ("ORG_ELEMENT_LIMIT_EXCEEDED", "error"),
        ("ORG_NESTING_LIMIT_EXCEEDED", "error"),
        ("ORG_INVALID_UTF8", "error"),
        ("ORG_DIAGNOSTICS_TRUNCATED", "error"),
    ],
)
def test_rejects_no_document_diagnostics_in_document_projection(
    tmp_path: Path, diagnostic_code: str, severity: str
) -> None:
    _write_corpus(tmp_path)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["diagnostics"] = [{"code": diagnostic_code, "severity": severity}]
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_accepts_document_projection_with_255_ordinary_diagnostics(
    tmp_path: Path,
) -> None:
    _write_corpus(tmp_path)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    diagnostic = {"code": "ORG_OPAQUE_EXECUTABLE_SYNTAX", "severity": "warning"}
    semantic["diagnostics"] = [diagnostic.copy() for _ in range(255)]
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    cases = load_corpus_manifest(tmp_path)

    assert len(cases) == 1


def test_rejects_document_projection_with_256_ordinary_diagnostics(
    tmp_path: Path,
) -> None:
    _write_corpus(tmp_path)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    diagnostic = {"code": "ORG_OPAQUE_EXECUTABLE_SYNTAX", "severity": "warning"}
    semantic["diagnostics"] = [diagnostic.copy() for _ in range(256)]
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_rejects_exact_source_text_that_disagrees_with_source_fixture(
    tmp_path: Path,
) -> None:
    _write_corpus(tmp_path)
    exact_path = tmp_path / "tests/org_assurance/exact_v1/source.json"
    exact = json.loads(exact_path.read_text(encoding="utf-8"))
    exact["source_text"] = "* Different source\n"
    exact_path.write_text(json.dumps(exact), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_rejects_text_mode_semantic_title_that_disagrees_with_manifest(
    tmp_path: Path,
) -> None:
    _write_corpus(tmp_path)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["page_title"] = "Different title"
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_file_expectation_must_match_explicit_page_title(
    tmp_path: Path,
) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["fixtures"][0]["parse"] = {
        "entrypoint": "file",
        "page_title": "Caller-selected file title",
    }
    _save_manifest(tmp_path, manifest)
    semantic_path = tmp_path / "tests/org_assurance/logseq_org_semantic_v1/source.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic["page_title"] = "Independent expected title"
    semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_rejects_invalid_projection_json(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    (tmp_path / "tests/org_assurance/exact_v1/source.json").write_text("{invalid", encoding="utf-8")

    _assert_code(tmp_path, "projection_path_invalid")


def test_rejects_duplicate_fixture_ids_and_source_paths(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    duplicate_id = dict(manifest["fixtures"][0])
    duplicate_id["source_path"] = "tests/fixtures/org/second.org"
    (tmp_path / duplicate_id["source_path"]).write_text("second\n", encoding="utf-8")
    duplicate_id["source_sha256"] = hashlib.sha256(b"second\n").hexdigest()
    manifest["fixtures"].append(duplicate_id)
    _save_manifest(tmp_path, manifest)
    _assert_code(tmp_path, "duplicate_fixture_id")

    duplicate_path = dict(duplicate_id)
    duplicate_path["id"] = "second-id"
    duplicate_path["source_path"] = manifest["fixtures"][0]["source_path"]
    duplicate_path["source_sha256"] = manifest["fixtures"][0]["source_sha256"]
    manifest["fixtures"][1] = duplicate_path
    _save_manifest(tmp_path, manifest)
    _assert_code(tmp_path, "fixture_path_invalid")


def test_rejects_duplicate_projection_paths(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    duplicate = dict(manifest["fixtures"][0])
    duplicate.update(
        id="second-id",
        source_path="tests/fixtures/org/second.org",
        exact_expectation="tests/org_assurance/exact_v1/second.json",
        semantic_expectation=("tests/org_assurance/logseq_org_semantic_v1/second.json"),
    )
    (tmp_path / duplicate["source_path"]).write_text("second\n", encoding="utf-8")
    duplicate["source_sha256"] = hashlib.sha256(b"second\n").hexdigest()
    (tmp_path / duplicate["exact_expectation"]).write_text("{}\n", encoding="utf-8")
    (tmp_path / duplicate["semantic_expectation"]).write_text("{}\n", encoding="utf-8")
    manifest["fixtures"].append(duplicate)
    manifest["fixtures"][1]["exact_expectation"] = manifest["fixtures"][0]["exact_expectation"]
    _save_manifest(tmp_path, manifest)

    _assert_code(tmp_path, "projection_path_invalid")


def test_preserves_manifest_order_for_multiple_cases(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    first = manifest["fixtures"][0]
    second = dict(first)
    second.update(
        id="second-page",
        source_path="tests/fixtures/org/second.org",
        parse={"entrypoint": "text", "page_title": "Second page"},
        exact_expectation="tests/org_assurance/exact_v1/second.json",
        semantic_expectation=("tests/org_assurance/logseq_org_semantic_v1/second.json"),
    )
    source = tmp_path / second["source_path"]
    source.write_bytes(b"* Second page\n")
    second["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    (tmp_path / second["exact_expectation"]).write_text(
        '{"schema_version": 1, "source_text": "* Second page\\n", "elements": []}\n',
        encoding="utf-8",
    )
    (tmp_path / second["semantic_expectation"]).write_text(
        '{"schema_version": 1, "page_title": "Second page", "blocks": [], '
        '"page_properties": [], "references": [], "timestamps": [], '
        '"opaque": [], "diagnostics": []}\n',
        encoding="utf-8",
    )
    manifest["fixtures"] = [second, first]
    _save_manifest(tmp_path, manifest)

    cases = load_corpus_manifest(tmp_path)

    assert [case.id for case in cases] == ["second-page", "synthetic-page"]


def test_loads_canonical_org_corpus_when_present() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "tests/org_assurance/manifest.json"
    if not manifest_path.exists():
        pytest.skip("canonical D1 Org corpus has not been authored yet")

    cases = load_corpus_manifest(repo_root)
    repeated_cases = load_corpus_manifest(repo_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixtures_by_id = {fixture["id"]: fixture for fixture in manifest["fixtures"]}

    assert len(cases) == 6
    assert cases == repeated_cases
    assert [case.id for case in cases] == sorted(case.id for case in cases)
    assert set(fixtures_by_id) == {case.id for case in cases}
    for case in cases:
        fixture = fixtures_by_id[case.id]
        assert fixture["provenance"] == "project-authored"
        assert fixture["license"] == "Apache-2.0"
        source_bytes = (repo_root / case.source_path).read_bytes()
        exact = json.loads((repo_root / case.exact_expectation).read_text(encoding="utf-8"))
        semantic = json.loads((repo_root / case.semantic_expectation).read_text(encoding="utf-8"))
        assert exact["source_text"].encode("utf-8") == source_bytes
        assert semantic["page_title"] == fixture["parse"]["page_title"]
