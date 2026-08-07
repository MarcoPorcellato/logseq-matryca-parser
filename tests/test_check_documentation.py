"""Tests for the deterministic maintained-documentation gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_documentation.py"
SPEC = importlib.util.spec_from_file_location("check_documentation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)

FIELDS = {
    "type": "Guide",
    "title": "Guide",
    "description": "Maintained guide.",
    "status": "stable",
    "classification": "active",
    "audience": "maintainers",
    "owner": "repository",
    "authority": "source_repository",
    "execution_mode": "reviewed",
    "last_verified": "2026-08-06",
    "verified": "2026-08-06",
    "stale_after": "2026-08-20",
    "okf_profile": "matryca_okf_inspired_quality",
    "okf_spec_version": "null",
    "supersedes": "null",
    "superseded_by": "null",
}


def _profile(root: Path, documents: tuple[str, ...] = ("docs/a.md", "docs/b.md")) -> Path:
    path = root / "docs" / "maintained.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ", ".join(f'"{field}"' for field in FIELDS)
    paths = ", ".join(f'"{document}"' for document in documents)
    path.write_text(
        f"required_frontmatter_fields = [{fields}]\nmaintained_documents = [{paths}]\n",
        encoding="utf-8",
    )
    return path


def _document(path: Path, *, body: str = "", **overrides: str | None) -> None:
    values = FIELDS | {key: value for key, value in overrides.items() if value is not None}
    for key, value in overrides.items():
        if value is None:
            values.pop(key, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = "\n".join(f"{key}: {value}" for key, value in values.items())
    path.write_text(f"---\n{frontmatter}\n---\n\n# Guide\n{body}", encoding="utf-8")


def _run(root: Path, profile: Path, capsys: pytest.CaptureFixture[str], as_of: str = "2026-08-07") -> tuple[int, str]:
    code = checker.main(["--root", str(root), "--profile", str(profile), "--as-of-date", as_of])
    return code, capsys.readouterr().out


def test_valid_bundle_and_matryca_anchor_semantics(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path)
    _document(tmp_path / "docs/a.md", classification="canonical", body="[target](b.md#linked-heading)\n")
    _document(
        tmp_path / "docs/b.md",
        type="Reference",
        title="Reference",
        body="# [Linked](elsewhere.md) Heading\n# Linked Heading\n",
    )
    (tmp_path / "docs/elsewhere.md").write_text("# Elsewhere\n", encoding="utf-8")
    code, output = _run(tmp_path, profile, capsys)
    assert (code, output) == (0, "")


def test_missing_file_frontmatter_and_field(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path, ("docs/a.md", "docs/b.md", "docs/missing.md"))
    _document(tmp_path / "docs/a.md", description=None)
    (tmp_path / "docs/b.md").write_text("# No metadata\n", encoding="utf-8")
    code, output = _run(tmp_path, profile, capsys)
    assert code == 1
    assert "DOC_FIELD_MISSING" in output
    assert "DOC_FRONTMATTER_MISSING" in output
    assert "DOC_PATH_MISSING" in output


def test_metadata_lifecycle_and_freshness_failures(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path, ("docs/a.md",))
    _document(
        tmp_path / "docs/a.md",
        status="active",
        classification="stable",
        last_verified="2026-08-05",
        verified="2026-08-08",
        stale_after="2026-08-04",
    )
    code, output = _run(tmp_path, profile, capsys)
    assert code == 1
    for finding in (
        "DOC_STATUS_INVALID",
        "DOC_CLASSIFICATION_INVALID",
        "DOC_DATE_MISMATCH",
        "DOC_VERIFIED_FUTURE",
        "DOC_STALE_ORDER",
        "DOC_STALE",
    ):
        assert finding in output


def test_each_invalid_date_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path, ("docs/a.md",))
    _document(tmp_path / "docs/a.md", last_verified="bad", verified="also-bad", stale_after="never")
    code, output = _run(tmp_path, profile, capsys)
    assert code == 1
    assert output.count("DOC_DATE_INVALID") == 3


def test_link_missing_anchor_escape_and_fenced_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path)
    _document(
        tmp_path / "docs/a.md",
        classification="canonical",
        body=(
            "[missing](missing.md) [anchor](b.md#absent) [escape](../../outside.md)\n"
            "```md\n[ignored](also-missing.md)\n```\n"
            "[external](https://example.com)\n"
        ),
    )
    _document(tmp_path / "docs/b.md", type="Reference")
    code, output = _run(tmp_path, profile, capsys)
    assert code == 1
    assert "DOC_LINK_MISSING" in output
    assert "DOC_ANCHOR_MISSING" in output
    assert "DOC_LINK_ESCAPE" in output
    assert "also-missing" not in output


def test_duplicate_frontmatter_and_canonical_type(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path)
    _document(tmp_path / "docs/a.md", classification="canonical")
    _document(tmp_path / "docs/b.md", classification="canonical")
    with (tmp_path / "docs/a.md").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    text = (tmp_path / "docs/a.md").read_text(encoding="utf-8")
    (tmp_path / "docs/a.md").write_text(text.replace("title: Guide", "title: Guide\ntitle: Duplicate"), encoding="utf-8")
    code, output = _run(tmp_path, profile, capsys)
    assert code == 1
    assert "DOC_FRONTMATTER_DUPLICATE" in output
    assert "DOC_CANONICAL_DUPLICATE" in output


def test_diagnostics_are_relative_and_sorted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile = _profile(tmp_path)
    _document(tmp_path / "docs/a.md", status="invalid")
    _document(tmp_path / "docs/b.md", status="invalid", type="Reference")
    code, output = _run(tmp_path, profile, capsys)
    lines = output.splitlines()
    assert code == 1
    assert lines == sorted(lines)
    assert str(tmp_path) not in output


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [("2026-08-07", 0), ("invalid", 2)],
)
def test_cli_exit_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], as_of: str, expected: int
) -> None:
    profile = _profile(tmp_path, ("docs/a.md",))
    _document(tmp_path / "docs/a.md")
    code, _ = _run(tmp_path, profile, capsys, as_of)
    assert code == expected
