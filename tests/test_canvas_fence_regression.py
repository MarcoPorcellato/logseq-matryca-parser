"""Public parser regressions for fenced code in serialized list items."""

from __future__ import annotations

import pytest

from logseq_matryca_parser import LogosParser, LogseqNode, LogseqPage, serialize_logseq_page

_CODE_UUID = "11111111-1111-1111-1111-111111111111"
_FOLLOWING_UUID = "22222222-2222-2222-2222-222222222222"
_LITERAL_UUID = "33333333-3333-3333-3333-333333333333"


def _source_node(block_uuid: str, content: str) -> LogseqNode:
    return LogseqNode(
        uuid=block_uuid,
        source_uuid=block_uuid,
        synthetic_id=False,
        content=content,
        indent_level=0,
        properties={"id": block_uuid},
        properties_order=["id"],
    )


def _unidentified_node(content: str) -> LogseqNode:
    return LogseqNode(
        uuid="source-has-no-id-property",
        content=content,
        indent_level=0,
        synthetic_id=True,
    )


def _serialized_page(*nodes: LogseqNode) -> str:
    page = LogseqPage(title="fenced-code-regression", raw_content="", root_nodes=list(nodes))
    return serialize_logseq_page(page, tab_size=2)


def test_serialized_fence_node_keeps_following_paragraph_identity_and_source_order() -> None:
    markdown = _serialized_page(
        _source_node(_CODE_UUID, '```python\nprint("inside code")\n```'),
        _source_node(_FOLLOWING_UUID, "following paragraph"),
    )

    page = LogosParser(tab_size=2).parse(markdown, page_title="fenced-code-regression")

    assert page.raw_content == markdown
    assert len(page.root_nodes) == 2
    code, following = page.root_nodes
    assert [node.source_uuid for node in page.root_nodes] == [_CODE_UUID, _FOLLOWING_UUID]
    assert code.properties == {"id": _CODE_UUID}
    assert code.content == '```python\n  print("inside code")\n  ```'
    assert following.content == "following paragraph"
    assert [(node.line_start, node.line_end) for node in page.root_nodes] == [(1, 4), (5, 6)]


def test_serialized_fence_keeps_literal_id_and_fake_bullet_inside_code() -> None:
    code_content = f"```python\nid:: {_LITERAL_UUID}\n- fake bullet\nprint('still code')\n```"
    markdown = _serialized_page(
        _source_node(_CODE_UUID, code_content),
        _source_node(_FOLLOWING_UUID, "following paragraph"),
    )

    page = LogosParser(tab_size=2).parse(markdown, page_title="fenced-code-regression")

    assert len(page.root_nodes) == 2
    code, following = page.root_nodes
    assert code.source_uuid == _CODE_UUID
    assert code.properties == {"id": _CODE_UUID}
    assert code.children == []
    assert f"  id:: {_LITERAL_UUID}" in code.content
    assert "  - fake bullet" in code.content
    assert all(node.source_uuid != _LITERAL_UUID for node in page.root_nodes)
    assert following.source_uuid == _FOLLOWING_UUID
    assert following.content == "following paragraph"


@pytest.mark.parametrize(
    ("fence_char", "fence_width"),
    [("`", 3), ("~", 3), ("`", 4), ("~", 4)],
)
def test_serialized_fence_character_and_opener_width_preserve_following_node(
    fence_char: str,
    fence_width: int,
) -> None:
    fence = fence_char * fence_width
    markdown = _serialized_page(
        _source_node(_CODE_UUID, f"{fence}python\nprint('inside')\n{fence}"),
        _source_node(_FOLLOWING_UUID, "following paragraph"),
    )

    page = LogosParser(tab_size=2).parse(markdown, page_title="fenced-code-regression")

    assert [node.source_uuid for node in page.root_nodes] == [_CODE_UUID, _FOLLOWING_UUID]
    code, following = page.root_nodes
    assert code.content == f"{fence}python\n  print('inside')\n  {fence}"
    assert code.properties == {"id": _CODE_UUID}
    assert following.content == "following paragraph"


def test_serialized_four_tick_fence_ignores_wrong_short_and_trailing_text_closers() -> None:
    code_content = (
        "````python\n"
        "~~~~\n"
        "```\n"
        "```` trailing text\n"
        f"id:: {_LITERAL_UUID}\n"
        "SCHEDULED: <2026-10-20 Tue>\n"
        "- fake bullet\n"
        "print('still fenced')\n"
        "`````"
    )
    markdown = _serialized_page(
        _source_node(_CODE_UUID, code_content),
        _source_node(_FOLLOWING_UUID, "following paragraph"),
    )

    page = LogosParser(tab_size=2).parse(markdown, page_title="fenced-code-regression")

    assert len(page.root_nodes) == 2
    code, following = page.root_nodes
    assert code.source_uuid == _CODE_UUID
    assert code.properties == {"id": _CODE_UUID}
    assert code.children == []
    assert "  ~~~~" in code.content
    assert "  ```\n" in code.content
    assert "  ```` trailing text" in code.content
    assert f"  id:: {_LITERAL_UUID}" in code.content
    assert "  - fake bullet" in code.content
    assert code.scheduled_at is None
    assert f"id:: {_LITERAL_UUID}" in code.clean_text
    assert "SCHEDULED: <2026-10-20 Tue>" in code.clean_text
    assert following.source_uuid == _FOLLOWING_UUID
    assert following.content == "following paragraph"


@pytest.mark.parametrize(
    ("fence_char", "fence_width"),
    [("`", 3), ("~", 3), ("`", 4), ("~", 4)],
)
def test_unclosed_serialized_fence_protects_following_lines_through_eof(
    fence_char: str,
    fence_width: int,
) -> None:
    fence = fence_char * fence_width
    markdown = _serialized_page(
        _unidentified_node(
            f"{fence}python\nid:: {_LITERAL_UUID}\n- fake bullet\nprint('last code line')"
        ),
        _source_node(_FOLLOWING_UUID, "following paragraph"),
    )

    page = LogosParser(tab_size=2).parse(markdown, page_title="unclosed-fence-regression")

    assert page.raw_content == markdown
    assert len(page.root_nodes) == 1
    code = page.root_nodes[0]
    assert code.source_uuid is None
    assert code.properties == {}
    assert code.children == []
    assert f"  id:: {_LITERAL_UUID}" in code.content
    assert "  - fake bullet" in code.content
    assert "- following paragraph" in code.content
    assert f"  id:: {_FOLLOWING_UUID}" in code.content
    assert code.line_start == 1
    assert code.line_end == len(markdown.splitlines())


def test_nested_tab_indented_code_item_keeps_child_order_and_line_ranges() -> None:
    literal_uuid = "44444444-4444-4444-4444-444444444444"
    child_uuid = "55555555-5555-5555-5555-555555555555"
    after_uuid = "66666666-6666-6666-6666-666666666666"
    markdown = (
        "- Parent\n"
        "\t- ````python\n"
        f"\t\tid:: {literal_uuid}\n"
        "\t\t- fake bullet\n"
        "\t\t````\n"
        f"\t\tid:: {child_uuid}\n"
        "\t- After code\n"
        f"\t\tid:: {after_uuid}\n"
    )

    page = LogosParser(tab_size=2).parse(markdown, page_title="nested-fence-regression")

    assert page.raw_content == markdown
    assert len(page.root_nodes) == 1
    parent = page.root_nodes[0]
    assert parent.content == "Parent"
    assert len(parent.children) == 2
    code, after = parent.children
    assert code.source_uuid == child_uuid
    assert code.properties == {"id": child_uuid}
    assert code.children == []
    assert f"\t\tid:: {literal_uuid}" in code.content
    assert "\t\t- fake bullet" in code.content
    assert after.source_uuid == after_uuid
    assert after.content == "After code"
    assert [(node.line_start, node.line_end) for node in parent.children] == [(2, 6), (7, 8)]


def test_code_keeps_blank_lines_and_crlf_source_and_parser_can_be_reused() -> None:
    markdown = (
        "- ```python\r\n"
        "  first\r\n"
        "\r\n"
        "  second\r\n"
        "  ```\r\n"
        f"  id:: {_CODE_UUID}\r\n"
        f"- Following\r\n  id:: {_FOLLOWING_UUID}\r\n"
    )
    parser = LogosParser(tab_size=2)
    page = parser.parse(markdown, page_title="crlf-fence")
    assert page.raw_content == markdown
    assert len(page.root_nodes) == 2
    assert page.root_nodes[0].content == "```python\n  first\n\n  second\n  ```"
    assert [node.source_uuid for node in page.root_nodes] == [_CODE_UUID, _FOLLOWING_UUID]
    parser.parse("- ```python\n  unclosed", page_title="unclosed")
    clean = parser.parse("- plain\n- next\n", page_title="clean")
    assert [node.content for node in clean.root_nodes] == ["plain", "next"]


def test_backtick_inside_opening_info_does_not_enter_fenced_mode() -> None:
    markdown = f"- ```bad`info\n- Following\n  id:: {_FOLLOWING_UUID}\n"
    page = LogosParser(tab_size=2).parse(markdown, page_title="invalid-fence-info")
    assert len(page.root_nodes) == 2
    assert page.root_nodes[0].content == "```bad`info"
    assert page.root_nodes[1].source_uuid == _FOLLOWING_UUID


def test_real_schedule_after_closure_is_not_suppressed_with_code_schedule() -> None:
    markdown = _serialized_page(
        _source_node(_CODE_UUID, "````python\n~~~\nSCHEDULED: <2026-10-20 Tue>\n````"),
        _source_node(_FOLLOWING_UUID, "Following SCHEDULED: <2026-10-21 Wed>"),
    )
    page = LogosParser(tab_size=2).parse(markdown, page_title="schedule-after-code")
    assert len(page.root_nodes) == 2
    code, following = page.root_nodes
    assert code.scheduled_at is None
    assert following.scheduled_at is not None
    assert following.source_uuid == _FOLLOWING_UUID
