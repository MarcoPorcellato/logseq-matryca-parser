"""Strict loader for the offline, versioned parser compatibility corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CORPUS_ROOT = Path(__file__).parents[1] / "fixtures" / "compat" / "v1"


def _keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional_keys = optional or set()
    missing = required - value.keys()
    unknown = value.keys() - required - optional_keys
    if missing or unknown:
        raise ValueError(f"manifest keys missing={sorted(missing)} unknown={sorted(unknown)}")


def _relative_file(root: Path, raw_path: object, *, must_exist: bool = True) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("manifest path must be a non-empty string")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"manifest path escapes corpus root: {raw_path}")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"manifest path escapes corpus root: {raw_path}") from error
    if must_exist and not candidate.is_file():
        raise ValueError(f"manifest file does not exist: {raw_path}")
    return candidate


def _snapshot_file(root: Path, raw_path: object, *, must_exist: bool = True) -> Path:
    if not isinstance(raw_path, str):
        raise ValueError("snapshot path must be a string")
    relative = Path(raw_path)
    if len(relative.parts) < 2 or relative.parts[0] != "snapshots" or relative.suffix != ".json":
        raise ValueError(f"snapshot path must be a JSON file under snapshots/: {raw_path}")
    candidate = _relative_file(root, raw_path, must_exist=must_exist)
    try:
        candidate.relative_to((root / "snapshots").resolve())
    except ValueError as error:
        raise ValueError(f"snapshot path escapes snapshots directory: {raw_path}") from error
    return candidate


def _validate_entry(entry: object, *, root: Path) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("each fixture entry must be an object")
    _keys(
        entry,
        required={
            "id",
            "fixture_schema_version",
            "snapshot_schema_version",
            "source",
            "parse",
            "profiles",
            "expectation",
            "notes",
        },
    )
    fixture_id = entry["id"]
    if not isinstance(fixture_id, str) or not fixture_id:
        raise ValueError("fixture id must be a non-empty string")
    if entry["fixture_schema_version"] != 1 or entry["snapshot_schema_version"] != 1:
        raise ValueError(f"{fixture_id}: unsupported fixture or snapshot schema version")

    source = entry["source"]
    if not isinstance(source, dict):
        raise ValueError(f"{fixture_id}: source must be an object")
    _keys(source, required={"path", "sha256", "provenance", "license"})
    source_path = _relative_file(root, source["path"])
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source["sha256"] != digest:
        raise ValueError(f"{fixture_id}: source SHA-256 mismatch")
    if source["provenance"] != "project-authored" or source["license"] != "Apache-2.0":
        raise ValueError(f"{fixture_id}: unsupported source provenance or license")

    parse = entry["parse"]
    if not isinstance(parse, dict):
        raise ValueError(f"{fixture_id}: parse must be an object")
    _keys(parse, required={"entrypoint", "tab_size"}, optional={"page_title"})
    if parse["entrypoint"] not in {"text", "file"}:
        raise ValueError(f"{fixture_id}: unsupported parse entrypoint")
    if not isinstance(parse["tab_size"], int) or parse["tab_size"] < 1:
        raise ValueError(f"{fixture_id}: tab_size must be a positive integer")
    if parse["entrypoint"] == "text" and not isinstance(parse.get("page_title"), str):
        raise ValueError(f"{fixture_id}: text entrypoint requires page_title")
    if parse["entrypoint"] == "file" and "page_title" in parse:
        raise ValueError(f"{fixture_id}: file entrypoint derives page_title")

    profiles = entry["profiles"]
    if not isinstance(profiles, dict):
        raise ValueError(f"{fixture_id}: profiles must be an object")
    _keys(profiles, required={"exact_parse", "semantic_roundtrip"})
    _snapshot_file(root, profiles["exact_parse"], must_exist=False)
    if profiles["semantic_roundtrip"] is not True:
        raise ValueError(f"{fixture_id}: semantic round-trip profile must be enabled")

    expectation = entry["expectation"]
    if not isinstance(expectation, dict):
        raise ValueError(f"{fixture_id}: expectation must be an object")
    _keys(
        expectation,
        required={
            "outcome",
            "protected_behaviors",
            "identity_policy",
            "expected_diagnostics",
        },
    )
    if expectation["outcome"] != "valid":
        raise ValueError(f"{fixture_id}: M1-A accepts only valid fixtures")
    behaviors = expectation["protected_behaviors"]
    if (
        not isinstance(behaviors, list)
        or not behaviors
        or not all(isinstance(item, str) and item for item in behaviors)
    ):
        raise ValueError(f"{fixture_id}: protected_behaviors must be non-empty strings")
    diagnostics = expectation["expected_diagnostics"]
    if not isinstance(diagnostics, list) or not all(isinstance(item, str) for item in diagnostics):
        raise ValueError(f"{fixture_id}: expected_diagnostics must be strings")
    identity = expectation["identity_policy"]
    if not isinstance(identity, dict):
        raise ValueError(f"{fixture_id}: identity_policy must be an object")
    _keys(identity, required={"synthetic_uuid", "source_uuid", "relations"})
    if identity["synthetic_uuid"] not in {"stable", "recomputed"}:
        raise ValueError(f"{fixture_id}: invalid synthetic UUID policy")
    if identity["source_uuid"] not in {"preserve", "absent"}:
        raise ValueError(f"{fixture_id}: invalid source UUID policy")
    if identity["relations"] not in {"direct_ids", "outline_paths"}:
        raise ValueError(f"{fixture_id}: invalid relation policy")
    if identity["synthetic_uuid"] == "recomputed" and identity["relations"] == "direct_ids":
        raise ValueError(f"{fixture_id}: recomputed UUIDs require outline-path relations")
    if not isinstance(entry["notes"], str):
        raise ValueError(f"{fixture_id}: notes must be a string")
    return entry


def validate_manifest(manifest: object, *, root: Path = CORPUS_ROOT) -> tuple[dict[str, Any], ...]:
    """Validate manifest structure and return entries in deterministic ID order."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    _keys(
        manifest,
        required={"corpus_schema_version", "snapshot_schema_version", "license", "fixtures"},
    )
    if manifest["corpus_schema_version"] != 1 or manifest["snapshot_schema_version"] != 1:
        raise ValueError("unsupported corpus or snapshot schema version")
    if manifest["license"] != "Apache-2.0":
        raise ValueError("corpus license must be Apache-2.0")
    fixtures = manifest["fixtures"]
    if not isinstance(fixtures, list):
        raise ValueError("fixtures must be a list")
    entries = tuple(_validate_entry(entry, root=root) for entry in fixtures)
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("fixture ids must be unique")
    sources = [_relative_file(root, entry["source"]["path"]) for entry in entries]
    snapshots = [
        _snapshot_file(root, entry["profiles"]["exact_parse"], must_exist=False)
        for entry in entries
    ]
    if len(snapshots) != len(set(snapshots)):
        raise ValueError("exact snapshot destinations must be unique")
    if set(sources).intersection(snapshots):
        raise ValueError("source and snapshot paths must not collide")
    return tuple(sorted(entries, key=lambda entry: entry["id"]))


def load_corpus_entries(*, root: Path = CORPUS_ROOT) -> tuple[dict[str, Any], ...]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    return validate_manifest(manifest, root=root)


def load_exact_snapshot(entry: dict[str, Any], *, root: Path = CORPUS_ROOT) -> object:
    snapshot_path = _snapshot_file(root, entry["profiles"]["exact_parse"])
    return json.loads(snapshot_path.read_text(encoding="utf-8"))
