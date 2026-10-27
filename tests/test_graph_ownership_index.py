"""Synthetic ownership semantics and deterministic enumeration-work regressions."""

from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import Any

import pytest

import logseq_matryca_parser.graph as graph_module
from logseq_matryca_parser.graph import LogseqGraph
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage


def _node(name: str, source: str | None) -> LogseqNode:
    return LogseqNode(uuid=name, content=name, indent_level=0, source_path=source)


def _page(title: str, source: str | None, nodes: list[LogseqNode]) -> LogseqPage:
    return LogseqPage(title=title, raw_content="", source_path=source, root_nodes=nodes)


def _graph(root: Path, pages: dict[str, LogseqPage], nodes: list[LogseqNode]) -> LogseqGraph:
    return LogseqGraph(
        graph_path=root,
        pages=pages,
        source_pages={},
        node_registry={node.uuid: node for node in nodes},
        backlink_registry={},
        lower_title_map={},
    )


def _slow_owners(graph: LogseqGraph, nodes: list[LogseqNode]) -> list[LogseqPage | None]:
    """Test-only pre-change relation; explicit identity assertions remain independent."""
    result: list[LogseqPage | None] = []
    for node in nodes:
        found: LogseqPage | None = None
        if node.source_path:
            source = Path(node.source_path).resolve()
            matched: set[int] = set()
            for page in graph.pages.values():
                if id(page) in matched:
                    continue
                if page.source_path and Path(page.source_path).resolve() == source:
                    matched.add(id(page))
                    found = page
        result.append(found)
    return result


def _count_resolves(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    calls: list[Path] = []
    original = Path.resolve

    def counted(path: Path, *args: Any, **kwargs: Any) -> Path:
        calls.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", counted)
    return calls


def _forbid_graph_opens(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    original = builtins.open
    original_path_open = Path.open

    def guarded(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, os.PathLike)) and Path(file).is_relative_to(root):
            raise AssertionError("ownership must not open synthetic source files")
        return original(file, *args, **kwargs)

    def guarded_path_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.is_relative_to(root):
            raise AssertionError("ownership must not open synthetic source files")
        return original_path_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
    monkeypatch.setattr(Path, "open", guarded_path_open)


def _four_page_graph(
    root: Path, blocks: int, aliases: int = 0
) -> tuple[LogseqGraph, list[LogseqNode]]:
    sources = [str(root / f"Page-{index}.md") for index in range(4)]
    nodes = [_node(f"block-{index}", sources[index % 4]) for index in range(blocks)]
    pages = {
        f"Page-{index}": _page(f"Page-{index}", source, nodes[index::4])
        for index, source in enumerate(sources)
    }
    for index, page in enumerate(tuple(pages.values())):
        for alias in range(aliases):
            pages[f"alias-{index}-{alias}"] = page
    return _graph(root, pages, nodes), nodes


@pytest.mark.parametrize("blocks", [64, 640])
@pytest.mark.parametrize("operation", ["iteration", "query"])
def test_attached_nodes_resolve_work_is_independent_of_block_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocks: int, operation: str
) -> None:
    """A node-by-page scan breaks the fixed P+U path-resolution work bound."""
    graph, expected = _four_page_graph(tmp_path, blocks)
    _forbid_graph_opens(monkeypatch, tmp_path)
    calls = _count_resolves(monkeypatch)

    actual = (
        list(graph.iter_attached_nodes()) if operation == "iteration" else graph.query().execute()
    )
    observed = len(calls)

    assert len(actual) == blocks
    assert all(left is right for left, right in zip(actual, expected, strict=True))
    assert observed <= 8, f"ownership resolved {observed} paths for P=4, U=4"


def test_alias_keys_do_not_multiply_ownership_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph, expected = _four_page_graph(tmp_path, 64, aliases=64)
    _forbid_graph_opens(monkeypatch, tmp_path)
    calls = _count_resolves(monkeypatch)

    actual = list(graph.iter_attached_nodes())
    observed = len(calls)

    assert len(graph.pages) == 260
    assert all(left is right for left, right in zip(actual, expected, strict=True))
    assert observed <= 8, f"alias entries multiplied path work: {observed}"


def test_page_ownership_index_preserves_last_distinct_match(tmp_path: Path) -> None:
    source = str(tmp_path / "Shared.md")
    first = _page("first", source, [])
    last = _page("last", source, [])
    other = _page("other", str(tmp_path / "Other.md"), [])
    pages = {
        "first": first,
        "last": last,
        "repeat-first": first,
        "other": other,
        "no-source": _page("no-source", None, []),
    }

    owners = graph_module._page_ownership_index(pages)

    assert owners[Path(source).resolve()] is last
    assert owners[Path(other.source_path or "").resolve()] is other
    assert len(owners) == 2


@pytest.mark.parametrize("restore_alias", [False, True])
def test_attachment_uses_published_pages_and_preserves_registry_order(
    tmp_path: Path, restore_alias: bool
) -> None:
    alpha = _node("alpha", str(tmp_path / "Alpha.md"))
    beta = _node("beta", str(tmp_path / "Beta.md"))
    detached = _node("detached", str(tmp_path / "Detached.md"))
    no_source = _node("no-source", None)
    alpha_page = _page("Shared", alpha.source_path, [alpha])
    beta_page = _page("Shared", beta.source_path, [beta])
    pages = {"Shared": beta_page, "beta-alias": beta_page}
    if restore_alias:
        pages["alpha-alias"] = alpha_page
    registry = [detached, beta, no_source, alpha]
    graph = _graph(tmp_path, pages, registry)
    # Physical inventory deliberately retains the collision loser.
    graph._source_pages = {str(alpha.source_path): alpha_page, str(beta.source_path): beta_page}
    owners = _slow_owners(graph, registry)

    actual = list(graph.iter_attached_nodes())

    expected = [beta, alpha] if restore_alias else [beta]
    assert [node.uuid for node in actual] == (["beta", "alpha"] if restore_alias else ["beta"])
    assert all(left is right for left, right in zip(actual, expected, strict=True))
    assert [node.uuid for node, owner in zip(registry, owners, strict=True) if owner] == [
        node.uuid for node in expected
    ]


def test_source_path_membership_does_not_require_outline_or_uuid_identity(tmp_path: Path) -> None:
    source = str(tmp_path / "Page.md")
    foreign = _node("not-in-outline", source)
    page = _page("Page", source, [])
    graph = _graph(tmp_path, {"Page": page}, [foreign])

    assert list(graph.iter_attached_nodes()) == [foreign]
    assert graph.page_for_node(foreign) is page


@pytest.mark.parametrize("with_nodes", [False, True])
def test_empty_or_source_free_registry_does_not_resolve_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_nodes: bool
) -> None:
    page = _page("Unresolved", str(tmp_path / "NotRead.md"), [])
    nodes = [_node("none", None), _node("blank", "")] if with_nodes else []
    graph = _graph(tmp_path, {"Unresolved": page}, nodes)

    def reject_resolve(*_args: Any, **_kwargs: Any) -> Path:
        raise AssertionError("empty/source-free enumeration must not resolve pages")

    monkeypatch.setattr(Path, "resolve", reject_resolve)
    assert list(graph.iter_attached_nodes()) == []


@pytest.mark.parametrize("failure_on", ["node", "page"])
def test_ownership_resolution_errors_propagate_without_partial_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_on: str
) -> None:
    page_path = tmp_path / "Page.md"
    node_path = tmp_path / "Node.md" if failure_on == "node" else page_path
    good_path = tmp_path / "Good.md"
    good_node = _node("good", str(good_path))
    node = _node("block", str(node_path))
    graph = _graph(
        tmp_path,
        {
            "Good": _page("Good", str(good_path), [good_node]),
            "Page": _page("Page", str(page_path), []),
        },
        [good_node, node],
    )
    failing = node_path if failure_on == "node" else page_path
    original = Path.resolve

    def resolve(path: Path, *args: Any, **kwargs: Any) -> Path:
        if path == failing:
            raise PermissionError("synthetic ownership resolution denial")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    iterator = graph.iter_attached_nodes()
    with pytest.raises(PermissionError, match="synthetic ownership resolution denial"):
        next(iterator)


def test_equivalent_path_spellings_and_missing_paths_follow_existing_relation(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "Missing.md"
    equivalent = tmp_path / "unused" / ".." / "Missing.md"
    node = _node("block", str(equivalent))
    page = _page("Page", str(canonical), [])
    graph = _graph(tmp_path, {"Page": page}, [node])

    assert _slow_owners(graph, [node]) == [page]
    assert list(graph.iter_attached_nodes()) == [node]
    assert not canonical.exists()


def test_symlink_retargeting_is_observed_by_the_next_enumeration(tmp_path: Path) -> None:
    first, second, alias = tmp_path / "First.md", tmp_path / "Second.md", tmp_path / "Alias.md"
    first.write_text("- synthetic first\n", encoding="utf-8")
    second.write_text("- synthetic second\n", encoding="utf-8")
    try:
        alias.symlink_to(first)
    except OSError:
        pytest.skip("synthetic symlink creation is unavailable")
    node = _node("alias-node", str(alias))
    page = _page("First", str(first), [])
    graph = _graph(tmp_path, {"First": page}, [node])

    assert list(graph.iter_attached_nodes()) == [node]
    alias.unlink()
    alias.symlink_to(second)
    assert _slow_owners(graph, [node]) == [None]
    assert list(graph.iter_attached_nodes()) == []
    alias.unlink()
    alias.symlink_to(first)
    assert list(graph.iter_attached_nodes()) == [node]


def test_supported_collision_and_file_lifecycle_rebuilds_are_fresh(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    alpha = pages / "Alpha.md"
    beta = pages / "Beta.md"
    alpha.write_text("- alpha\n", encoding="utf-8")
    beta.write_text("- beta\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(tmp_path)

    def contents() -> list[str]:
        return [node.content for node in graph.iter_attached_nodes()]

    assert contents() == ["alpha", "beta"]
    beta.write_text("alias:: Alpha\n\n- beta override\n", encoding="utf-8")
    graph.invalidate_and_reload_page(beta)
    assert contents() == ["beta override"]
    beta.unlink()
    graph.invalidate_and_reload_page(beta)
    assert contents() == ["alpha"]
    beta.write_text("- beta recreated\n", encoding="utf-8")
    graph.invalidate_and_reload_page(beta)
    assert contents() == ["alpha", "beta recreated"]
    renamed = pages / "Gamma.md"
    beta.rename(renamed)
    graph.invalidate_and_reload_page(beta)
    graph.invalidate_and_reload_page(renamed)
    assert contents() == ["alpha", "beta recreated"]
    assert all(node.source_path != str(beta) for node in graph.iter_attached_nodes())
