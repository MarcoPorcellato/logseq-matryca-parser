"""Unit tests for the extract_changelog release helper (scripts/extract_changelog.py).

Covers normalize_version, extract_changelog_section, iter_changelog_versions,
and error paths per issue #23.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the script as a module (it lives outside the package in scripts/).
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_changelog.py"
_spec = importlib.util.spec_from_file_location("extract_changelog", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
_extract = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _extract
_spec.loader.exec_module(_extract)

normalize_version = _extract.normalize_version
extract_changelog_section = _extract.extract_changelog_section
iter_changelog_versions = _extract.iter_changelog_versions


# ── minimal changelog fixture ────────────────────────────────────────────

MINIMAL_CHANGELOG = """# Changelog

## [Unreleased]

- Upcoming feature

## [1.0.0] - 2026-01-15

### Added
- Initial release

## [0.9.0] - 2025-12-01

### Added
- Beta feature
"""


class TestNormalizeVersion:
    """Tests for ``normalize_version()`` tag/version cleaning."""

    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            ("v1.0.0", "1.0.0"),
            ("V1.0.0", "1.0.0"),
            ("v2.3.4-beta", "2.3.4-beta"),
            ("1.0.0", "1.0.0"),
            ("  v1.0.0  ", "1.0.0"),   # whitespace stripped
            ("Unreleased", "Unreleased"),
            ("unreleased", "Unreleased"),
            ("UNRELEASED", "Unreleased"),
        ],
    )
    def test_normalize_version(self, input_val, expected):
        assert normalize_version(input_val) == expected

    def test_v_without_digit_not_stripped(self):
        """Leading 'v' without a following digit is kept as-is."""
        assert normalize_version("vintage") == "vintage"
        assert normalize_version("V-2") == "V-2"


class TestExtractChangelogSection:
    """Tests for ``extract_changelog_section()`` block extraction."""

    def test_extract_existing_version(self):
        section = extract_changelog_section(MINIMAL_CHANGELOG, "1.0.0")
        assert "## [1.0.0]" in section
        assert "- Initial release" in section
        assert section.endswith("\n")

    def test_extract_with_v_prefix(self):
        section = extract_changelog_section(MINIMAL_CHANGELOG, "v1.0.0")
        assert "## [1.0.0]" in section

    def test_extract_first_version_section(self):
        """The 0.9.0 section should be the last entry and contain beta feature."""
        section = extract_changelog_section(MINIMAL_CHANGELOG, "0.9.0")
        assert "## [0.9.0]" in section
        assert "- Beta feature" in section

    def test_missing_version_raises_lookuperror(self):
        with pytest.raises(LookupError, match="9.9.9"):
            extract_changelog_section(MINIMAL_CHANGELOG, "9.9.9")

    def test_missing_version_includes_hint_with_known_versions(self):
        with pytest.raises(LookupError, match="Known versions"):
            extract_changelog_section("# Changelog\n\n## [1.0.0]\n", "2.0.0")

    def test_unreleased_with_allow_unreleased_true(self):
        section = extract_changelog_section(
            MINIMAL_CHANGELOG, "Unreleased", allow_unreleased=True
        )
        assert "## [Unreleased]" in section
        assert "- Upcoming feature" in section

    def test_unreleased_without_allow_raises_valueerror(self):
        with pytest.raises(ValueError, match="Refusing to extract"):
            extract_changelog_section(MINIMAL_CHANGELOG, "Unreleased")

    def test_section_stops_at_next_version_heading(self):
        """Extracted section must not include subsequent version blocks."""
        section = extract_changelog_section(MINIMAL_CHANGELOG, "1.0.0")
        assert "## [1.0.0]" in section
        assert "## [0.9.0]" not in section


class TestIterChangelogVersions:
    """Tests for ``iter_changelog_versions()`` version listing."""

    def test_returns_versions_excluding_unreleased(self):
        versions = iter_changelog_versions(MINIMAL_CHANGELOG)
        assert versions == ["1.0.0", "0.9.0"]

    def test_empty_changelog_returns_empty_list(self):
        assert iter_changelog_versions("# Changelog\n\n") == []

    def test_only_unreleased_returns_empty(self):
        assert iter_changelog_versions("## [Unreleased]\n") == []
