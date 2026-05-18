from __future__ import annotations

import re

from logseq_matryca_parser import __version__


def test_package_version_is_public_semver_string() -> None:
    """Runtime __version__ must be a semver-shaped string for distribution tooling."""
    assert isinstance(__version__, str)
    assert re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
        __version__,
    ), f"unexpected __version__ format: {__version__!r}"
