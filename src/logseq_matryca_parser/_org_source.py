"""Private, fail-closed acquisition boundary for one Org source file."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ._org_source_contract import OrgSourceCode, OrgSourceFailure, _utf16_code_units

_MAX_PATH_CHARS = 32_767
_DRIVE_PATH = re.compile(r"^[A-Za-z]:\\")
_WINDOWS_INVALID = set('<>:"/\\|?*')
_WINDOWS_DEVICES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
    *(f"COM{digit}" for digit in "¹²³"),
    *(f"LPT{digit}" for digit in "¹²³"),
}


def _invalid() -> OrgSourceFailure:
    return OrgSourceFailure(OrgSourceCode.PATH_INVALID)


def _windows_components(spelling: str) -> tuple[str, list[tuple[str, tuple[int, ...]]]] | OrgSourceFailure:
    if len(spelling) < 4 or not _DRIVE_PATH.match(spelling):
        return _invalid()
    drive = spelling[0].upper()
    tail = spelling[3:]
    components = tail.split("\\")
    if not components or any(not component or component in {".", ".."} for component in components):
        return _invalid()
    if not components[-1].endswith(".org"):
        return _invalid()
    parsed_components: list[tuple[str, tuple[int, ...]]] = []
    for component in components:
        if component.endswith((" ", ".")) or any(ord(char) < 32 or char in _WINDOWS_INVALID for char in component):
            return _invalid()
        units = _utf16_code_units(component, max_units=255)
        if units is None:
            return _invalid()
        if ":" in component:
            return _invalid()
        basename = component.split(".", 1)[0].upper()
        if basename in _WINDOWS_DEVICES:
            return _invalid()
        parsed_components.append((component, units))
    return drive, parsed_components


def _posix_components(spelling: str) -> list[str] | OrgSourceFailure:
    if not spelling.startswith("/") or spelling.startswith("//"):
        return _invalid()
    components = spelling[1:].split("/")
    if not components or any(component in {"", ".", ".."} for component in components):
        return _invalid()
    if not components[-1].endswith(".org"):
        return _invalid()
    return components


def _exposed_spelling(path: str | Path) -> str | OrgSourceFailure:
    if not isinstance(path, (str, Path)):
        return _invalid()
    try:
        spelling = os.fspath(path)
    except (TypeError, ValueError, OSError):
        return _invalid()
    if not isinstance(spelling, str) or not spelling or len(spelling) > _MAX_PATH_CHARS or "\x00" in spelling:
        return _invalid()
    return spelling


def read_org_source(path: str | Path) -> bytes | OrgSourceFailure:
    """Read raw bytes from one explicitly selected, policy-approved Org file."""
    spelling = _exposed_spelling(path)
    if isinstance(spelling, OrgSourceFailure):
        return spelling

    # A drive-qualified spelling is always interpreted by the strict Windows
    # grammar, even on POSIX, so malformed Windows paths are not misclassified.
    if len(spelling) >= 2 and spelling[1] == ":":
        parsed = _windows_components(spelling)
        if isinstance(parsed, OrgSourceFailure):
            return parsed
        if sys.platform != "win32" or os.name != "nt" or not (sys.maxsize > 2**32):
            return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)
        from ._org_source_windows import read_windows_source

        return read_windows_source(*parsed)

    if sys.platform == "win32" and spelling.startswith("/"):
        return _invalid()

    components = _posix_components(spelling)
    if isinstance(components, OrgSourceFailure):
        return components
    if sys.platform == "darwin" and os.uname().machine == "arm64":
        from ._org_source_posix import read_posix_source

        return read_posix_source(components, platform="darwin")
    if sys.platform == "linux" and os.uname().machine == "x86_64":
        from ._org_source_posix import read_posix_source

        return read_posix_source(components, platform="linux")
    return OrgSourceFailure(OrgSourceCode.SOURCE_UNSUPPORTED)


__all__ = ["OrgSourceCode", "OrgSourceFailure", "read_org_source"]
