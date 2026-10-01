"""Shared private values for Org source parsing and platform readers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OrgSourceCode(StrEnum):
    PATH_INVALID = "ORG_FILE_PATH_INVALID"
    SOURCE_UNSUPPORTED = "ORG_FILE_SOURCE_UNSUPPORTED"
    SOURCE_REJECTED = "ORG_FILE_SOURCE_REJECTED"
    READ_FAILED = "ORG_FILE_READ_FAILED"
    SOURCE_TOO_LARGE = "ORG_SOURCE_TOO_LARGE"


@dataclass(frozen=True, slots=True)
class OrgSourceFailure:
    code: OrgSourceCode


_MAX_SOURCE_BYTES = 8_388_608


def _utf16_code_units(value: str, *, max_units: int | None = None) -> tuple[int, ...] | None:
    units: list[int] = []
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            return None
        if codepoint <= 0xFFFF:
            units.append(codepoint)
        else:
            supplementary = codepoint - 0x10000
            units.extend((0xD800 + (supplementary >> 10), 0xDC00 + (supplementary & 0x3FF)))
        if max_units is not None and len(units) > max_units:
            return None
    return tuple(units)
