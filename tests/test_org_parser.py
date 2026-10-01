"""Contract tests for the private, source-preserving Org text parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from logseq_matryca_parser import _org_parser as org
from logseq_matryca_parser._org_source import OrgSourceCode, OrgSourceFailure
from tests.org_assurance.manifest import load_corpus_manifest

ROOT = Path(__file__).parents[1]


def _text(source: str, span: org.OrgSpan) -> str:
    return source[span.start : span.end]


def _code(result: org.OrgParseResult) -> str | None:
    return result.diagnostics[0].code.value if result.diagnostics else None


def test_parse_org_text_requires_explicit_page_title() -> None:
    result = org.parse_org_text("", page_title="Page")
    assert result.document is not None
    assert result.document.page_title == "Page"
    assert result.document.elements == ()


@pytest.mark.parametrize(
    ("title", "code"),
    [
        (None, "ORG_PAGE_TITLE_REQUIRED"),
        (b"Page", "ORG_PAGE_TITLE_REQUIRED"),
        ("", "ORG_PAGE_TITLE_REQUIRED"),
        (" \t\n", "ORG_PAGE_TITLE_REQUIRED"),
        (" " * 1025, "ORG_PAGE_TITLE_TOO_LARGE"),
        ("x" * 1025, "ORG_PAGE_TITLE_TOO_LARGE"),
        ("\ud800", "ORG_INVALID_UNICODE"),
        ("x" * 1024 + "\ud800", "ORG_INVALID_UNICODE"),
        ("\ud800" + "x" * 1025, "ORG_INVALID_UNICODE"),
        ("x" * 1025 + "\ud800", "ORG_PAGE_TITLE_TOO_LARGE"),
        ("é" * 513 + "\ud800", "ORG_PAGE_TITLE_TOO_LARGE"),
    ],
)
def test_parse_org_text_validates_title(title: object, code: str) -> None:
    assert _code(org.parse_org_text("body", page_title=title)) == code


def test_parse_org_text_title_bytes_count_multibyte_without_normalization() -> None:
    accepted_title = "é" * 512
    accepted = org.parse_org_text("", page_title=accepted_title)
    rejected = org.parse_org_text("", page_title="é" * 513)
    assert accepted.document is not None
    assert accepted.document.page_title is accepted_title
    assert _code(rejected) == "ORG_PAGE_TITLE_TOO_LARGE"


def test_parse_org_title_scan_stops_at_first_utf8_byte_overflow() -> None:
    work = org._Work()
    title = "x" * 1024 + "x" * 100_000

    result = org._validate_page_title(title, work)

    assert result is not None
    assert _code(result) == "ORG_PAGE_TITLE_TOO_LARGE"
    assert work.phase_used["title"] == 4 * 1025


def test_parse_org_text_rejects_source_surrogate() -> None:
    assert _code(org.parse_org_text("x\udfff", page_title="Page")) == "ORG_INVALID_UNICODE"


def test_parse_org_text_preserves_source_offsets_and_line_spans() -> None:
    source = "\ufeff* Title\r\nbody\n\nlast"
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert result.document.source_text is source
    first, second, third = result.document.elements
    assert isinstance(first, org.OrgHeading)
    assert first.span == org.OrgSpan(0, 8, 1, 1)
    assert _text(source, first.title_span) == "Title"
    assert isinstance(second, org.OrgParagraph)
    assert second.span == org.OrgSpan(10, 14, 2, 2)
    assert isinstance(third, org.OrgParagraph)
    assert _text(source, third.span) == "last"


def test_parse_org_text_preserves_heading_and_active_list_ancestry() -> None:
    source = "* A\n- A\n  - B\n- C\n    - D\n"
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    heading, listing, orphan = result.document.elements
    assert isinstance(heading, org.OrgHeading)
    assert isinstance(listing, org.OrgList)
    assert [item.span.line_start for item in listing.items] == [2, 4]
    assert listing.items[0].child_items[0].span.line_start == 3
    assert isinstance(orphan, org.OrgParagraph)
    assert _text(source, orphan.span) == "    - D"


def test_parse_org_text_scans_links_once_and_keeps_them_unresolved() -> None:
    source = "[[Page]] [[https://example.invalid][label]] [[file:x]] [[bad"
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    paragraph = result.document.elements[0]
    assert isinstance(paragraph, org.OrgParagraph)
    assert [(link.kind, link.resolution) for link in paragraph.annotations] == [
        ("page", "unresolved"),
        ("external", "not_applicable"),
        ("file", "never"),
    ]
    assert [_text(source, link.target_span) for link in paragraph.annotations] == [
        "Page",
        "https://example.invalid",
        "file:x",
    ]


def test_parse_org_text_does_not_treat_unicode_separator_as_new_line() -> None:
    source = "first\u2028second\rlast"
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert len(result.document.elements) == 1
    assert _text(source, result.document.elements[0].span) == source


def test_parse_org_text_rejects_heading_depth_129_and_accepts_128() -> None:
    accepted = org.parse_org_text("*" * 128 + " title", page_title="Page")
    rejected = org.parse_org_text("*" * 129 + " title", page_title="Page")
    assert accepted.document is not None
    heading = accepted.document.elements[0]
    assert isinstance(heading, org.OrgHeading)
    assert heading.level == 128
    assert _code(rejected) == "ORG_NESTING_LIMIT_EXCEEDED"


def test_parse_org_text_list_depth_128_valid_129_and_orphan_129() -> None:
    chain = "".join(" " * (2 * (depth - 1)) + "- x\n" for depth in range(1, 129))
    accepted = org.parse_org_text(chain, page_title="Page")
    valid_child = org.parse_org_text(chain + " " * 256 + "- child", page_title="Page")
    orphan = org.parse_org_text(" " * 256 + "- orphan", page_title="Page")
    assert accepted.document is not None
    assert _code(valid_child) == "ORG_NESTING_LIMIT_EXCEEDED"
    assert orphan.document is not None
    assert isinstance(orphan.document.elements[0], org.OrgParagraph)


def test_parse_org_text_depth_dimensions_use_maximum_not_sum() -> None:
    source = "* Heading\n" + "".join(
        " " * (2 * (depth - 1)) + "- x\n" for depth in range(1, 129)
    )
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None


def test_parse_org_text_line_and_bom_policy() -> None:
    cases = [
        ("", 0),
        ("x\n", 1),
        ("x\r\ny", 2),
        ("x\ry", 1),
        ("\ufeff", 0),
        ("\ufeff\ufeffx", 1),
        ("\u3000", 1),
    ]
    for source, count in cases:
        result = org.parse_org_text(source, page_title="Page")
        assert result.document is not None
        assert len(result.document.elements) == count


def test_parse_org_text_counts_work_over_powers_of_two() -> None:
    for size in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512):
        source = ("[[ [[x]] #+BEGIN_ <2026-99-99 Mon> :END_\n" * size)
        counter = org._Work()
        result = org._parse_org_text(source, page_title="Page", _work=counter)
        assert result.document is not None
        source_bytes = len(source)
        elements = counter.phase_used["alloc"] // 48
        bound = 64 * (source_bytes + len(source) + len("Page") + elements + source.count("\n") + 1)
        assert counter.used <= bound
        assert counter.limit == bound


def test_parse_org_text_work_counter_aborts_before_overrun() -> None:
    source = "[[" * 80 + "x" * 256
    measured = org._Work()
    org._parse_org_text(source, page_title="Page", _work=measured)
    injected = org._Work(measured.used - 1)
    with pytest.raises(org._WorkLimitExceeded):
        org._parse_org_text(source, page_title="Page", _work=injected)
    assert injected.limit is not None
    assert injected.used <= injected.limit


def test_parse_org_text_dense_long_line_near_miss_is_bounded() -> None:
    source = ("[[x][y]] [[unterminated #+BEGIN_foo <2026-99-99 Abc>\n" * 1024)
    counter = org._Work()
    result = org._parse_org_text(source, page_title="Page", _work=counter)
    assert result.document is not None
    assert counter.limit is not None
    assert counter.used <= counter.limit


def test_parse_org_text_keeps_unknown_directives_and_blocks_inert() -> None:
    source = (
        "#+UNKNOWN: kept\n"
        "#+BEGIN_CUSTOM trailing\n"
        "#+BEGIN_SRC sh\n"
        "#+END_CUSTOM\n"
        "#+BEGIN_SRC sh\n"
        "echo inert\n"
        "#+END_SRC\n"
    )
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert isinstance(result.document.elements[0], org.OrgDirective)
    custom, source_block = result.document.elements[1:]
    assert isinstance(custom, org.OrgOpaque) and custom.kind == "other_block"
    assert _text(source, custom.span) == "#+BEGIN_CUSTOM trailing\n#+BEGIN_SRC sh\n#+END_CUSTOM"
    assert isinstance(source_block, org.OrgOpaque) and source_block.kind == "source_block"
    assert [diagnostic.line for diagnostic in result.diagnostics] == [5]


def test_parse_org_text_warns_at_each_executable_opener_only() -> None:
    source = (
        "#+BEGIN_SRC sh\n#+END_SRC\n"
        "#+BEGIN_QUERY\n#+END_QUERY\n"
        "#+BEGIN: custom\n#+END:\n"
        "#+MACRO: m inert\n"
    )
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert [diagnostic.line for diagnostic in result.diagnostics] == [1, 3, 5, 7]
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        org.OrgDiagnosticCode.OPAQUE_EXECUTABLE_SYNTAX
    }


def test_parse_org_text_preserves_malformed_timestamp_as_paragraph() -> None:
    source = "SCHEDULED: <2026-02-30 Mon>\nCLOSEDLY: ignored"
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert all(isinstance(element, org.OrgParagraph) for element in result.document.elements)


@pytest.mark.parametrize(
    "source",
    [
        "SCHEDULED <2026-01-01 Thu>",
        "SCHEDULED:<2026-01-01 Thu>",
        "DEADLINE <2026-01-01 Thu>",
        "DEADLINE:<2026-01-01 Thu>",
        "SCHEDULED: <0000-01-01 Sat>",
        "CLOSED",
        "CLOCK foo",
        "CLOSED:foo",
        "CLOCK:foo",
    ],
)
def test_parse_org_text_rejects_noncontract_timestamp_forms(source: str) -> None:
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert len(result.document.elements) == 1
    assert isinstance(result.document.elements[0], org.OrgParagraph)


def test_parse_org_text_accepts_exact_timestamp_forms() -> None:
    source = (
        "SCHEDULED:\t<2024-02-29 Thu>\n"
        "DEADLINE: <2026-01-01 Thu>\n"
        "CLOSED:\n"
        "CLOCK: ")
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert [element.kind_name for element in result.document.elements if isinstance(element, org.OrgTimestamp)] == [
        "scheduled", "deadline", "closed", "clock"
    ]
    scheduled = result.document.elements[0]
    assert isinstance(scheduled, org.OrgTimestamp)
    assert scheduled.date_value is not None and scheduled.date_value.isoformat() == "2024-02-29"


@pytest.mark.parametrize("closed", [True, False])
def test_parse_org_text_drawer_body_keeps_heading_shaped_lines_opaque(closed: bool) -> None:
    source = "* Owner\n:PROPERTIES:\n* injected\n" + (":END:\n" if closed else "")
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert [element for element in result.document.elements if isinstance(element, org.OrgHeading)] == [
        result.document.elements[0]
    ]
    assert len(result.document.elements) == 2
    drawer = result.document.elements[1]
    if closed:
        assert isinstance(drawer, org.OrgPropertyDrawer)
        assert _text(source, drawer.span) == ":PROPERTIES:\n* injected\n:END:"
    else:
        assert isinstance(drawer, org.OrgOpaque)
        assert drawer.kind == "unterminated_drawer"
        assert _code(result) == "ORG_UNCLOSED_DRAWER"


def test_parse_org_text_charges_out_of_range_lookahead() -> None:
    reads: list[int] = []
    work = org._Work()
    result = org._parse_org_text("[", page_title="Page", _work=work, _read_hook=reads.append)
    assert result.document is not None
    assert 1 in reads


def test_parse_org_text_refuses_list_freeze_before_allocation_hook() -> None:
    allocations: list[str] = []
    with pytest.raises(org._WorkLimitExceeded):
        org._parse_org_text(
            "- root\n  - child",
            page_title="Page",
            _allocation_limit=0,
            _allocation_hook=allocations.append,
        )
    assert allocations == []


def test_parse_org_text_charges_each_list_freeze_allocation_before_hook() -> None:
    allocations: list[str] = []
    result = org._parse_org_text(
        "- root\n  - child",
        page_title="Page",
        _allocation_hook=allocations.append,
    )
    assert result.document is not None
    assert {
        "list_stack", "list_stack_entry", "list_frozen_map", "list_child_values",
        "list_child_value_slot", "list_child_tuple_slots", "list_frozen_record",
        "list_frozen_map_entry", "list_root_values", "list_root_value_slot",
        "list_root_tuple_slots", "list_element_record", "list_element_append",
    } <= set(allocations)


def test_parse_org_text_refuses_diagnostic_before_allocation_hook() -> None:
    allocations: list[str] = []
    with pytest.raises(org._WorkLimitExceeded):
        org._parse_org_text(
            "#+MACRO: m inert",
            page_title="Page",
            _allocation_limit=0,
            _allocation_hook=allocations.append,
        )
    assert allocations == []


def test_parse_org_text_charges_diagnostic_record_and_tuple_before_hook() -> None:
    allocations: list[str] = []
    result = org._parse_org_text(
        "#+MACRO: m inert",
        page_title="Page",
        _allocation_hook=allocations.append,
    )
    assert result.document is not None
    assert allocations.count("diagnostic") == 1
    assert allocations.count("diagnostic_tuple_slots") == 1


def test_parse_org_text_line_overflow_charges_fixed_diagnostic_before_allocation() -> None:
    source = "\n" * 250_001
    ordinary = org.parse_org_text(source, page_title="P")
    assert _code(ordinary) == "ORG_LINE_LIMIT_EXCEEDED"

    allocations: list[str] = []
    with pytest.raises(org._WorkLimitExceeded):
        org._parse_org_text(
            source,
            page_title="P",
            _allocation_limit=0,
            _allocation_hook=allocations.append,
        )
    assert allocations == []


def test_parse_org_text_invalid_title_charges_fixed_diagnostic_before_allocation() -> None:
    allocations: list[str] = []
    with pytest.raises(org._WorkLimitExceeded):
        org._parse_org_text(
            "",
            page_title=None,
            _allocation_limit=0,
            _allocation_hook=allocations.append,
        )
    assert allocations == []


def test_parse_org_file_validates_title_before_reader_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def reader(path: object) -> bytes:
        calls.append(path)
        raise AssertionError("reader called before title validation")

    monkeypatch.setattr(org, "read_org_source", reader, raising=False)
    cases = [
        (None, "ORG_PAGE_TITLE_REQUIRED"),
        (b"Page", "ORG_PAGE_TITLE_REQUIRED"),
        ("x" * 1024 + "\ud800", "ORG_INVALID_UNICODE"),
        (" " * 1025, "ORG_PAGE_TITLE_TOO_LARGE"),
        ("x" * 1025 + "\ud800", "ORG_PAGE_TITLE_TOO_LARGE"),
        ("", "ORG_PAGE_TITLE_REQUIRED"),
    ]
    for title, code in cases:
        result = org.parse_org_file("relative/bad.txt", page_title=title)
        assert _code(result) == code
    assert org.parse_org_file("relative/bad.txt").diagnostics[0].code.value == "ORG_PAGE_TITLE_REQUIRED"
    assert calls == []


@pytest.mark.parametrize(
    ("source_code", "diagnostic_code"),
    [
        (OrgSourceCode.PATH_INVALID, "ORG_FILE_PATH_INVALID"),
        (OrgSourceCode.SOURCE_UNSUPPORTED, "ORG_FILE_SOURCE_UNSUPPORTED"),
        (OrgSourceCode.SOURCE_REJECTED, "ORG_FILE_SOURCE_REJECTED"),
        (OrgSourceCode.READ_FAILED, "ORG_FILE_READ_FAILED"),
        (OrgSourceCode.SOURCE_TOO_LARGE, "ORG_SOURCE_TOO_LARGE"),
    ],
)
def test_parse_org_file_maps_source_failures_without_path_detail(
    monkeypatch: pytest.MonkeyPatch,
    source_code: OrgSourceCode,
    diagnostic_code: str,
) -> None:
    secret_path = "/private/example-do-not-report.org"
    monkeypatch.setattr(org, "read_org_source", lambda path: OrgSourceFailure(source_code), raising=False)
    result = org.parse_org_file(secret_path, page_title="Page")
    assert result.document is None
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code.value == diagnostic_code
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].line is None
    assert secret_path not in repr(result)


def test_parse_org_file_enforces_actual_byte_cap_before_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    decode_calls: list[bool] = []

    class DecodeProbe(bytes):
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            decode_calls.append(True)
            return super().decode(encoding, errors)

    oversized = DecodeProbe(b"x" * 8_388_609)
    monkeypatch.setattr(org, "read_org_source", lambda path: oversized, raising=False)
    result = org.parse_org_file("/private/oversized.org", page_title="Page")
    assert _code(result) == "ORG_SOURCE_TOO_LARGE"
    assert decode_calls == []


def test_parse_org_file_maps_strict_utf8_failure_without_path(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_path = "/private/invalid-utf8.org"
    monkeypatch.setattr(org, "read_org_source", lambda path: b"\xff", raising=False)
    result = org.parse_org_file(secret_path, page_title="Page")
    assert result.document is None
    assert _code(result) == "ORG_INVALID_UTF8"
    assert secret_path not in repr(result)


def test_parse_org_file_matches_text_results_for_all_fixtures() -> None:
    cases = load_corpus_manifest(ROOT)
    assert len(cases) == 6
    for case in cases:
        source = case.source_path.read_bytes().decode("utf-8", errors="strict")
        file_result = org.parse_org_file(case.source_path.absolute(), page_title=case.page_title)
        text_result = org.parse_org_text(source, page_title=case.page_title)
        assert file_result == text_result, case.id
        assert file_result.document is not None, case.id
        assert str(case.source_path) not in repr(file_result), case.id
        exact = json.loads((ROOT / case.exact_expectation).read_text())
        semantic = json.loads((ROOT / case.semantic_expectation).read_text())
        assert _exact_projection(file_result.document) == exact, case.id
        assert _semantic_projection(file_result) == semantic, case.id


@pytest.mark.parametrize("kind", ["tags", "list", "properties", "links", "mixed"])
def test_parse_org_text_shared_node_budget_rejects_before_100001_allocation(kind: str) -> None:
    def source_for(count: int) -> tuple[str, int]:
        if kind == "tags":
            tags = ":".join("t" for _ in range(count - 1))
            return f"* H :{tags}:\n", count
        if kind == "list":
            item_count = count - 1
            pairs = item_count // 2
            source = "- root\n  - child\n" * pairs
            if item_count % 2:
                source += "- final\n"
            return source, count
        if kind == "properties":
            return "* H\n:PROPERTIES:\n" + ":P: v\n" * (count - 2), count - 2
        if kind == "links":
            return " ".join("[[x]]" for _ in range(count - 1)), count - 1
        pairs = (count + 1) // 2
        return "* H\nx\n" * pairs, count

    exact_source, exact_occurrences = source_for(100_000)
    accepted_nodes: list[int] = []
    accepted = org._parse_org_text(
        exact_source, page_title="Page", _node_hook=accepted_nodes.append
    )
    assert accepted.document is not None
    assert accepted_nodes[-1] == 100_000
    assert len(accepted_nodes) == 100_000
    assert exact_occurrences >= 99_998

    overflow_source, _ = source_for(100_001)
    attempted_nodes: list[int] = []
    rejected = org._parse_org_text(
        overflow_source, page_title="Page", _node_hook=attempted_nodes.append
    )
    assert rejected.document is None
    assert _code(rejected) == "ORG_ELEMENT_LIMIT_EXCEEDED"
    assert len(attempted_nodes) == 100_000
    assert attempted_nodes[-1] == 100_000


def test_parse_org_text_unclosed_drawer_still_charges_property_entries() -> None:
    source = "* H\n:PROPERTIES:\n" + ":P: v\n" * 10 + "body\n"
    result = org.parse_org_text(source, page_title="Page")
    assert result.document is not None
    assert result.diagnostics[0].code == org.OrgDiagnosticCode.UNCLOSED_DRAWER
    final_element = result.document.elements[-1]
    assert isinstance(final_element, org.OrgOpaque)
    assert final_element.kind == "unterminated_drawer"


@pytest.mark.parametrize("warning_count", [255, 256])
def test_parse_org_text_diagnostic_limit_includes_truncation_marker(warning_count: int) -> None:
    source = "#+MACRO: m x\n" * warning_count
    result = org.parse_org_text(source, page_title="Page")
    if warning_count == 255:
        assert result.document is not None
        assert len(result.diagnostics) == 255
        assert result.diagnostics[-1].code == org.OrgDiagnosticCode.OPAQUE_EXECUTABLE_SYNTAX
    else:
        assert result.document is None
        assert len(result.diagnostics) == 256
        assert result.diagnostics[-1].code == org.OrgDiagnosticCode.DIAGNOSTICS_TRUNCATED


def test_parse_org_text_source_byte_limit_inclusive() -> None:
    below = org.parse_org_text("x" * 8_388_607, page_title="Page")
    exact = org.parse_org_text("x" * 8_388_608, page_title="Page")
    too_large = org.parse_org_text("x" * 8_388_609, page_title="Page")
    assert below.document is not None
    assert exact.document is not None
    assert _code(too_large) == "ORG_SOURCE_TOO_LARGE"


def test_parse_org_text_logical_line_limit_inclusive() -> None:
    below = org.parse_org_text("\n" * 249_999, page_title="Page")
    exact = org.parse_org_text("\n" * 250_000, page_title="Page")
    too_many = org.parse_org_text("\n" * 250_001, page_title="Page")
    assert below.document is not None
    assert exact.document is not None
    assert _code(too_many) == "ORG_LINE_LIMIT_EXCEEDED"


def test_parse_org_text_has_no_filesystem_or_process_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("side effect attempted")

    monkeypatch.setattr("builtins.open", denied)
    monkeypatch.setattr("subprocess.Popen", denied)
    monkeypatch.setattr("os.system", denied)
    monkeypatch.setattr("socket.create_connection", denied)
    source = "[[file:missing]]\n#+BEGIN_SRC sh\necho inert\n#+END_SRC"
    assert org.parse_org_text(source, page_title="Page").document is not None


def test_parse_org_text_calls_are_state_isolated() -> None:
    first = org.parse_org_text("* First\n#+MACRO: m x", page_title="One")
    second = org.parse_org_text("plain", page_title="Two")
    assert first.document is not None and second.document is not None
    assert second.document.page_title == "Two"
    assert len(second.document.elements) == 1
    assert second.diagnostics == ()


def test_parse_org_text_matches_exact_fixture_element_projections() -> None:
    cases = load_corpus_manifest(ROOT)
    assert len(cases) == 6
    for case in cases:
        source = case.source_path.read_text(encoding="utf-8")
        expected = json.loads((ROOT / case.exact_expectation).read_text())
        result = org.parse_org_text(source, page_title=case.page_title)
        assert result.document is not None, case.id
        actual = _exact_projection(result.document)
        assert actual == expected, case.id


def _exact_projection(document: org.OrgDocument) -> dict[str, object]:
    source = document.source_text

    def element(value: org.OrgElement) -> dict[str, object]:
        base: dict[str, object] = {"line_start": value.span.line_start, "line_end": value.span.line_end}
        if isinstance(value, org.OrgHeading):
            marker = _text(source, value.marker_span) if value.marker_span else None
            base.update(
                kind="heading", level=value.level, title=_text(source, value.title_span),
                marker=marker, priority=value.priority,
                tags=[_text(source, tag) for tag in value.tag_spans],
            )
        elif isinstance(value, org.OrgParagraph):
            base.update(kind="paragraph", text=_text(source, value.span))
        elif isinstance(value, org.OrgList):
            def item(row: org.OrgListItem) -> dict[str, object]:
                line = source[row.span.start : row.span.end]
                marker = line.find("- ")
                return {
                    "text": line[marker + 2 :].strip(" \t"),
                    "items": [item(child) for child in row.child_items],
                }
            base.update(kind="list", ordered=value.ordered, items=[item(row) for row in value.items])
        elif isinstance(value, org.OrgDirective):
            base.update(kind="directive", name=_text(source, value.name_span), value=_text(source, value.value_span))
        elif isinstance(value, org.OrgPropertyDrawer):
            base.update(
                kind="property_drawer",
                properties=[[_text(source, p.key_span), _text(source, p.value_span)] for p in value.properties],
            )
        elif isinstance(value, org.OrgTimestamp):
            base.update(
                kind="timestamp",
                kind_name={"scheduled": "SCHEDULED", "deadline": "DEADLINE", "closed": "CLOSED", "clock": "CLOCK"}[value.kind_name],
                raw=_text(source, value.raw_span),
            )
        elif isinstance(value, org.OrgOpaque):
            if value.kind == "unterminated_drawer":
                base.update(kind="opaque_unterminated", element="property_drawer", raw=_text(source, value.span))
            else:
                name = {
                    "source_block": "source_block", "query_block": "query_block",
                    "dynamic_block": "dynamic_block", "macro_directive": "macro_directive",
                }.get(value.kind, value.kind)
                base.update(kind=name)
                if value.kind == "source_block":
                    newline = source.find("\n", value.span.start, value.span.end)
                    opener = source[value.span.start : newline if newline >= 0 else value.span.end]
                    tail = opener[len("#+BEGIN_SRC") :].strip(" \t")
                    base["language"] = tail.split(None, 1)[0] if tail else None
                if value.kind == "dynamic_block":
                    opener = source[value.span.start : value.span.end].splitlines()[0]
                    base["name"] = opener[len("#+BEGIN:") :].strip(" \t")
                if value.kind == "macro_directive":
                    line = source[value.span.start : value.span.end]
                    base["name"] = line[len("#+MACRO:") :].split(None, 1)[0]
        return base

    return {
        "schema_version": 1,
        "source_text": source,
        "elements": [element(row) for row in document.elements],
    }


def test_parse_org_text_matches_semantic_fixture_projections() -> None:
    cases = load_corpus_manifest(ROOT)
    assert len(cases) == 6
    for case in cases:
        source = case.source_path.read_text(encoding="utf-8")
        expected = json.loads((ROOT / case.semantic_expectation).read_text())
        result = org.parse_org_text(source, page_title=case.page_title)
        assert result.document is not None, case.id
        assert _semantic_projection(result) == expected, case.id


def _semantic_projection(result: org.OrgParseResult) -> dict[str, object]:
    assert result.document is not None
    document = result.document
    source = document.source_text
    blocks: list[dict[str, object]] = []
    properties: list[dict[str, object]] = []
    references: list[dict[str, object]] = []
    timestamps: list[dict[str, object]] = []
    opaque: list[dict[str, object]] = []
    heading_stack: list[tuple[int, int]] = []
    ordinal = 0
    first_heading_seen = False
    for value in document.elements:
        if isinstance(value, org.OrgHeading):
            first_heading_seen = True
            while heading_stack and heading_stack[-1][0] >= value.level:
                heading_stack.pop()
            parent = heading_stack[-1][1] if heading_stack else None
            tags = [_text(source, tag) for tag in value.tag_spans]
            blocks.append(
                {
                    "ordinal": ordinal,
                    "title": _text(source, value.title_span),
                    "marker": _text(source, value.marker_span) if value.marker_span else None,
                    "priority": value.priority,
                    "tags": tags,
                    "parent_ordinal": parent,
                    "line_start": value.span.line_start,
                }
            )
            heading_stack.append((value.level, ordinal))
            ordinal += 1
        elif isinstance(value, org.OrgDirective) and not first_heading_seen:
            name = _text(source, value.name_span)
            if name == "TITLE" or name == "FILETAGS":
                properties.append({"scope": "document", "name": name, "value": _text(source, value.value_span)})
        elif isinstance(value, org.OrgPropertyDrawer):
            for prop in value.properties:
                properties.append(
                    {
                        "scope": f"heading:{value.owner_heading_ordinal}",
                        "name": _text(source, prop.key_span),
                        "value": _text(source, prop.value_span),
                    }
                )
        elif isinstance(value, org.OrgParagraph):
            for ref in value.annotations:
                target = _text(source, ref.target_span)
                if ref.kind == "page":
                    references.append({"kind": "page", "target": target, "resolution": "unresolved"})
                else:
                    opaque.append(
                        {
                            "kind": "file_link" if ref.kind == "file" else "external_link",
                            "line_start": ref.span.line_start,
                            **({"resolution": "never"} if ref.kind == "file" else {}),
                        }
                    )
        elif isinstance(value, org.OrgTimestamp):
            if value.kind_name in {"scheduled", "deadline"}:
                timestamps.append(
                    {
                        "kind": value.kind_name,
                        "date": value.date_value.isoformat() if value.date_value else None,
                        "raw": _text(source, value.raw_span),
                    }
                )
            else:
                opaque.append(
                    {
                        "kind": "closed_timestamp" if value.kind_name == "closed" else "clock_timestamp",
                        "line_start": value.span.line_start,
                    }
                )
        elif isinstance(value, org.OrgList):
            opaque.append({"kind": "list", "line_start": value.span.line_start, "line_end": value.span.line_end})
        elif isinstance(value, org.OrgOpaque):
            names = {
                "source_block": "source_block",
                "query_block": "query_block",
                "dynamic_block": "dynamic_block",
            }
            if value.kind in names:
                opaque.append(
                    {"kind": names[value.kind], "line_start": value.span.line_start, "line_end": value.span.line_end}
                )
            elif value.kind == "unterminated_drawer":
                opaque.append(
                    {
                        "kind": "unterminated_property_drawer",
                        "line_start": value.span.line_start,
                        "line_end": value.span.line_end,
                    }
                )
            elif value.kind == "macro_directive":
                opaque.append(
                    {
                        "kind": "macro_directive_and_expansion",
                        "line_start": value.span.line_start,
                        "line_end": value.span.line_end + 1,
                    }
                )
    return {
        "schema_version": 1,
        "page_title": document.page_title,
        "blocks": blocks,
        "page_properties": properties,
        "references": references,
        "timestamps": timestamps,
        "opaque": opaque,
        "diagnostics": [
            {"code": d.code.value, "severity": d.severity, **({"line": d.line} if d.line is not None else {})}
            for d in result.diagnostics
        ],
    }
