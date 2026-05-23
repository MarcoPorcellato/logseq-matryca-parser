"""Logseq graph path helpers: discovery filters and title/filename translation."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)

_NAMESPACE_SEPARATOR = "___"
_LOGSEQ_URI_SAFE = "-_.!~*'()"
_EXCLUDED_PATH_PARTS: frozenset[str] = frozenset({"logseq", ".recycle", ".git"})


def is_excluded_graph_path(path: Path) -> bool:
    """Return True when ``path`` lives under Logseq backup, recycle, or VCS dirs."""
    excluded = _EXCLUDED_PATH_PARTS.intersection(path.parts)
    if excluded:
        logger.debug("Excluded graph path %s (parts=%s)", path, sorted(excluded))
        return True
    return False


def encode_page_title_segment(segment: str) -> str:
    """Percent-encode reserved OS characters within a single title segment."""
    return quote(segment, safe=_LOGSEQ_URI_SAFE)


def decode_page_title_segment(segment: str) -> str:
    """Decode a single filesystem segment back to its semantic title fragment."""
    return unquote(segment)


def page_title_to_filename(title: str) -> str:
    """Translate a page title into a flat Logseq filename stem (no ``.md`` suffix)."""
    flattened = title.replace("/", _NAMESPACE_SEPARATOR)
    return encode_page_title_segment(flattened)


def filename_to_page_title(name: str) -> str:
    """Translate a flat filename stem back into a semantic page title."""
    decoded = unquote(name)
    return decoded.replace(_NAMESPACE_SEPARATOR, "/")


def _last_part_index(parts: tuple[str, ...] | list[str], token: str) -> int | None:
    """Return the rightmost index of ``token`` in ``parts``, or ``None`` when absent."""
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == token:
            return index
    return None


def derive_page_title_from_source_path(path: Path) -> str:
    """Reconstruct the Logseq page title from a ``pages/`` or ``journals/`` markdown path."""
    resolved = path.resolve()
    stem_path = resolved.with_suffix("")
    parts = list(stem_path.parts)

    page_index = _last_part_index(parts, "pages")
    if page_index is not None:
        segments = parts[page_index + 1 :]
    elif (journal_index := _last_part_index(parts, "journals")) is not None:
        segments = parts[journal_index + 1 :]
    else:
        return filename_to_page_title(resolved.stem)

    if not segments:
        return resolved.stem

    if len(segments) == 1:
        return filename_to_page_title(segments[0])

    return "/".join(decode_page_title_segment(segment) for segment in segments)


def page_title_to_relative_path(title: str) -> Path:
    """Map a semantic page title to a relative ``pages/`` or ``journals/`` markdown path."""
    segments = [segment for segment in title.split("/") if segment]
    if not segments:
        return Path("untitled.md")
    encoded = [encode_page_title_segment(segment) for segment in segments]
    if len(encoded) == 1:
        return Path(f"{encoded[0]}.md")
    return Path(*encoded[:-1]) / f"{encoded[-1]}.md"
