from __future__ import annotations

from pathlib import Path

import pytest

from logseq_matryca_parser.logseq_paths import (
    decode_page_title_segment,
    derive_graph_root_from_source_path,
    derive_page_title_from_source_path,
    discover_graph_files,
    encode_page_title_segment,
    filename_to_page_title,
    is_excluded_graph_path,
    page_title_to_filename,
    page_title_to_relative_path,
)


@pytest.mark.parametrize(
    ("title", "expected_stem"),
    [
        ("Simple", "Simple"),
        ("Progetti/AI/Matryca", "Progetti___AI___Matryca"),
        ("What?", "What%3F"),
        ('File:Name', "File%3AName"),
        ("Star*Path", "Star%2APath"),
        ('Pipe|Name', "Pipe%7CName"),
        ('Quote"Name', "Quote%22Name"),
    ],
)
def test_page_title_to_filename_encodes_namespaces_and_reserved_chars(
    title: str,
    expected_stem: str,
) -> None:
    assert page_title_to_filename(title) == expected_stem


@pytest.mark.parametrize(
    ("stem", "expected_title"),
    [
        ("Simple", "Simple"),
        ("Progetti___AI___Matryca", "Progetti/AI/Matryca"),
        ("What%3F", "What?"),
    ],
)
def test_filename_to_page_title_decodes_namespaces(stem: str, expected_title: str) -> None:
    assert filename_to_page_title(stem) == expected_title


def test_title_filename_roundtrip_preserves_reserved_characters() -> None:
    title = 'Notes/Topic: Alpha?'
    assert filename_to_page_title(page_title_to_filename(title)) == title


@pytest.mark.parametrize(
    ("stem", "expected_title"),
    [
        ("Projects.Secret", "Projects/Secret"),
        ("Projects%2FSecret", "Projects/Secret"),
    ],
)
def test_legacy_namespace_filename_resolution(stem: str, expected_title: str) -> None:
    """Legacy dot and percent-encoded slash filename separators decode to canonical titles."""
    assert filename_to_page_title(stem) == expected_title


def test_filename_to_page_title_preserves_dots_in_phrases_with_spaces() -> None:
    """Titles like ``Dr. Smith`` keep literal dots (LIM-001)."""
    assert filename_to_page_title("Dr. Smith") == "Dr. Smith"


def test_page_title_to_filename_empty_title_uses_untitled() -> None:
    """Empty titles map to the stable ``untitled`` stem (LIM-002)."""
    assert page_title_to_filename("") == "untitled"
    assert page_title_to_filename("   ") == "untitled"
    assert page_title_to_relative_path("") == Path("untitled.md")


def test_encode_and_decode_page_title_segment() -> None:
    assert encode_page_title_segment("A#B") == "A%23B"
    assert decode_page_title_segment("A%23B") == "A#B"


def test_derive_page_title_from_source_path_ignores_deceptive_parent_pages_dir(
    tmp_path: Path,
) -> None:
    page_path = tmp_path / "pages" / "my_graph" / "pages" / "Idea.md"
    page_path.parent.mkdir(parents=True)
    assert derive_page_title_from_source_path(page_path) == "Idea"
    assert derive_graph_root_from_source_path(page_path) == (tmp_path / "pages" / "my_graph").resolve()


def test_derive_graph_root_from_journals_path(tmp_path: Path) -> None:
    journal_path = tmp_path / "vault" / "journals" / "2026_05_23.md"
    journal_path.parent.mkdir(parents=True)
    assert derive_graph_root_from_source_path(journal_path) == (tmp_path / "vault").resolve()


def test_derive_page_title_from_folder_namespace(tmp_path: Path) -> None:
    page_path = tmp_path / "vault" / "pages" / "Progetti" / "AI" / "Matryca.md"
    page_path.parent.mkdir(parents=True)
    assert derive_page_title_from_source_path(page_path) == "Progetti/AI/Matryca"


def test_derive_page_title_from_flat_encoded_namespace(tmp_path: Path) -> None:
    page_path = tmp_path / "vault" / "pages" / "Progetti___AI___Matryca.md"
    page_path.parent.mkdir(parents=True)
    assert derive_page_title_from_source_path(page_path) == "Progetti/AI/Matryca"


def test_derive_page_title_from_percent_encoded_segment(tmp_path: Path) -> None:
    encoded = encode_page_title_segment("What?")
    page_path = tmp_path / "vault" / "pages" / f"{encoded}.md"
    page_path.parent.mkdir(parents=True)
    assert derive_page_title_from_source_path(page_path) == "What?"


def test_page_title_to_relative_path_uses_namespace_folders() -> None:
    assert page_title_to_relative_path("Progetti/AI/Matryca") == Path("Progetti/AI/Matryca.md")
    assert page_title_to_relative_path("What?") == Path("What%3F.md")


@pytest.mark.parametrize(
    "relative",
    [
        Path("pages/logseq/bak/ghost.md"),
        Path("pages/.recycle/old.md"),
        Path("pages/.git/hooks/pre-commit.md"),
        Path("journals/logseq/bak/journal.md"),
    ],
)
def test_is_excluded_graph_path(tmp_path: Path, relative: Path) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("- ghost\n", encoding="utf-8")
    assert is_excluded_graph_path(target) is True


def test_discover_graph_files_skips_backup_and_recycle_dirs(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Real.md").write_text("- real\n", encoding="utf-8")
    (pages / "logseq" / "bak").mkdir(parents=True)
    (pages / "logseq" / "bak" / "Ghost.md").write_text("- ghost\n", encoding="utf-8")
    (pages / ".recycle").mkdir(parents=True)
    (pages / ".recycle" / "Old.md").write_text("- old\n", encoding="utf-8")

    discovered = discover_graph_files(graph_root)

    assert len(discovered) == 1
    assert discovered[0].name == "Real.md"
