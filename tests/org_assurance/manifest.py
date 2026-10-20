"""Test-only loader for the versioned Logseq Org fixture corpus."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Literal, NoReturn

ManifestErrorCode = Literal[
    "manifest_schema_invalid",
    "profile_version_unsupported",
    "duplicate_fixture_id",
    "fixture_path_invalid",
    "fixture_hash_mismatch",
    "fixture_provenance_invalid",
    "fixture_license_invalid",
    "fixture_parse_invalid",
    "projection_path_invalid",
]


class CorpusManifestError(ValueError):
    """Manifest failure with a stable, machine-readable reason code."""

    def __init__(self, code: ManifestErrorCode, message: str) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported corpus manifest error code")
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class OrgFixtureCase:
    """One validated fixture and its independent expected projections."""

    id: str
    source_path: Path
    source_sha256: str
    entrypoint: Literal["text", "file"]
    page_title: str
    exact_expectation: Path
    semantic_expectation: Path
    protected_invariant: str


_MANIFEST_KEYS = frozenset({"schema_version", "exact_profile", "semantic_profile", "fixtures"})
_FIXTURE_KEYS = frozenset(
    {
        "id",
        "source_path",
        "source_sha256",
        "provenance",
        "license",
        "parse",
        "exact_expectation",
        "semantic_expectation",
        "protected_invariant",
    }
)
_EXACT_KEYS = frozenset({"schema_version", "source_text", "elements"})
_SEMANTIC_KEYS = frozenset(
    {
        "schema_version",
        "page_title",
        "blocks",
        "page_properties",
        "references",
        "timestamps",
        "opaque",
        "diagnostics",
    }
)
_EXACT_ELEMENT_KEYS = {
    "heading": frozenset(
        {
            "kind",
            "line_start",
            "line_end",
            "level",
            "title",
            "marker",
            "priority",
            "tags",
        }
    ),
    "paragraph": frozenset({"kind", "line_start", "line_end", "text"}),
    "list": frozenset({"kind", "line_start", "line_end", "ordered", "items"}),
    "source_block": frozenset({"kind", "line_start", "line_end", "language"}),
    "query_block": frozenset({"kind", "line_start", "line_end"}),
    "dynamic_block": frozenset({"kind", "line_start", "line_end", "name"}),
    "macro_directive": frozenset({"kind", "line_start", "line_end", "name"}),
    "directive": frozenset({"kind", "line_start", "line_end", "name", "value"}),
    "property_drawer": frozenset({"kind", "line_start", "line_end", "properties"}),
    "timestamp": frozenset({"kind", "line_start", "line_end", "kind_name", "raw"}),
    "opaque_unterminated": frozenset({"kind", "line_start", "line_end", "element", "raw"}),
}
_SEMANTIC_RECORD_KEYS = {
    "blocks": frozenset(
        {
            "ordinal",
            "title",
            "marker",
            "priority",
            "tags",
            "parent_ordinal",
            "line_start",
        }
    ),
    "page_properties": frozenset({"scope", "name", "value"}),
    "references": frozenset({"kind", "target", "resolution"}),
    "timestamps": frozenset({"kind", "date", "raw"}),
}
_OPAQUE_RECORD_KEYS = {
    "source_block": frozenset({"kind", "line_start", "line_end"}),
    "query_block": frozenset({"kind", "line_start", "line_end"}),
    "dynamic_block": frozenset({"kind", "line_start", "line_end"}),
    "macro_directive_and_expansion": frozenset({"kind", "line_start", "line_end"}),
    "list": frozenset({"kind", "line_start", "line_end"}),
    "unterminated_property_drawer": frozenset({"kind", "line_start", "line_end"}),
    "external_link": frozenset({"kind", "line_start"}),
    "closed_timestamp": frozenset({"kind", "line_start"}),
    "clock_timestamp": frozenset({"kind", "line_start"}),
    "file_link": frozenset({"kind", "line_start", "resolution"}),
}
_DIAGNOSTIC_SEVERITIES = {
    "ORG_OPAQUE_EXECUTABLE_SYNTAX": "warning",
    "ORG_UNCLOSED_DRAWER": "error",
    "ORG_PAGE_TITLE_REQUIRED": "error",
    "ORG_PAGE_TITLE_TOO_LARGE": "error",
    "ORG_INVALID_UNICODE": "error",
    "ORG_SOURCE_TOO_LARGE": "error",
    "ORG_LINE_LIMIT_EXCEEDED": "error",
    "ORG_ELEMENT_LIMIT_EXCEEDED": "error",
    "ORG_NESTING_LIMIT_EXCEEDED": "error",
    "ORG_INVALID_UTF8": "error",
    "ORG_DIAGNOSTICS_TRUNCATED": "error",
}
_DOCUMENT_DIAGNOSTIC_SEVERITIES = {
    "ORG_OPAQUE_EXECUTABLE_SYNTAX": "warning",
    "ORG_UNCLOSED_DRAWER": "error",
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_ERROR_CODES = frozenset(
    {
        "manifest_schema_invalid",
        "profile_version_unsupported",
        "duplicate_fixture_id",
        "fixture_path_invalid",
        "fixture_hash_mismatch",
        "fixture_provenance_invalid",
        "fixture_license_invalid",
        "fixture_parse_invalid",
        "projection_path_invalid",
    }
)


def _fail(code: ManifestErrorCode, message: str) -> NoReturn:
    if code not in _ERROR_CODES:
        raise AssertionError("internal manifest error code is not registered")
    raise CorpusManifestError(code, message)


def _has_exact_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, dict) and value.keys() == keys


def _json_object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_json(path: Path, code: ManifestErrorCode) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object_without_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        _fail(code, f"cannot read valid UTF-8 JSON: {path.name}")


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_or_none(value: object) -> bool:
    return value is None or isinstance(value, str)


def _integer_at_least(value: object, minimum: int) -> bool:
    return type(value) is int and value >= minimum


def _logical_line_count(source_text: str) -> int:
    return source_text.count("\n") + int(bool(source_text) and not source_text.endswith("\n"))


def _valid_line_span(value: dict[str, Any], line_count: int, *, require_end: bool) -> bool:
    start = value.get("line_start")
    if type(start) is not int or not 1 <= start <= line_count:
        return False
    if not require_end:
        return True
    end = value.get("line_end")
    return type(end) is int and start <= end <= line_count


def _valid_line_number(value: object, line_count: int) -> bool:
    return type(value) is int and 1 <= value <= line_count


def _valid_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _valid_list_items(value: object) -> bool:
    if not isinstance(value, list):
        return False
    pending = [value]
    while pending:
        items = pending.pop()
        for item in items:
            if not _has_exact_keys(item, frozenset({"text", "items"})):
                return False
            if not isinstance(item["text"], str) or not isinstance(item["items"], list):
                return False
            pending.append(item["items"])
    return True


def _valid_exact_element(value: object, line_count: int) -> bool:
    if not isinstance(value, dict):
        return False
    kind = value.get("kind")
    keys = _EXACT_ELEMENT_KEYS.get(kind) if isinstance(kind, str) else None
    if keys is None or not _has_exact_keys(value, keys):
        return False
    if not _valid_line_span(value, line_count, require_end=True):
        return False

    if kind == "heading":
        return (
            _integer_at_least(value["level"], 1)
            and isinstance(value["title"], str)
            and _string_or_none(value["marker"])
            and _string_or_none(value["priority"])
            and _valid_string_list(value["tags"])
        )
    if kind == "paragraph":
        return isinstance(value["text"], str)
    if kind == "list":
        return type(value["ordered"]) is bool and _valid_list_items(value["items"])
    if kind == "source_block":
        return isinstance(value["language"], str)
    if kind in {"dynamic_block", "macro_directive"}:
        return _nonempty_string(value["name"])
    if kind == "directive":
        return _nonempty_string(value["name"]) and isinstance(value["value"], str)
    if kind == "property_drawer":
        properties = value["properties"]
        return isinstance(properties, list) and all(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(part, str) for part in pair)
            for pair in properties
        )
    if kind == "timestamp":
        return (
            isinstance(value["kind_name"], str)
            and value["kind_name"] in {"SCHEDULED", "DEADLINE", "CLOSED", "CLOCK"}
            and _nonempty_string(value["raw"])
        )
    if kind == "opaque_unterminated":
        return _nonempty_string(value["element"]) and isinstance(value["raw"], str)
    return kind == "query_block"


def _valid_exact_elements(value: object, line_count: int) -> bool:
    if not isinstance(value, list):
        return False
    previous_start = 0
    for element in value:
        if not _valid_exact_element(element, line_count):
            return False
        line_start = element["line_start"]
        if line_start < previous_start:
            return False
        previous_start = line_start
    return True


def _valid_semantic_records(value: dict[str, Any], line_count: int) -> bool:
    blocks = value["blocks"]
    block_lines: dict[int, int] = {}
    previous_block_line = 0
    for ordinal, block in enumerate(blocks):
        if not _has_exact_keys(block, _SEMANTIC_RECORD_KEYS["blocks"]):
            return False
        if (
            type(block["ordinal"]) is not int
            or block["ordinal"] != ordinal
            or not isinstance(block["title"], str)
            or not _string_or_none(block["marker"])
            or not _string_or_none(block["priority"])
            or not _valid_string_list(block["tags"])
            or not _valid_line_span(block, line_count, require_end=False)
            or block["line_start"] < previous_block_line
        ):
            return False
        parent = block["parent_ordinal"]
        if parent is not None and (
            not _integer_at_least(parent, 0)
            or parent >= ordinal
            or block_lines[parent] >= block["line_start"]
        ):
            return False
        block_lines[ordinal] = block["line_start"]
        previous_block_line = block["line_start"]

    for prop in value["page_properties"]:
        if (
            not _has_exact_keys(prop, _SEMANTIC_RECORD_KEYS["page_properties"])
            or not isinstance(prop["scope"], str)
            or not _nonempty_string(prop["name"])
            or not isinstance(prop["value"], str)
        ):
            return False
        if prop["scope"] != "document":
            match = re.fullmatch(r"heading:(0|[1-9][0-9]*)", prop["scope"])
            if match is None or int(match.group(1)) not in block_lines:
                return False

    for reference in value["references"]:
        if (
            not _has_exact_keys(reference, _SEMANTIC_RECORD_KEYS["references"])
            or reference["kind"] != "page"
            or not _nonempty_string(reference["target"])
            or reference["resolution"] != "unresolved"
        ):
            return False

    for timestamp in value["timestamps"]:
        if (
            not _has_exact_keys(timestamp, _SEMANTIC_RECORD_KEYS["timestamps"])
            or not isinstance(timestamp["kind"], str)
            or timestamp["kind"] not in {"scheduled", "deadline"}
            or not _nonempty_string(timestamp["raw"])
            or not isinstance(timestamp["date"], str)
        ):
            return False
        try:
            if date.fromisoformat(timestamp["date"]).isoformat() != timestamp["date"]:
                return False
        except ValueError:
            return False

    for opaque in value["opaque"]:
        if not isinstance(opaque, dict):
            return False
        kind = opaque.get("kind")
        keys = _OPAQUE_RECORD_KEYS.get(kind) if isinstance(kind, str) else None
        if keys is None or not _has_exact_keys(opaque, keys):
            return False
        if not _valid_line_span(opaque, line_count, require_end="line_end" in keys):
            return False
        if kind == "file_link" and opaque["resolution"] != "never":
            return False

    diagnostics = value["diagnostics"]
    if len(diagnostics) > 255:
        return False
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            return False
        keys = frozenset({"code", "severity"})
        if "line" in diagnostic:
            keys = keys | {"line"}
        if not _has_exact_keys(diagnostic, keys):
            return False
        if not isinstance(diagnostic["code"], str):
            return False
        expected_severity = _DOCUMENT_DIAGNOSTIC_SEVERITIES.get(diagnostic["code"])
        if (
            expected_severity is None
            or diagnostic["severity"] != expected_severity
            or ("line" in diagnostic and not _valid_line_number(diagnostic["line"], line_count))
        ):
            return False

    return True


def _checked_file(
    repo_root: Path,
    raw_path: object,
    prefix: tuple[str, ...],
    suffix: str,
    code: ManifestErrorCode,
) -> tuple[Path, Path]:
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        _fail(code, "path must be a canonical repository-relative POSIX path")
    if "\x00" in raw_path:
        _fail(code, "path contains a NUL byte")
    posix_path = PurePosixPath(raw_path)
    parts = posix_path.parts
    if (
        posix_path.is_absolute()
        or not parts
        or raw_path != posix_path.as_posix()
        or any(part in {"", ".", ".."} for part in raw_path.split("/"))
        or parts[: len(prefix)] != prefix
        or len(parts) <= len(prefix)
        or not parts[-1].endswith(suffix)
    ):
        _fail(code, "path is noncanonical or outside its assigned corpus root")

    relative = Path(*parts)
    candidate = repo_root / relative
    current = repo_root
    try:
        for index, part in enumerate(parts):
            current = current / part
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode):
                _fail(code, "symlink path components are forbidden")
            if index < len(parts) - 1 and not stat.S_ISDIR(mode):
                _fail(code, "path component is not a directory")
            if index == len(parts) - 1 and not stat.S_ISREG(mode):
                _fail(code, "corpus path is not a regular file")
    except OSError:
        _fail(code, "corpus path does not exist or cannot be inspected")
    return relative, candidate


def _validate_projection(
    path: Path, profile: Literal["exact", "semantic"], line_count: int = 0
) -> dict[str, Any]:
    value = _read_json(path, "projection_path_invalid")
    keys = _EXACT_KEYS if profile == "exact" else _SEMANTIC_KEYS
    if not _has_exact_keys(value, keys):
        _fail("projection_path_invalid", "projection JSON has unexpected root keys")
    schema_version = value["schema_version"]
    if type(schema_version) is not int or schema_version != 1:
        _fail("profile_version_unsupported", "projection schema version is unsupported")
    if profile == "exact":
        if not isinstance(value["source_text"], str) or not isinstance(value["elements"], list):
            _fail("projection_path_invalid", "exact projection fields have invalid types")
        if not _valid_exact_elements(value["elements"], _logical_line_count(value["source_text"])):
            _fail("projection_path_invalid", "exact projection elements are invalid")
        return value
    if (
        not isinstance(value["page_title"], str)
        or not value["page_title"].strip()
        or any(
            not isinstance(value[field], list)
            for field in (
                "blocks",
                "page_properties",
                "references",
                "timestamps",
                "opaque",
                "diagnostics",
            )
        )
    ):
        _fail(
            "projection_path_invalid",
            "semantic projection fields have invalid types",
        )
    if not _valid_semantic_records(value, line_count):
        _fail("projection_path_invalid", "semantic projection records are invalid")
    return value


def load_corpus_manifest(repo_root: Path) -> tuple[OrgFixtureCase, ...]:
    """Load and validate the test-only Org corpus manifest deterministically."""
    root = Path(repo_root)
    manifest_rel = Path("tests/org_assurance/manifest.json")
    manifest_path = root / manifest_rel
    try:
        mode = manifest_path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            _fail("manifest_schema_invalid", "manifest must be a regular non-symlink file")
    except OSError:
        _fail("manifest_schema_invalid", "manifest file is missing or unreadable")

    manifest = _read_json(manifest_path, "manifest_schema_invalid")
    if not _has_exact_keys(manifest, _MANIFEST_KEYS):
        _fail("manifest_schema_invalid", "manifest has unexpected root keys")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        _fail("profile_version_unsupported", "manifest schema version is unsupported")
    if (
        manifest["exact_profile"] != "org_exact_v1"
        or manifest["semantic_profile"] != "logseq_org_semantic_v1"
    ):
        _fail("profile_version_unsupported", "manifest projection profile is unsupported")
    fixtures = manifest["fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        _fail("manifest_schema_invalid", "manifest fixtures must be a nonempty array")

    cases: list[OrgFixtureCase] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    seen_exact: set[str] = set()
    seen_semantic: set[str] = set()
    for fixture in fixtures:
        if not _has_exact_keys(fixture, _FIXTURE_KEYS):
            _fail("manifest_schema_invalid", "fixture has unexpected or missing keys")

        fixture_id = fixture["id"]
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            _fail("manifest_schema_invalid", "fixture id must be a nonempty string")
        if fixture_id in seen_ids:
            _fail("duplicate_fixture_id", "fixture ids must be unique")
        seen_ids.add(fixture_id)

        source_rel, source_path = _checked_file(
            root,
            fixture["source_path"],
            ("tests", "fixtures", "org"),
            ".org",
            "fixture_path_invalid",
        )
        source_key = source_rel.as_posix()
        if source_key in seen_sources:
            _fail("fixture_path_invalid", "source paths must be unique")
        seen_sources.add(source_key)

        digest = fixture["source_sha256"]
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            _fail("fixture_hash_mismatch", "source SHA-256 must be lowercase hexadecimal")
        try:
            source_bytes = source_path.read_bytes()
        except OSError:
            _fail("fixture_path_invalid", "source file cannot be read")
        if hashlib.sha256(source_bytes).hexdigest() != digest:
            _fail("fixture_hash_mismatch", "source bytes do not match declared SHA-256")

        if fixture["provenance"] != "project-authored":
            _fail("fixture_provenance_invalid", "fixture provenance must be project-authored")
        if fixture["license"] != "Apache-2.0":
            _fail("fixture_license_invalid", "fixture license must be Apache-2.0")

        parse = fixture["parse"]
        if not isinstance(parse, dict):
            _fail("fixture_parse_invalid", "parse must be an object")
        entrypoint = parse.get("entrypoint")
        if entrypoint in {"text", "file"}:
            if set(parse) != {"entrypoint", "page_title"}:
                _fail("fixture_parse_invalid", "entrypoint requires only page_title")
            page_title = parse["page_title"]
            if not isinstance(page_title, str) or not page_title.strip():
                _fail("fixture_parse_invalid", "entrypoint requires a nonempty page_title")
        else:
            _fail("fixture_parse_invalid", "entrypoint must be text or file")

        exact_rel, exact_path = _checked_file(
            root,
            fixture["exact_expectation"],
            ("tests", "org_assurance", "exact_v1"),
            ".json",
            "projection_path_invalid",
        )
        exact_key = exact_rel.as_posix()
        if exact_key in seen_exact:
            _fail("projection_path_invalid", "exact projection paths must be unique")
        seen_exact.add(exact_key)
        exact_projection = _validate_projection(exact_path, "exact")
        try:
            decoded_source = source_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("fixture_path_invalid", "source file is not valid UTF-8")
        if exact_projection["source_text"] != decoded_source:
            _fail(
                "projection_path_invalid",
                "exact source text does not match the UTF-8 fixture",
            )

        semantic_rel, semantic_path = _checked_file(
            root,
            fixture["semantic_expectation"],
            ("tests", "org_assurance", "logseq_org_semantic_v1"),
            ".json",
            "projection_path_invalid",
        )
        semantic_key = semantic_rel.as_posix()
        if semantic_key in seen_semantic:
            _fail("projection_path_invalid", "semantic projection paths must be unique")
        seen_semantic.add(semantic_key)
        semantic_projection = _validate_projection(
            semantic_path, "semantic", _logical_line_count(decoded_source)
        )
        if semantic_projection["page_title"] != page_title:
            _fail(
                "projection_path_invalid",
                "semantic page title does not match the explicit input",
            )

        invariant = fixture["protected_invariant"]
        if not isinstance(invariant, str) or not invariant.strip():
            _fail("manifest_schema_invalid", "protected invariant must be nonempty")

        cases.append(
            OrgFixtureCase(
                id=fixture_id,
                source_path=source_rel,
                source_sha256=digest,
                entrypoint=entrypoint,
                page_title=page_title,
                exact_expectation=exact_rel,
                semantic_expectation=semantic_rel,
                protected_invariant=invariant,
            )
        )

    return tuple(cases)
