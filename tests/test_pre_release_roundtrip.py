"""Regression tests from pre-release stress harness (parse → serialize → parse)."""

from __future__ import annotations

from logseq_matryca_parser.logos_parser import StackMachineParser
from logseq_matryca_parser.logseq_markdown import serialize_logseq_page


def _roundtrip(page_title: str, source: str):
    parser = StackMachineParser()
    first = parser.parse(source, page_title=page_title)
    rendered = serialize_logseq_page(first)
    second = parser.parse(rendered, page_title=first.title)
    return first, rendered, second


def test_soft_break_roundtrip_preserves_content_not_properties() -> None:
    source = "- block\n  soft line\n  later:: not-a-prop\n"
    first, _, second = _roundtrip("soft-break", source)
    root = second.root_nodes[0]
    assert "later:: not-a-prop" in root.content
    assert "later" not in root.properties


def test_list_property_block_roundtrip_uses_bullet_layout() -> None:
    source = "- root\n  tags::\n    - one\n    - two\n"
    _, rendered, second = _roundtrip("list-prop", source)
    assert "tags:: ['one'" not in rendered
    assert "  tags::\n    - one\n    - two\n" in rendered
    assert second.root_nodes[0].properties["tags"] == ["one", "two"]


def test_logbook_drawer_roundtrip() -> None:
    source = (
        "- A\n"
        "  :LOGBOOK:\n"
        "  CLOCK: [2026-01-01 Wed 10:00]--[2026-01-01 Wed 10:30]\n"
        "  :END:\n"
        "  - B\n"
    )
    _, rendered, second = _roundtrip("logbook", source)
    assert "logbook::" not in rendered
    assert ":LOGBOOK:" in rendered
    assert second.root_nodes[0].children[0].content == "B"


def test_yaml_frontmatter_title_overrides_page_title() -> None:
    source = "---\ntitle: Y\n---\n\n- bullet\n"
    parser = StackMachineParser()
    page = parser.parse(source, page_title="untitled")
    assert page.title == "Y"


def test_yaml_frontmatter_roundtrip_preserves_block_uuid() -> None:
    source = "---\ntitle: Y\n---\n\n- bullet\n"
    parser = StackMachineParser()
    first = parser.parse(source, page_title="untitled")
    uuid_first = first.root_nodes[0].uuid
    second = parser.parse(serialize_logseq_page(first), page_title=first.title)
    assert second.title == "Y"
    assert second.root_nodes[0].uuid == uuid_first
    assert serialize_logseq_page(first).startswith("---\ntitle: Y\n---")


def test_native_title_frontmatter_roundtrip_preserves_block_uuid() -> None:
    source = "title:: Y\n\n- bullet\n"
    parser = StackMachineParser()
    first = parser.parse(source, page_title="untitled")
    assert first.title == "Y"
    uuid_first = first.root_nodes[0].uuid
    second = parser.parse(serialize_logseq_page(first), page_title=first.title)
    assert second.root_nodes[0].uuid == uuid_first


def test_derived_scheduled_properties_are_not_serialized() -> None:
    source = "- TODO x SCHEDULED: <2022-01-08 Sat.+2d>\n  :LOGBOOK:\n  :END:\n"
    _, rendered, _ = _roundtrip("scheduled", source)
    assert "scheduled::" not in rendered
    assert "repeater::" not in rendered
