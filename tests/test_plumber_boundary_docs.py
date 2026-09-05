"""Regression coverage for the Parser-to-Plumber architectural boundary."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "decisions" / "ADR-0004-PARSER-PLUMBER-BOUNDARY.md"


def test_parser_plumber_boundary_adr_is_maintained_and_explicit() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "Logseq OG -> Parser -> Plumber -> Trama/Brain" in text
    assert "The Parser runtime must not import Plumber, Trama, or Brain." in text
    assert "LENS remains compatible in this slice" in text

    maintained = (ROOT / "docs" / "maintained.toml").read_text(encoding="utf-8")
    assert '"docs/decisions/ADR-0004-PARSER-PLUMBER-BOUNDARY.md"' in maintained


def test_parser_authority_docs_preserve_parser_only_ownership() -> None:
    clean_architecture = (ROOT / "docs" / "CLEAN_CODE_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "Parser owns deterministic OG parsing" in clean_architecture
    assert "Trama owns future product-intelligence visualization" in architecture


def test_active_navigation_does_not_assign_a_parser_gui_or_gateway_role() -> None:
    starter_scope = (ROOT / "docs" / "GOOD_FIRST_ISSUES.md").read_text(encoding="utf-8")
    references = (ROOT / "docs" / "reference" / "index.md").read_text(encoding="utf-8")

    assert "Desktop GUI ([#3]" not in starter_scope
    assert "Trama graph-intelligence UI" in starter_scope
    assert "not a cross-product gateway" in references
