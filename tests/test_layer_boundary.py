"""Clean Architecture layer import boundaries (Uncle Bob dependency rule)."""

from __future__ import annotations

from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "logseq_matryca_parser"

_ENTITY_USE_CASE = frozenset(
    {
        "logos_core.py",
        "exceptions.py",
        "logos_parser.py",
        "graph.py",
        "logseq_markdown.py",
        "logseq_paths.py",
    }
)

_ADAPTERS = frozenset(
    {
        "synapse.py",
        "forge.py",
        "agent_writer.py",
        "agent_press.py",
        "lens.py",
    }
)

_FORBIDDEN_FRAMEWORKS = (
    "typer",
    "rich",
    "langchain",
    "llama_index",
    "networkx",
    "pyvis",
)

_FORBIDDEN_INNER_ADAPTER_IMPORTS = (
    "logseq_matryca_parser.kinetic",
    "from logseq_matryca_parser import kinetic",
    "from .kinetic",
    "from logseq_matryca_parser.kinetic",
)

_FORBIDDEN_USE_CASE_ADAPTER_IMPORTS = (
    "logseq_matryca_parser.synapse",
    "logseq_matryca_parser.forge",
    "logseq_matryca_parser.lens",
    "logseq_matryca_parser.agent_writer",
    "logseq_matryca_parser.agent_press",
    "from .synapse",
    "from .forge",
    "from .lens",
    "from .agent_writer",
    "from .agent_press",
)


def _module_text(name: str) -> str:
    return (_SRC / name).read_text(encoding="utf-8")


def test_inner_rings_do_not_import_frameworks() -> None:
    offenders: list[str] = []
    for name in sorted(_ENTITY_USE_CASE):
        text = _module_text(name)
        for framework in _FORBIDDEN_FRAMEWORKS:
            if f"import {framework}" in text or f"from {framework}" in text:
                offenders.append(f"{name} imports {framework}")
    assert offenders == []


def test_use_cases_do_not_import_adapters() -> None:
    offenders: list[str] = []
    for name in sorted(_ENTITY_USE_CASE):
        text = _module_text(name)
        for needle in _FORBIDDEN_USE_CASE_ADAPTER_IMPORTS:
            if needle in text:
                offenders.append(f"{name} imports adapter via {needle!r}")
    assert offenders == []


def test_adapters_do_not_import_kinetic() -> None:
    offenders: list[str] = []
    for name in sorted(_ADAPTERS):
        text = _module_text(name)
        for needle in _FORBIDDEN_INNER_ADAPTER_IMPORTS:
            if needle in text:
                offenders.append(f"{name} imports kinetic via {needle!r}")
    assert offenders == []


def test_use_cases_do_not_import_kinetic() -> None:
    offenders: list[str] = []
    for name in sorted(_ENTITY_USE_CASE):
        text = _module_text(name)
        for needle in _FORBIDDEN_INNER_ADAPTER_IMPORTS:
            if needle in text:
                offenders.append(f"{name} imports kinetic via {needle!r}")
    assert offenders == []
