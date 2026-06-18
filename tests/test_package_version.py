from __future__ import annotations

import importlib.metadata
import re

from logseq_matryca_parser import __version__


def test_package_version_is_public_semver_string() -> None:
    """Runtime __version__ must be a semver-shaped string for distribution tooling."""
    assert isinstance(__version__, str)
    assert re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
        __version__,
    ), f"unexpected __version__ format: {__version__!r}"


def test_package_version_matches_distribution_metadata() -> None:
    """Runtime __version__ must match the installed distribution metadata."""
    assert __version__ == importlib.metadata.version("logseq-matryca-parser")


def test_public_api_exports_are_importable() -> None:
    """Core symbols are reachable from the package root without deep import paths."""
    import logseq_matryca_parser as pkg

    for name in (
        "StackMachineParser",
        "LogseqGraph",
        "LogseqPage",
        "LogseqNode",
        "SynapseAdapter",
        "SessionAliasRegistry",
        "GraphVisualizer",
    ):
        assert hasattr(pkg, name), f"missing public export: {name}"
    assert pkg.StackMachineParser is pkg.LogosParser
