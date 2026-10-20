"""Architecture guard for the private Org source-reader modules."""

from __future__ import annotations

import ast
from pathlib import Path


def _org_source_import_graph() -> dict[str, set[str]]:
    package_dir = Path(__file__).resolve().parents[1] / "src" / "logseq_matryca_parser"
    module_paths = {path.stem: path for path in package_dir.glob("_org_source*.py")}
    module_names = set(module_paths)
    graph: dict[str, set[str]] = {name: set() for name in module_names}

    for name, path in module_paths.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level == 1:
                    if node.module in module_names:
                        graph[name].add(node.module)
                    elif node.module is None:
                        graph[name].update(alias.name for alias in node.names if alias.name in module_names)
                elif node.module == "logseq_matryca_parser":
                    graph[name].update(alias.name for alias in node.names if alias.name in module_names)
                elif node.module and node.module.startswith("logseq_matryca_parser."):
                    imported_module = node.module.removeprefix("logseq_matryca_parser.")
                    if imported_module in module_names:
                        graph[name].add(imported_module)
            elif isinstance(node, ast.Import):
                prefix = "logseq_matryca_parser."
                graph[name].update(
                    alias.name.removeprefix(prefix)
                    for alias in node.names
                    if alias.name.startswith(prefix) and alias.name.removeprefix(prefix) in module_names
                )

    return graph


def _find_import_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    active: list[str] = []
    visited: set[str] = set()

    def visit(module: str) -> list[str] | None:
        if module in active:
            start = active.index(module)
            return [*active[start:], module]
        if module in visited:
            return None
        active.append(module)
        for imported in sorted(graph[module]):
            cycle = visit(imported)
            if cycle is not None:
                return cycle
        active.pop()
        visited.add(module)
        return None

    for module in sorted(graph):
        cycle = visit(module)
        if cycle is not None:
            return cycle
    return None


def test_org_source_modules_have_no_static_import_cycle() -> None:
    cycle = _find_import_cycle(_org_source_import_graph())
    assert cycle is None, f"Org source import cycle: {' -> '.join(cycle or [])}"
