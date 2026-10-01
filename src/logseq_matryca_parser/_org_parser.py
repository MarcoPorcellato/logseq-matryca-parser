"""Private source-preserving reader for the bounded Logseq Org subset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

from ._org_source import OrgSourceCode, OrgSourceFailure, read_org_source

_MISSING = object()


class OrgDiagnosticCode(StrEnum):
    OPAQUE_EXECUTABLE_SYNTAX = "ORG_OPAQUE_EXECUTABLE_SYNTAX"
    UNCLOSED_DRAWER = "ORG_UNCLOSED_DRAWER"
    PAGE_TITLE_REQUIRED = "ORG_PAGE_TITLE_REQUIRED"
    PAGE_TITLE_TOO_LARGE = "ORG_PAGE_TITLE_TOO_LARGE"
    INVALID_UNICODE = "ORG_INVALID_UNICODE"
    SOURCE_TOO_LARGE = "ORG_SOURCE_TOO_LARGE"
    INVALID_UTF8 = "ORG_INVALID_UTF8"
    LINE_LIMIT_EXCEEDED = "ORG_LINE_LIMIT_EXCEEDED"
    ELEMENT_LIMIT_EXCEEDED = "ORG_ELEMENT_LIMIT_EXCEEDED"
    NESTING_LIMIT_EXCEEDED = "ORG_NESTING_LIMIT_EXCEEDED"
    DIAGNOSTICS_TRUNCATED = "ORG_DIAGNOSTICS_TRUNCATED"
    FILE_PATH_INVALID = "ORG_FILE_PATH_INVALID"
    FILE_SOURCE_UNSUPPORTED = "ORG_FILE_SOURCE_UNSUPPORTED"
    FILE_SOURCE_REJECTED = "ORG_FILE_SOURCE_REJECTED"
    FILE_READ_FAILED = "ORG_FILE_READ_FAILED"


@dataclass(frozen=True, slots=True)
class OrgSpan:
    start: int
    end: int
    line_start: int
    line_end: int


@dataclass(frozen=True, slots=True)
class OrgDiagnostic:
    code: OrgDiagnosticCode
    severity: Literal["warning", "error"]
    line: int | None = None


@dataclass(frozen=True, slots=True)
class OrgHeading:
    span: OrgSpan
    title_span: OrgSpan
    level: int
    marker_span: OrgSpan | None
    priority: str | None
    tag_spans: tuple[OrgSpan, ...]


@dataclass(frozen=True, slots=True)
class OrgReference:
    span: OrgSpan
    kind: Literal["page", "external", "file"]
    target_span: OrgSpan
    resolution: Literal["unresolved", "never", "not_applicable"]


@dataclass(frozen=True, slots=True)
class OrgParagraph:
    span: OrgSpan
    annotations: tuple[OrgReference, ...]


@dataclass(frozen=True, slots=True)
class OrgListItem:
    span: OrgSpan
    child_items: tuple[OrgListItem, ...]


@dataclass(frozen=True, slots=True)
class OrgList:
    span: OrgSpan
    ordered: bool
    items: tuple[OrgListItem, ...]


@dataclass(frozen=True, slots=True)
class OrgDirective:
    span: OrgSpan
    name_span: OrgSpan
    value_span: OrgSpan


@dataclass(frozen=True, slots=True)
class OrgProperty:
    key_span: OrgSpan
    value_span: OrgSpan


@dataclass(frozen=True, slots=True)
class OrgPropertyDrawer:
    span: OrgSpan
    properties: tuple[OrgProperty, ...]
    owner_heading_ordinal: int | None


@dataclass(frozen=True, slots=True)
class OrgTimestamp:
    span: OrgSpan
    raw_span: OrgSpan
    kind_name: Literal["scheduled", "deadline", "closed", "clock"]
    date_value: date | None


@dataclass(frozen=True, slots=True)
class OrgOpaque:
    span: OrgSpan
    kind: Literal[
        "source_block", "query_block", "dynamic_block", "other_block",
        "macro_directive", "unowned_property_drawer", "unterminated_drawer",
    ]


OrgElement = (
    OrgHeading | OrgParagraph | OrgList | OrgDirective | OrgTimestamp
    | OrgPropertyDrawer | OrgOpaque
)


@dataclass(frozen=True, slots=True)
class OrgDocument:
    page_title: str
    source_text: str
    elements: tuple[OrgElement, ...]


@dataclass(frozen=True, slots=True)
class OrgParseResult:
    document: OrgDocument | None
    diagnostics: tuple[OrgDiagnostic, ...]


_MAX_SOURCE_BYTES = 8_388_608
_MAX_TITLE_BYTES = 1_024
_MAX_LINES = 250_000
_MAX_ELEMENTS = 100_000
_MAX_DEPTH = 128
_MAX_DIAGNOSTICS = 256


class _Rejected(Exception):
    def __init__(self, code: OrgDiagnosticCode) -> None:
        self.code = code


class _WorkLimitExceeded(Exception):
    """Private test-injection failure; never part of the parse result API."""


class _Work:
    __slots__ = (
        "limit", "used", "phase_limits", "phase_used", "injected",
        "alloc_remaining", "alloc_limit", "alloc_used", "allocation_hook",
        "fixed_remaining", "fixed_precharged", "read_hook",
    )

    def __init__(
        self,
        limit: int | None = None,
        *,
        allocation_limit: int | None = None,
        allocation_hook: object = None,
        read_hook: object = None,
    ) -> None:
        self.limit = limit
        self.used = 0
        self.phase_limits: dict[str, int] = {}
        self.phase_used: dict[str, int] = {}
        self.injected = limit is not None
        self.alloc_remaining = 0
        self.alloc_limit = allocation_limit
        self.alloc_used = 0
        self.allocation_hook = allocation_hook
        self.fixed_remaining = 16
        self.fixed_precharged = False
        self.read_hook = read_hook

    def charge(self, amount: int = 1, phase: str = "scan") -> None:
        phase_used = self.phase_used.get(phase, 0)
        phase_limit = self.phase_limits.get(phase)
        if amount < 0 or (phase_limit is not None and phase_used + amount > phase_limit):
            raise _WorkLimitExceeded
        if self.limit is not None and self.used + amount > self.limit:
            raise _WorkLimitExceeded
        self.used += amount
        self.phase_used[phase] = phase_used + amount

    def configure(self, phase: str, limit: int) -> None:
        self.phase_limits[phase] = limit
        if self.phase_used.get(phase, 0) > limit:
            raise _WorkLimitExceeded

    def reserve_fixed(self) -> None:
        if not self.fixed_precharged:
            self.charge(16, "fixed")
            self.fixed_precharged = True

    def allow_node(self) -> None:
        if not self.injected and self.limit is not None:
            self.limit += 64

    def charge_allocation(self, label: str, amount: int = 1, *, fixed: bool = False) -> None:
        remaining = self.fixed_remaining if fixed else self.alloc_remaining
        if amount < 0 or amount > remaining:
            raise _WorkLimitExceeded
        if self.alloc_limit is not None and self.alloc_used + amount > self.alloc_limit:
            raise _WorkLimitExceeded
        if fixed:
            self.fixed_remaining -= amount
        else:
            self.alloc_remaining -= amount
        self.alloc_used += amount
        if callable(self.allocation_hook):
            cast(object, self.allocation_hook)(label)  # type: ignore[operator]


@dataclass(slots=True)
class _Item:
    span: OrgSpan
    depth: int
    children: list[_Item]


@dataclass(slots=True)
class _Run:
    start: int
    end: int
    line_start: int
    line_end: int
    roots: list[_Item]
    active: list[_Item]


def _utf8_width(codepoint: int) -> int:
    if codepoint < 0x80:
        return 1
    if codepoint < 0x800:
        return 2
    if codepoint < 0x10000:
        return 3
    return 4


def _fixed_failure(code: OrgDiagnosticCode, work: _Work | None = None) -> OrgParseResult:
    if work is not None:
        work.reserve_fixed()
        work.charge_allocation("fixed_diagnostic", 2, fixed=True)
    return OrgParseResult(None, (OrgDiagnostic(code, "error"),))


def _validate_page_title(page_title: object, work: _Work) -> OrgParseResult | None:
    if not isinstance(page_title, str):
        return _fixed_failure(OrgDiagnosticCode.PAGE_TITLE_REQUIRED, work)
    work.configure("title", 4 * (_MAX_TITLE_BYTES + 1))
    title_bytes = 0
    title_blank = True
    for char in page_title:
        work.charge(4, "title")
        point = ord(char)
        if 0xD800 <= point <= 0xDFFF:
            return _fixed_failure(OrgDiagnosticCode.INVALID_UNICODE, work)
        title_bytes += _utf8_width(point)
        if title_bytes > _MAX_TITLE_BYTES:
            return _fixed_failure(OrgDiagnosticCode.PAGE_TITLE_TOO_LARGE, work)
        if not char.isspace():
            title_blank = False
    if title_blank:
        return _fixed_failure(OrgDiagnosticCode.PAGE_TITLE_REQUIRED, work)
    return None


def _parse_org_text(
    text: str,
    *,
    page_title: object = _MISSING,
    _work: _Work | None = None,
    _node_hook: object = None,
    _allocation_limit: int | None = None,
    _allocation_hook: object = None,
    _read_hook: object = None,
    _title_validated: bool = False,
) -> OrgParseResult:
    """Instrumented implementation; private injection points exist for tests."""
    work = _work if _work is not None else _Work()
    if _allocation_limit is not None:
        work.alloc_limit = _allocation_limit
    if _allocation_hook is not None:
        work.allocation_hook = _allocation_hook
    if _read_hook is not None:
        work.read_hook = _read_hook
    if not isinstance(page_title, str):
        return _fixed_failure(OrgDiagnosticCode.PAGE_TITLE_REQUIRED, work)
    n = len(text)
    t = len(page_title)
    if not _title_validated:
        title_failure = _validate_page_title(page_title, work)
        if title_failure is not None:
            return title_failure

    work.configure("source", 4 * n)
    source_bytes = 0
    for char in text:
        work.charge(4, "source")
        point = ord(char)
        if 0xD800 <= point <= 0xDFFF:
            return _fixed_failure(OrgDiagnosticCode.INVALID_UNICODE, work)
        source_bytes += _utf8_width(point)
        if source_bytes > _MAX_SOURCE_BYTES:
            return _fixed_failure(OrgDiagnosticCode.SOURCE_TOO_LARGE, work)

    work.configure("index", 4 * n + _MAX_LINES)
    work.configure("fixed", 4 * _MAX_LINES + 16)
    if not work.injected:
        work.limit = 64 * (source_bytes + n + t + _MAX_LINES + 1)

    work.reserve_fixed()
    # Parallel integer arrays are the bounded physical-line index. End offsets
    # exclude LF/CRLF; a terminal line break does not create a phantom record.
    starts: list[int] = []
    ends: list[int] = []
    line_start = 0
    line_no = 1
    i = 0
    previous_was_cr = False
    while i < n:
        work.charge(4, "index")
        char = text[i]
        if char == "\n":
            if len(starts) >= _MAX_LINES:
                return _fixed_failure(OrgDiagnosticCode.LINE_LIMIT_EXCEEDED, work)
            work.charge(1, "index")
            work.charge(4, "fixed")
            starts.append(line_start)
            ends.append(i - 1 if i > line_start and previous_was_cr else i)
            line_no += 1
            line_start = i + 1
            if len(starts) > _MAX_LINES:
                return _fixed_failure(OrgDiagnosticCode.LINE_LIMIT_EXCEEDED, work)
        previous_was_cr = char == "\r"
        i += 1
    if n and line_start < n:
        if len(starts) >= _MAX_LINES:
            return _fixed_failure(OrgDiagnosticCode.LINE_LIMIT_EXCEEDED, work)
        work.charge(1, "index")
        work.charge(4, "fixed")
        starts.append(line_start)
        ends.append(n)
    if len(starts) > _MAX_LINES:
        return _fixed_failure(OrgDiagnosticCode.LINE_LIMIT_EXCEEDED, work)
    line_count = len(starts)
    work.configure("index", 4 * n + line_count)
    work.configure("scan", 16 * n + 2 * line_count)
    work.configure("alloc", 48 * _MAX_ELEMENTS)
    work.configure("fixed", 4 * line_count + 16)
    if not work.injected:
        work.limit = 64 * (source_bytes + n + t + line_count + 1)

    elements: list[OrgElement] = []
    diagnostics: list[OrgDiagnostic] = []
    node_count = 0
    list_run: _Run | None = None
    block_kind: str | None = None
    block_start = 0
    block_start_line = 0
    block_name_start = 0
    block_name_end = 0
    block_reserved = False
    drawer_start = 0
    drawer_line = 0
    drawer_owner: int | None = None
    drawer_properties: list[OrgProperty] = []
    previous_heading_ordinal: int | None = None
    previous_heading_line = 0
    heading_ordinal = 0

    def at(index: int) -> str:
        work.charge()
        if callable(work.read_hook):
            cast(object, work.read_hook)(index)  # type: ignore[operator]
        if index < 0 or index >= n:
            return "\0"
        return text[index]

    def span(start: int, end: int, first_line: int, last_line: int | None = None) -> OrgSpan:
        return OrgSpan(start, end, first_line, first_line if last_line is None else last_line)

    def reserve_node() -> None:
        nonlocal node_count
        if node_count >= _MAX_ELEMENTS:
            raise _Rejected(OrgDiagnosticCode.ELEMENT_LIMIT_EXCEEDED)
        work.allow_node()
        work.charge(48, "alloc")
        work.alloc_remaining += 48
        node_count += 1
        if callable(_node_hook):
            cast(object, _node_hook)(node_count)  # type: ignore[operator]

    def add_diagnostic(code: OrgDiagnosticCode, severity: Literal["warning", "error"], ln: int) -> None:
        if len(diagnostics) >= _MAX_DIAGNOSTICS - 1:
            work.charge_allocation("diagnostic_truncation", 2, fixed=True)
            diagnostics.append(OrgDiagnostic(OrgDiagnosticCode.DIAGNOSTICS_TRUNCATED, "error"))
            raise _Rejected(OrgDiagnosticCode.DIAGNOSTICS_TRUNCATED)
        work.charge_allocation("diagnostic", 2)
        diagnostics.append(OrgDiagnostic(code, severity, ln))

    def ascii_equal(start: int, end: int, word: str) -> bool:
        if end - start != len(word):
            return False
        for offset, expected in enumerate(word):
            value = at(start + offset)
            if "a" <= value <= "z":
                value = chr(ord(value) - 32)
            if value != expected:
                return False
        return True

    def horizontal(index: int) -> bool:
        value = at(index)
        return value == " " or value == "\t"

    def is_ascii_key(index: int, end: int, *, first_only: bool = False) -> bool:
        value = at(index)
        if not ("A" <= value <= "Z" or "a" <= value <= "z"):
            return False
        if first_only:
            return True
        for pos in range(index + 1, end):
            value = at(pos)
            if not (
                "A" <= value <= "Z" or "a" <= value <= "z"
                or "0" <= value <= "9" or value in "_-"
            ):
                return False
        return True

    def flush_list() -> None:
        nonlocal list_run
        if list_run is None:
            return
        work.charge_allocation("list_stack", 1)
        stack: list[tuple[_Item, bool]] = []
        for root in reversed(list_run.roots):
            work.charge_allocation("list_stack_entry", 2)
            stack.append((root, False))
        work.charge_allocation("list_frozen_map", 1)
        frozen: dict[int, OrgListItem] = {}
        while stack:
            item, visited = stack.pop()
            if not visited:
                work.charge_allocation("list_stack_entry", 2)
                stack.append((item, True))
                for child in reversed(item.children):
                    work.charge_allocation("list_stack_entry", 2)
                    stack.append((child, False))
            else:
                work.charge_allocation("list_child_values", 1)
                child_values: list[OrgListItem] = []
                for child in item.children:
                    work.charge_allocation("list_child_value_slot")
                    child_values.append(frozen.pop(id(child)))
                work.charge_allocation("list_child_tuple_slots", len(child_values))
                work.charge_allocation("list_frozen_record", 1)
                work.charge_allocation("list_frozen_map_entry")
                frozen[id(item)] = OrgListItem(item.span, tuple(child_values))
        work.charge_allocation("list_root_values", 1)
        root_values: list[OrgListItem] = []
        for root in list_run.roots:
            work.charge_allocation("list_root_value_slot")
            root_values.append(frozen.pop(id(root)))
        work.charge_allocation("list_root_tuple_slots", len(root_values))
        roots = tuple(root_values)
        work.charge_allocation("list_element_record")
        work.charge_allocation("list_element_append")
        elements.append(
            OrgList(
                span(list_run.start, list_run.end, list_run.line_start, list_run.line_end),
                False,
                roots,
            )
        )
        list_run = None

    def is_blank(start: int, end: int, recognition_start: int) -> bool:
        p = recognition_start
        while p < end:
            if not horizontal(p):
                return False
            p += 1
        return True

    def paragraph(start: int, end: int, ln: int, element_start: int) -> None:
        reserve_node()
        annotations: list[OrgReference] = []
        p = start
        while p < end:
            if at(p) != "[" or at(p + 1) != "[":
                p += 1
                continue
            candidate_start = p
            content = p + 2
            q = content
            close = -1
            split = -1
            while q < end:
                if at(q) == "]" and at(q + 1) == "]":
                    close = q
                    break
                if split < 0 and at(q) == "]" and at(q + 1) == "[":
                    split = q
                    q += 2
                else:
                    q += 1
            if close < 0:
                break
            target_end = split if split >= 0 else close
            extra_split = False
            if split >= 0:
                z = split + 2
                while z < close:
                    if at(z) == "]" and at(z + 1) == "[":
                        extra_split = True
                        break
                    z += 1
            if target_end == content or extra_split:
                p = close + 2
                continue
            target_kind: Literal["page", "external", "file"] = "page"
            resolution: Literal["unresolved", "never", "not_applicable"] = "unresolved"
            if ascii_equal(content, min(content + 5, target_end), "FILE:"):
                target_kind, resolution = "file", "never"
            elif (
                ascii_equal(content, min(content + 7, target_end), "HTTP://")
                or ascii_equal(content, min(content + 8, target_end), "HTTPS://")
                or ascii_equal(content, min(content + 7, target_end), "MAILTO:")
            ):
                target_kind, resolution = "external", "not_applicable"
            reserve_node()
            annotations.append(
                OrgReference(
                    span(candidate_start, close + 2, ln),
                    target_kind,
                    span(content, target_end, ln),
                    resolution,
                )
            )
            p = close + 2
        work.charge_allocation("paragraph_annotation_tuple_slots", len(annotations))
        elements.append(OrgParagraph(span(element_start, end, ln), tuple(annotations)))

    try:
        for index in range(line_count):
            start = starts[index]
            end = ends[index]
            ln = index + 1
            work.charge(2)
            recognition = start + 1 if index == 0 and at(start) == "\ufeff" else start
            if drawer_line:
                if ascii_equal(recognition, end, ":END:"):
                    if drawer_owner is None:
                        work.charge_allocation("drawer_element")
                        elements.append(OrgOpaque(span(drawer_start, end, drawer_line, ln), "unowned_property_drawer"))
                    else:
                        work.charge_allocation("drawer_property_tuple_slots", len(drawer_properties))
                        work.charge_allocation("drawer_element")
                        elements.append(
                            OrgPropertyDrawer(
                                span(drawer_start, end, drawer_line, ln),
                                tuple(drawer_properties),
                                drawer_owner,
                            )
                        )
                    drawer_line = 0
                    drawer_properties = []
                elif at(recognition) == ":":
                    p = recognition + 1
                    key_start = p
                    if p < end and is_ascii_key(p, p + 1, first_only=True):
                        p += 1
                        while p < end:
                            ch = at(p)
                            if "A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch == "_":
                                p += 1
                            else:
                                break
                        if p < end and at(p) == ":":
                            key_end = p
                            p += 1
                            while p < end and horizontal(p):
                                p += 1
                            reserve_node()
                            work.charge_allocation("drawer_property_slot")
                            drawer_properties.append(OrgProperty(span(key_start, key_end, ln), span(p, end, ln)))
                previous_heading_ordinal = None
                previous_heading_line = 0
                continue
            if is_blank(start, end, recognition):
                flush_list()
                previous_heading_ordinal = None
                previous_heading_line = 0
                continue
            if block_kind is not None:
                close_start = recognition
                closer = "#+END_SRC" if block_kind == "source_block" else "#+END_QUERY"
                if block_kind == "dynamic_block":
                    closer = "#+END:"
                matched = True
                prefix_length = len(closer)
                if block_kind == "other_block":
                    closer = "#+END_"
                    prefix_length = len(closer)
                for offset in range(prefix_length):
                    actual = at(close_start + offset)
                    expected = closer[offset]
                    if "a" <= actual <= "z":
                        actual = chr(ord(actual) - 32)
                    if actual != expected:
                        matched = False
                        break
                if matched and block_kind == "other_block":
                    for offset in range(block_name_end - block_name_start):
                        actual = at(close_start + prefix_length + offset)
                        expected = at(block_name_start + offset)
                        if "a" <= actual <= "z":
                            actual = chr(ord(actual) - 32)
                        if "a" <= expected <= "z":
                            expected = chr(ord(expected) - 32)
                        if actual != expected:
                            matched = False
                            break
                if matched:
                    tail = close_start + prefix_length
                    if block_kind == "other_block":
                        tail += block_name_end - block_name_start
                    while tail < end and horizontal(tail):
                        tail += 1
                    matched = tail == end
                if matched:
                    elements.append(
                        OrgOpaque(span(block_start, end, block_start_line, ln), cast(Literal[
                            "source_block", "query_block", "dynamic_block", "other_block"
                        ], block_kind))
                    )
                    block_kind = None
                    block_reserved = False
                continue
            if at(recognition) == "*":
                p = recognition
                while p < end and at(p) == "*":
                    p += 1
                level = p - recognition
                if p < end and at(p) == " ":
                    flush_list()
                    if level > _MAX_DEPTH:
                        raise _Rejected(OrgDiagnosticCode.NESTING_LIMIT_EXCEEDED)
                    title_start = p + 1
                    marker_start: int | None = None
                    marker_end = title_start
                    for candidate in ("TODO", "DONE", "WAITING"):
                        if ascii_equal(title_start, title_start + len(candidate), candidate) and (
                            horizontal(title_start + len(candidate))
                        ):
                            marker_start = title_start
                            marker_end = title_start + len(candidate)
                            title_start = marker_end
                            while title_start < end and horizontal(title_start):
                                title_start += 1
                            break
                    priority: str | None = None
                    if title_start + 4 <= end and at(title_start) == "[" and at(title_start + 1) == "#" and at(title_start + 3) == "]":
                        priority_char = at(title_start + 2)
                        if "A" <= priority_char <= "Z" and (
                            title_start + 4 == end or horizontal(title_start + 4)
                        ):
                            priority = priority_char
                            title_start += 4
                            while title_start < end and horizontal(title_start):
                                title_start += 1
                    title_end = end
                    while title_end > title_start and horizontal(title_end - 1):
                        title_end -= 1
                    reserve_node()
                    tag_spans: list[OrgSpan] = []
                    tag_start = title_end - 1
                    while tag_start > title_start and not horizontal(tag_start - 1):
                        tag_start -= 1
                    if tag_start > title_start and horizontal(tag_start - 1) and at(tag_start) == ":":
                        valid = True
                        q = tag_start + 1
                        part_start = q
                        tag_count = 0
                        while q < title_end:
                            value = at(q)
                            if value == ":":
                                if q == part_start:
                                    valid = False
                                else:
                                    tag_count += 1
                                part_start = q + 1
                            elif not (
                                "A" <= value <= "Z" or "a" <= value <= "z"
                                or "0" <= value <= "9" or value in "_@#%"
                            ):
                                valid = False
                            q += 1
                        if part_start != title_end or not tag_count:
                            valid = False
                        if valid:
                            title_end = tag_start - 1
                            while title_end > title_start and horizontal(title_end - 1):
                                title_end -= 1
                            q = tag_start + 1
                            part_start = q
                            while q < tag_start + 1 + (end - (tag_start + 1)):
                                if at(q) == ":":
                                    first, last = part_start, q
                                    reserve_node()
                                    tag_spans.append(span(first, last, ln))
                                    part_start = q + 1
                                q += 1
                    while title_start < title_end and horizontal(title_start):
                        title_start += 1
                    elements.append(
                        OrgHeading(
                            span(start if index != 0 or recognition == start else start, end, ln),
                            span(title_start, title_end, ln),
                            level,
                            span(marker_start, marker_end, ln) if marker_start is not None else None,
                            priority,
                            tuple(tag_spans),
                        )
                    )
                    heading_ordinal += 1
                    previous_heading_ordinal = heading_ordinal - 1
                    previous_heading_line = ln
                    continue
                flush_list()
                paragraph(recognition, end, ln, start)
                previous_heading_ordinal = None
                previous_heading_line = 0
                continue

            if at(recognition) == ":" and ascii_equal(recognition, end, ":PROPERTIES:"):
                flush_list()
                reserve_node()
                drawer_start = start
                drawer_line = ln
                drawer_owner = previous_heading_ordinal if previous_heading_line == ln - 1 else None
                drawer_properties = []
                previous_heading_ordinal = None
                previous_heading_line = 0
                continue

            # Block and directive recognizers.
            if at(recognition) == "#" and at(recognition + 1) == "+":
                p = recognition + 2
                key_start = p
                if p < end and is_ascii_key(p, p + 1, first_only=True):
                    p += 1
                    while p < end:
                        ch = at(p)
                        if "A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch in "_-":
                            p += 1
                        else:
                            break
                    key_end = p
                    key_is_begin = ascii_equal(key_start, key_end, "BEGIN")
                    source_begin = ascii_equal(key_start, key_end, "BEGIN_SRC") and (key_end == end or horizontal(key_end))
                    query_begin = ascii_equal(key_start, key_end, "BEGIN_QUERY") and (key_end == end or horizontal(key_end))
                    other_begin = (
                        key_end - key_start > 6
                        and ascii_equal(key_start, key_start + 6, "BEGIN_")
                        and key_end - key_start <= 38
                        and (key_end == end or horizontal(key_end))
                        and is_ascii_key(key_start + 6, key_start + 7, first_only=True)
                    )
                    if key_is_begin or source_begin or query_begin or other_begin:
                        flush_list()
                        begin_kind: str | None = None
                        name_start = key_end
                        name_end = key_end
                        if source_begin:
                            begin_kind, name_start, name_end = "source_block", key_start + 6, key_end
                        elif query_begin:
                            begin_kind, name_start, name_end = "query_block", key_start + 6, key_end
                        elif other_begin:
                            begin_kind, name_start, name_end = "other_block", key_start + 6, key_end
                        elif key_end < end and at(key_end) == ":" and key_end + 1 < end and horizontal(key_end + 1):
                            name_start = key_end + 2
                            name_end = name_start
                            while name_end < end and name_end - name_start <= 32:
                                ch = at(name_end)
                                if "A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch in "_-":
                                    name_end += 1
                                else:
                                    break
                            if name_start < name_end and name_end - name_start <= 32 and (name_end == end or horizontal(name_end)) and is_ascii_key(name_start, name_start + 1, first_only=True):
                                begin_kind = "dynamic_block"
                        elif key_end < end and at(key_end) == "_":
                            name_start = key_end + 1
                            name_end = name_start
                            while name_end < end and name_end - name_start <= 32:
                                ch = at(name_end)
                                if "A" <= ch <= "Z" or "a" <= ch <= "z" or "0" <= ch <= "9" or ch in "_-":
                                    name_end += 1
                                else:
                                    break
                            if name_start < name_end and name_end - name_start <= 32 and (name_end == end or horizontal(name_end)) and is_ascii_key(name_start, name_start + 1, first_only=True):
                                begin_kind = "other_block"
                        if begin_kind is not None:
                            reserve_node()
                            block_kind, block_start, block_start_line = begin_kind, start, ln
                            block_name_start, block_name_end = name_start, name_end
                            block_reserved = True
                            if begin_kind in {"source_block", "query_block", "dynamic_block"}:
                                add_diagnostic(OrgDiagnosticCode.OPAQUE_EXECUTABLE_SYNTAX, "warning", ln)
                            previous_heading_ordinal = None
                            previous_heading_line = 0
                            continue
                    if p < end and at(p) == ":":
                        flush_list()
                        value_start = p + 1
                        while value_start < end and horizontal(value_start):
                            value_start += 1
                        if ascii_equal(key_start, key_end, "MACRO"):
                            reserve_node()
                            elements.append(OrgOpaque(span(start, end, ln), "macro_directive"))
                            add_diagnostic(OrgDiagnosticCode.OPAQUE_EXECUTABLE_SYNTAX, "warning", ln)
                        else:
                            reserve_node()
                            elements.append(
                                OrgDirective(
                                    span(start, end, ln),
                                    span(key_start, key_end, ln),
                                    span(value_start, end, ln),
                                )
                            )
                        previous_heading_ordinal = None
                        previous_heading_line = 0
                        continue

            # List candidates are tested before timestamp and paragraph.
            if at(recognition) == " " or at(recognition) == "-":
                p = recognition
                while p < end and at(p) == " ":
                    p += 1
                indent = p - recognition
                if p + 1 < end and at(p) == "-" and at(p + 1) == " " and indent % 2 == 0:
                    depth = indent // 2 + 1
                    if list_run is not None:
                        while list_run.active and list_run.active[-1].depth >= depth:
                            list_run.active.pop()
                    parent = list_run.active[-1] if list_run is not None and list_run.active else None
                    if depth == 1 or (parent is not None and parent.depth == depth - 1):
                        if depth > _MAX_DEPTH:
                            raise _Rejected(OrgDiagnosticCode.NESTING_LIMIT_EXCEEDED)
                        if list_run is None:
                            reserve_node()
                            list_run = _Run(start, end, ln, ln, [], [])
                        reserve_node()
                        item_start = span(start, end, ln)
                        item = _Item(item_start, depth, [])
                        if depth == 1:
                            list_run.roots.append(item)
                        else:
                            assert parent is not None
                            parent.children.append(item)
                        list_run.active.append(item)
                        list_run.end = end
                        list_run.line_end = ln
                        previous_heading_ordinal = None
                        previous_heading_line = 0
                        continue
                    flush_list()
                    paragraph(recognition, end, ln, start)
                    previous_heading_ordinal = None
                    previous_heading_line = 0
                    continue

            # Date-bearing and opaque timestamps.
            timestamp_kind: str | None = None
            raw_start = recognition
            date_value: date | None = None
            for key, kind in (("SCHEDULED", "scheduled"), ("DEADLINE", "deadline"), ("CLOSED", "closed"), ("CLOCK", "clock")):
                key_end = recognition + len(key)
                if key_end >= end or not ascii_equal(recognition, key_end, key):
                    continue
                if kind in {"scheduled", "deadline"}:
                    if at(key_end) != ":":
                        continue
                    raw_start = key_end + 1
                    if raw_start >= end or not horizontal(raw_start):
                        continue
                    timestamp_kind = kind
                    break
                if at(key_end) != ":":
                    continue
                boundary = key_end + 1
                if boundary < end and not horizontal(boundary):
                    continue
                timestamp_kind = kind
                raw_start = boundary
                break
            if timestamp_kind is not None:
                flush_list()
                if timestamp_kind in {"closed", "clock"}:
                    reserve_node()
                    elements.append(OrgTimestamp(span(start, end, ln), span(start, end, ln), cast(Literal["closed", "clock"], timestamp_kind), None))
                    previous_heading_ordinal = None
                    previous_heading_line = 0
                    continue
                p = raw_start
                while p < end and horizontal(p):
                    p += 1
                valid = p + 16 <= end and at(p) == "<" and at(p + 5) == "-" and at(p + 8) == "-" and at(p + 11) == " " and at(p + 15) == ">"
                if p + 16 <= end:
                    year = 0
                    month = 0
                    day = 0
                    for value_index, (number_start, width) in enumerate(((p + 1, 4), (p + 6, 2), (p + 9, 2))):
                        numeric_value = 0
                        for digit_offset in range(width):
                            ch = at(number_start + digit_offset)
                            if not ("0" <= ch <= "9"):
                                valid = False
                            else:
                                numeric_value = numeric_value * 10 + ord(ch) - 48
                        if value_index == 0:
                            year = numeric_value
                        elif value_index == 1:
                            month = numeric_value
                        else:
                            day = numeric_value
                    for pos in (p + 12, p + 13, p + 14):
                        ch = at(pos)
                        if not ("A" <= ch <= "Z" or "a" <= ch <= "z"):
                            valid = False
                    tail = p + 16
                    while tail < end and horizontal(tail):
                        tail += 1
                    if tail != end:
                        valid = False
                    if valid:
                        month_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
                        if year < 1 or month < 1 or month > 12:
                            valid = False
                        else:
                            maximum_day = month_days[month - 1]
                            if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
                                maximum_day = 29
                            if day < 1 or day > maximum_day:
                                valid = False
                else:
                    valid = False
                if valid:
                    reserve_node()
                    date_value = date(year, month, day)
                    elements.append(OrgTimestamp(span(start, end, ln), span(start, end, ln), cast(Literal["scheduled", "deadline"], timestamp_kind), date_value))
                    previous_heading_ordinal = None
                    previous_heading_line = 0
                    continue

            flush_list()
            paragraph(recognition, end, ln, start)
            previous_heading_ordinal = None
            previous_heading_line = 0

        flush_list()
        if block_kind is not None:
            if not block_reserved:
                reserve_node()
            elements.append(OrgOpaque(span(block_start, n, block_start_line, line_count), cast(Literal[
                "source_block", "query_block", "dynamic_block", "other_block"
            ], block_kind)))
        if drawer_line:
            work.charge_allocation("drawer_unclosed_element")
            elements.append(OrgOpaque(span(drawer_start, n, drawer_line, line_count), "unterminated_drawer"))
            add_diagnostic(OrgDiagnosticCode.UNCLOSED_DRAWER, "error", drawer_line)
        work.charge_allocation("document_element_tuple_slots", len(elements))
        work.charge_allocation("diagnostic_tuple_slots", len(diagnostics))
        return OrgParseResult(
            OrgDocument(page_title, text, tuple(elements)),
            tuple(diagnostics),
        )
    except _Rejected as rejected:
        if rejected.code == OrgDiagnosticCode.DIAGNOSTICS_TRUNCATED:
            work.charge_allocation("diagnostic_truncation_tuple_slots", 1, fixed=True)
            return OrgParseResult(None, tuple(diagnostics))
        work.charge_allocation("fixed_resource_diagnostic", 2, fixed=True)
        return OrgParseResult(None, (OrgDiagnostic(rejected.code, "error"),))


def parse_org_text(text: str, *, page_title: object = _MISSING) -> OrgParseResult:
    """Parse a bounded finite subset of Org syntax without side effects."""
    return _parse_org_text(text, page_title=page_title)


def parse_org_file(path: str | Path, *, page_title: object = _MISSING) -> OrgParseResult:
    """Read and parse one explicitly selected Org file."""
    work = _Work()
    title_failure = _validate_page_title(page_title, work)
    if title_failure is not None:
        return title_failure

    source = read_org_source(path)
    if isinstance(source, OrgSourceFailure):
        if source.code is OrgSourceCode.PATH_INVALID:
            return _fixed_failure(OrgDiagnosticCode.FILE_PATH_INVALID, work)
        if source.code is OrgSourceCode.SOURCE_UNSUPPORTED:
            return _fixed_failure(OrgDiagnosticCode.FILE_SOURCE_UNSUPPORTED, work)
        if source.code is OrgSourceCode.SOURCE_REJECTED:
            return _fixed_failure(OrgDiagnosticCode.FILE_SOURCE_REJECTED, work)
        if source.code is OrgSourceCode.READ_FAILED:
            return _fixed_failure(OrgDiagnosticCode.FILE_READ_FAILED, work)
        if source.code is OrgSourceCode.SOURCE_TOO_LARGE:
            return _fixed_failure(OrgDiagnosticCode.SOURCE_TOO_LARGE, work)
        return _fixed_failure(OrgDiagnosticCode.FILE_SOURCE_UNSUPPORTED, work)

    source_bytes = len(source)
    if source_bytes > _MAX_SOURCE_BYTES:
        return _fixed_failure(OrgDiagnosticCode.SOURCE_TOO_LARGE, work)
    work.configure("file", 8 * source_bytes)
    work.charge(8 * source_bytes, "file")
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _fixed_failure(OrgDiagnosticCode.INVALID_UTF8, work)
    return _parse_org_text(
        text,
        page_title=page_title,
        _work=work,
        _title_validated=True,
    )
