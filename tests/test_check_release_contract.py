from __future__ import annotations

from pathlib import Path

from scripts.check_release_contract import validate_release


def _changelog(version: str = "1.7.0", *, unreleased: str = "") -> str:
    return f"""# Changelog

## [Unreleased]
{unreleased}

## [{version}] - 2026-08-08

### Added

- Verified release artifact lineage.
"""


def test_valid_release_contract() -> None:
    failures, notes = validate_release(
        tag="v1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text=_changelog(),
    )

    assert failures == []
    assert notes is not None
    assert "Verified release artifact lineage" in notes


def test_repository_relative_release_links_must_exist(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "present.md").write_text("# Present\n", encoding="utf-8")
    changelog = _changelog().replace(
        "- Verified release artifact lineage.",
        "\n".join(
            (
                "- [Present](docs/present.md#present)",
                "- [Missing](examples/missing.py)",
                "- [External](https://example.com/release)",
            )
        ),
    )

    failures, _ = validate_release(
        tag="v1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text=changelog,
        repository_root=tmp_path,
    )

    assert failures == ["release notes link target does not exist: 'examples/missing.py'"]


def test_repository_relative_release_links_cannot_escape(tmp_path: Path) -> None:
    changelog = _changelog().replace(
        "- Verified release artifact lineage.",
        "- [Outside](../outside.md)",
    )

    failures, _ = validate_release(
        tag="v1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text=changelog,
        repository_root=tmp_path,
    )

    assert failures == ["release notes link escapes repository: '../outside.md'"]


def test_tag_source_and_runtime_mismatches_are_reported() -> None:
    failures, _ = validate_release(
        tag="v1.7.0",
        source="1.6.0",
        runtime="1.5.0",
        changelog_text=_changelog("1.7.0"),
    )

    assert failures == [
        "tag version '1.7.0' does not match source version '1.6.0'",
        "runtime version '1.5.0' does not match source version '1.6.0'",
    ]


def test_missing_or_empty_release_notes_fail_closed() -> None:
    missing, _ = validate_release(
        tag="v1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text=_changelog("1.6.0"),
    )
    empty, _ = validate_release(
        tag="v1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text="# Changelog\n\n## [Unreleased]\n\n## [1.7.0] - 2026-08-08\n",
    )

    assert missing == ["No changelog section found for version [1.7.0]. Known versions: 1.6.0"]
    assert empty == ["changelog section [1.7.0] has no release-note bullets"]


def test_unreleased_content_fails_before_tagging() -> None:
    failures, _ = validate_release(
        tag="v1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text=_changelog(unreleased="\n- Not finalized."),
    )

    assert failures == ["[Unreleased] must be empty before tagging"]


def test_non_semver_tag_is_rejected() -> None:
    failures, notes = validate_release(
        tag="release-1.7.0",
        source="1.7.0",
        runtime="1.7.0",
        changelog_text=_changelog(),
    )

    assert failures == ["tag 'release-1.7.0' is not a stable vX.Y.Z SemVer tag"]
    assert notes is None
