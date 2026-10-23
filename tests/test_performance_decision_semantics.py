"""Independent small-graph expectations and bounded observation sensitivity."""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, fields
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _semantics() -> ModuleType:
    return importlib.import_module("tests.performance.decision_semantics")


def _controlled_page(root: Path, *, deep: bool = False) -> Any:
    """Literal native models, not Parser/generator output or an expected-model helper."""
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

    title = "runtime-evidence-deep" if deep else "runtime-evidence-page-0001"
    source = str(root / "pages" / (title + ".md"))
    nodes: list[LogseqNode] = []
    for index in range(3 if deep else 24):
        identity = str(uuid.UUID(int=index + 1))
        content = (f"chain-{index:04d}" if deep else f"block-0001-{index:02d}"
                   + (" #runtime-evidence [[runtime-evidence-page-0002]]" if index == 0 else ""))
        parent = nodes[-1] if deep and nodes else None
        nodes.append(LogseqNode(
            uuid=identity, synthetic_id=True, content=content, clean_text=content,
            indent_level=index if deep else 0, source_path=source,
            line_start=index + (1 if deep else 3), line_end=index + (1 if deep else 3),
            parent_id=parent.uuid if parent else None,
            left_id=nodes[-1].uuid if not deep and nodes else None,
            path=[*[node.uuid for node in nodes], identity] if deep else [identity],
            outline_path=[1] * (index + 1) if deep else [index + 1],
            wikilinks=["runtime-evidence-page-0002"] if not deep and index == 0 else [],
            tags=["runtime-evidence"] if not deep and index == 0 else [],
            refs=["runtime-evidence-page-0002", "runtime-evidence"] if not deep and index == 0 else [],
        ))
        if parent is not None:
            parent.children.append(nodes[-1])
    if deep:
        raw = "".join("  " * (i + 1) + f"- chain-{i:04d}\n" for i in range(3))
    else:
        raw = "alias:: runtime-evidence-alias-0001\n\n" + "".join(
            "- " + node.content + "\n" for node in nodes
        )
    return LogseqPage(
        title=title, raw_content=raw, properties={} if deep else {"alias": "runtime-evidence-alias-0001"},
        properties_order=[] if deep else ["alias"],
        refs=[] if deep else ["runtime-evidence-page-0002", "runtime-evidence", "runtime-evidence-alias-0001"],
        created_at=111, updated_at=222, source_path=source, graph_root=str(root),
        root_nodes=nodes[:1] if deep else nodes,
    )


@contextmanager
def _changed(owner: Any, field: str, value: object) -> Iterator[None]:
    """Restore the identical field object even if the assertion under test fails."""
    storage = owner.__dict__ if field in owner.__dict__ else owner.__pydantic_private__
    original = storage[field]
    storage[field] = value
    try:
        yield
    finally:
        storage[field] = original


def _reference(page: Any) -> dict[str, Any]:
    from tests.parser_assurance.projection import project_page
    return project_page(
        page, profile="semantic_roundtrip_v1",
        identity_policy={"synthetic_uuid": "stable", "source_uuid": "absent", "relations": "direct_ids"},
    )


def _assert_reference(reference: dict[str, Any], page_row: Any, node_rows: tuple[Any, ...]) -> None:
    """Compare every canonical field, plus independently pinned supplements."""
    if set(reference) != {"profile", "snapshot_schema_version", "page"}:
        raise AssertionError("small workload semantic mismatch")
    if reference["profile"] != "semantic_roundtrip_v1" or reference["snapshot_schema_version"] != 1:
        raise AssertionError("small workload semantic mismatch")
    expected_page = dict(reference["page"])
    roots = expected_page.pop("root_nodes")
    observed_page = {
        field.name: getattr(page_row, field.name) for field in fields(page_row)
        if field.name not in {"logical_source", "raw_content_sha256", "root_uuids"}
    }
    observed_page["properties"] = {key: list(value) for key, value in page_row.properties}
    for name in ("properties_order", "refs", "namespace_chain"):
        observed_page[name] = list(observed_page[name])
    if observed_page != expected_page or page_row.root_uuids != tuple(row["uuid"] for row in roots):
        raise AssertionError("small workload semantic mismatch")
    flattened: list[dict[str, Any]] = []
    pending = list(reversed(roots))
    while pending:
        entry = pending.pop()
        flattened.append(entry)
        pending.extend(reversed(entry["children"]))
    if len(flattened) != len(node_rows):
        raise AssertionError("small workload semantic mismatch")
    for index, (expected, observed) in enumerate(zip(flattened, node_rows, strict=True)):
        actual = {field.name: getattr(observed, field.name) for field in fields(observed)
                  if field.name not in {"key", "logical_source", "line_start", "line_end", "child_uuids"}}
        actual["properties"] = {key: list(value) for key, value in observed.properties}
        for key in ("properties_order", "wikilinks", "tags", "assets", "block_refs", "refs",
                    "path", "outline_path"):
            actual[key] = list(actual[key])
        wanted = {key: value for key, value in expected.items() if key != "children"}
        offset = 1 if page_row.title == "runtime-evidence-deep" else 3
        if (actual != wanted or observed.child_uuids != tuple(row["uuid"] for row in expected["children"])
                or (observed.line_start, observed.line_end) != (index + offset, index + offset)
                or observed.key != (page_row.title, tuple(expected["outline_path"]))
                or observed.logical_source != f"pages/{page_row.title}.md"):
            raise AssertionError("small workload semantic mismatch")


def test_controlled_expected_small_graph_matches_independent_literals() -> None:
    expected = _semantics().expected_small_graph()
    assert (len(expected.pages), len(expected.nodes), len(expected.page_index),
            len(expected.source_page_index), len(expected.lower_titles),
            len(expected.node_index), len(expected.backlinks)) == (96, 3304, 191, 96, 96, 3304, 190)
    deep = expected.nodes[:1024]
    assert deep[0].uuid == "1416fd98-2dc4-5e05-8b60-d2a2cc0c7ab4"
    assert deep[-1].uuid == "7064c1af-b3b0-57aa-ab7d-239968aceb9c"
    assert expected.nodes[1024].uuid == "e0c88c00-2512-57a9-add5-3915be6b33b3"
    assert expected.nodes[-1].uuid == "7b037845-31c5-57df-a597-524e2e770325"
    assert expected.pages[0].raw_content_sha256 == "6c44ff9da0da8e80811d3e16fd58091f298bfe1e1803d34d6e045b298f37f405"
    assert expected.pages[1].raw_content_sha256 == "05002ecba0d2ffec12d0924b3ffe9dcb41a7accd1bfbc9246122400d4ed26220"
    assert expected.pages[-1].raw_content_sha256 == "1c9eed92ea30a50a2df94044ed005049eb5ae47802eb024686a33b16c39407c6"
    for index, node in enumerate(deep):
        assert (node.content, node.clean_text, node.indent_level, node.line_start, node.line_end) == (
            f"chain-{index:04d}", f"chain-{index:04d}", index, index + 1, index + 1,
        )
        assert node.outline_path == (1,) * (index + 1)
        assert node.path == tuple(item.uuid for item in deep[:index + 1])
        assert node.parent_id == (deep[index - 1].uuid if index else None)
        assert node.left_id is None
        assert node.child_uuids == ((deep[index + 1].uuid,) if index < 1023 else ())
    for page in expected.pages:
        assert page.created_at is None and page.updated_at is None and page.tab_size == 2
        assert page.namespace_chain == ()
    for node in expected.nodes:
        assert node.source_uuid is None and node.synthetic_id is True
        assert node.properties == node.properties_order == node.assets == node.block_refs == ()
        assert (node.task_status, node.task_priority, node.repeater, node.scheduled_at,
                node.deadline_at, node.created_at, node.updated_at) == (None,) * 7
    ordinary = expected.nodes[1024:]
    for index, node in enumerate(ordinary):
        page_index, block_index = divmod(index, 24)
        title = f"runtime-evidence-page-{page_index + 1:04d}"
        target = f"runtime-evidence-page-{page_index + 2:04d}" if page_index < 94 else "runtime-evidence-deep"
        content = f"block-{page_index + 1:04d}-{block_index:02d}"
        if block_index == 0:
            content += f" #runtime-evidence [[{target}]]"
        assert (node.key, node.content, node.clean_text, node.indent_level) == (
            (title, (block_index + 1,)), content, content, 0,
        )
        assert (node.line_start, node.line_end) == (block_index + 3, block_index + 3)
        assert node.wikilinks == ((target,) if block_index == 0 else ())
        assert node.tags == (("runtime-evidence",) if block_index == 0 else ())
        assert node.refs == ((target, "runtime-evidence") if block_index == 0 else ())
        assert node.parent_id is None and node.child_uuids == ()
        assert node.path == (node.uuid,)
        assert node.left_id == (ordinary[index - 1].uuid if block_index else None)
    assert all(not key.startswith("runtime-evidence-alias") for key, _ in expected.lower_titles)
    assert expected.page_index == tuple(sorted(expected.page_index))
    backlinks = dict(expected.backlinks)
    assert backlinks["runtime-evidence"] == tuple(ordinary[index].uuid for index in range(0, 2280, 24))
    assert backlinks["runtime-evidence-page-0002"] == backlinks["runtime-evidence-alias-0002"] == (
        "e0c88c00-2512-57a9-add5-3915be6b33b3",
    )
    assert "runtime-evidence-page-0001" not in backlinks
    assert "runtime-evidence-alias-0001" not in backlinks


def test_controlled_flat_mapping_covers_declared_models() -> None:
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
    from tests.test_performance_decision_workload import NODE_FIELDS, PAGE_FIELDS
    module = _semantics()
    assert tuple(field.name for field in fields(module.PageRow)) == PAGE_FIELDS
    assert tuple(field.name for field in fields(module.NodeRow)) == NODE_FIELDS
    assert set(LogseqPage.model_fields) == {
        "title", "raw_content", "properties", "properties_order", "refs", "created_at",
        "updated_at", "namespace_chain", "source_path", "graph_root", "tab_size", "root_nodes",
    }
    assert set(LogseqNode.model_fields) == {
        "uuid", "source_uuid", "synthetic_id", "content", "clean_text", "indent_level",
        "properties", "wikilinks", "tags", "assets", "block_refs", "refs", "task_status",
        "task_priority", "scheduled_at", "deadline_at", "repeater", "parent_id", "left_id",
        "path", "source_path", "line_start", "line_end", "outline_path", "properties_order",
        "created_at", "updated_at", "children",
    }


@pytest.mark.parametrize("deep", [False, True], ids=["siblings", "shallow-chain"])
def test_controlled_shallow_projection_parity(tmp_path: Path, deep: bool) -> None:
    page = _controlled_page(tmp_path, deep=deep)
    reference = _reference(page)
    row, nodes = _semantics()._observe_page_fields(
        page, graph_root=tmp_path, logical_source=f"pages/{page.title}.md", node_limit=24,
    )
    _assert_reference(reference, row, nodes)
    assert row.raw_content_sha256 == sha256(page.raw_content.encode("utf-8")).hexdigest()
    assert row.logical_source == f"pages/{page.title}.md"


@pytest.mark.parametrize("case", [
    "nested-property", "cyclic-property", "node-property", "bool-indent", "missing-range",
    "tuple-children", "tuple-roots", "outside-source", "outside-root", "path-object",
    "oversize-refs", "oversize-path", "hostile-order", "hostile-content", "bool-tab",
    "uuid-subclass", "negative-outline", "bad-synthetic", "deep-cycle", "shared-node",
])
def test_controlled_invalid_model_is_rejected_before_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    from tests.parser_assurance import invariants, projection
    from tests.test_performance_decision_workload import _Hostile, _StringSubclass
    page = _controlled_page(tmp_path, deep=case == "deep-cycle")
    node = page.root_nodes[0]
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    changes: dict[str, tuple[Any, str, object]] = {
        "nested-property": (page, "properties", {"alias": []}),
        "cyclic-property": (page, "properties", {"alias": cyclic}),
        "node-property": (node, "properties", cyclic),
        "bool-indent": (node, "indent_level", True),
        "missing-range": (node, "line_start", None),
        "tuple-children": (node, "children", ()),
        "tuple-roots": (page, "root_nodes", tuple(page.root_nodes)),
        "outside-source": (page, "source_path", str(tmp_path.parent / "outside.md")),
        "outside-root": (page, "graph_root", str(tmp_path.parent)),
        "path-object": (node, "source_path", Path(node.source_path)),
        "oversize-refs": (page, "refs", ["x"] * 4),
        "oversize-path": (node, "path", [node.uuid] * 1025),
        "hostile-order": (page, "properties_order", [_Hostile()]),
        "hostile-content": (node, "content", _Hostile()),
        "bool-tab": (page, "tab_size", True),
        "uuid-subclass": (node, "uuid", _StringSubclass(node.uuid)),
        "negative-outline": (node, "outline_path", [-1]),
        "bad-synthetic": (node, "synthetic_id", 1),
        "deep-cycle": (node.children[0].children[0] if case == "deep-cycle" else node, "children", [node]),
        "shared-node": (page, "root_nodes", [node, node, *page.root_nodes[2:]]),
    }
    calls: list[str] = []
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append("recursive-or-invariant-helper")
        raise AssertionError("helper reached before bounded validation")
    monkeypatch.setattr(invariants, "assert_tree_invariants", forbidden)
    monkeypatch.setattr(projection, "_canonical_value", forbidden)
    owner, name, bad = changes[case]
    with _changed(owner, name, bad):
        with pytest.raises(AssertionError, match="^small workload structure mismatch$"):
            _semantics()._observe_page_fields(
                page, graph_root=tmp_path, logical_source=f"pages/{page.title}.md", node_limit=24,
            )
    assert calls == []


@pytest.mark.parametrize("limit", [True, 0, 25, 1025, "24"])
def test_controlled_page_limit_is_closed(tmp_path: Path, limit: object) -> None:
    page = _controlled_page(tmp_path)
    with pytest.raises(AssertionError, match="^small workload structure mismatch$"):
        _semantics()._observe_page_fields(
            page, graph_root=tmp_path, logical_source="pages/runtime-evidence-page-0001.md",
            node_limit=limit,
        )


@pytest.mark.parametrize(("owner_name", "field", "bad"), [
    ("node", "content", "changed"), ("node", "clean_text", "changed"),
    ("node", "tags", ["different"]), ("node", "wikilinks", ["different"]),
    ("node", "refs", ["different"]), ("node", "properties_order", ["different"]),
    ("node", "parent_id", "0" * 36), ("node", "left_id", "0" * 36),
    ("node", "path", ["0" * 36]), ("node", "line_end", 4),
    ("node", "source_uuid", "0" * 36), ("node", "synthetic_id", False),
    ("page", "refs", ["different"]), ("page", "properties_order", []),
])
def test_controlled_per_page_semantic_mutations_are_rejected(
    tmp_path: Path, owner_name: str, field: str, bad: object,
) -> None:
    page = _controlled_page(tmp_path)
    reference = _reference(page)
    module = _semantics()
    owner = page if owner_name == "page" else page.root_nodes[0]
    with _changed(owner, field, bad):
        with pytest.raises(AssertionError):
            rows = module._observe_page_fields(
                page, graph_root=tmp_path, logical_source="pages/runtime-evidence-page-0001.md", node_limit=24,
            )
            _assert_reference(reference, *rows)
    _assert_reference(reference, *module._observe_page_fields(
        page, graph_root=tmp_path, logical_source="pages/runtime-evidence-page-0001.md", node_limit=24,
    ))


def test_controlled_mutation_restoration_survives_a_failing_assertion(tmp_path: Path) -> None:
    page = _controlled_page(tmp_path)
    original = page.refs
    with pytest.raises(AssertionError, match="injected failure"):
        with _changed(page, "refs", ["different"]):
            raise AssertionError("injected failure")
    assert page.refs is original


@dataclass(frozen=True)
class _NativeSmallGraphs:
    root: Path
    first: Any
    second: Any
    counts: dict[str, int]


@pytest.fixture(scope="module")
def native_small_graphs(
    tmp_path_factory: pytest.TempPathFactory,
    record_testsuite_property: Callable[[str, object], None],
) -> Iterator[_NativeSmallGraphs]:
    """Two real fresh loads, once per fixture-using invocation, never a timing loop."""
    from logseq_matryca_parser.graph import LogseqGraph
    from tests.performance import decision_vault, synthetic_vault

    counts = {"build": 0, "materialize": 0, "native_load": 0}
    build = decision_vault.build_decision_vault
    materialize = synthetic_vault.SyntheticVault.materialize
    native_load: Any = vars(LogseqGraph)["load_directory"].__func__
    repository = Path(__file__).resolve().parents[1]
    assert native_load.__code__.co_filename == str(repository / "src/logseq_matryca_parser/graph.py")

    def counted_build(profile_id: str) -> Any:
        assert profile_id == "vault-small-96-v1"
        counts["build"] += 1
        return build(profile_id)

    def counted_materialize(vault: Any, destination: Path) -> Path:
        counts["materialize"] += 1
        return materialize(vault, destination)

    def counted_native_load(cls: type[Any], path: Path, **options: bool) -> Any:
        assert cls is LogseqGraph
        assert options == {"strict_refs": False, "strict_title_collisions": False}
        counts["native_load"] += 1
        assert counts["native_load"] <= 2
        return native_load(cls, path, **options)

    with pytest.MonkeyPatch.context() as scoped:
        scoped.setattr(decision_vault, "build_decision_vault", counted_build)
        scoped.setattr(synthetic_vault.SyntheticVault, "materialize", counted_materialize)
        scoped.setattr(LogseqGraph, "load_directory", classmethod(counted_native_load))
        try:
            vault = decision_vault.build_decision_vault("vault-small-96-v1")
            assert (len(vault.files), vault.page_count, vault.deep_chain_depth,
                    vault.total_source_bytes) == (96, 96, 1024, 1107557)
            assert vault.source_sha256 == "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583"
            destination = tmp_path_factory.mktemp("decision-small") / "vault"
            assert not destination.exists()
            root = vault.materialize(destination)
            first = LogseqGraph.load_directory(root, strict_refs=False, strict_title_collisions=False)
            _semantics().assert_small_graph_semantics(first, graph_root=root)
            second = LogseqGraph.load_directory(root, strict_refs=False, strict_title_collisions=False)
            _semantics().assert_small_graph_semantics(second, graph_root=root)
            assert counts == {"build": 1, "materialize": 1, "native_load": 2}
            yield _NativeSmallGraphs(root, first, second, counts)
            assert counts == {"build": 1, "materialize": 1, "native_load": 2}
        finally:
            for name, count in counts.items():
                record_testsuite_property("decision_small_" + name + "_calls", count)


def test_native_small_graph_matches_independent_expectations(native_small_graphs: _NativeSmallGraphs) -> None:
    module = _semantics()
    for graph in (native_small_graphs.first, native_small_graphs.second):
        module.assert_small_graph_semantics(graph, graph_root=native_small_graphs.root)


def test_two_fresh_loads_preserve_same_source_uuids(native_small_graphs: _NativeSmallGraphs) -> None:
    module = _semantics()
    first, second = (module.observe_small_graph(graph, graph_root=native_small_graphs.root)
                     for graph in (native_small_graphs.first, native_small_graphs.second))
    assert tuple((node.key, node.uuid) for node in first.nodes) == tuple(
        (node.key, node.uuid) for node in second.nodes
    )
    assert native_small_graphs.first is not native_small_graphs.second
    assert native_small_graphs.counts == {"build": 1, "materialize": 1, "native_load": 2}


@contextmanager
def _native_mutation(
    data: _NativeSmallGraphs, changes: list[tuple[Any, str, object]],
) -> Iterator[None]:
    """Always restore and independently recheck, even when the rejection test fails."""
    try:
        with ExitStack() as stack:
            for owner, name, value in changes:
                stack.enter_context(_changed(owner, name, value))
            yield
    finally:
        _semantics().assert_small_graph_semantics(data.first, graph_root=data.root)


@pytest.mark.parametrize("field", ["content", "source-range"])
def test_deepest_node_and_ranges_are_checked(native_small_graphs: _NativeSmallGraphs, field: str) -> None:
    graph = native_small_graphs.first
    leaf = list(graph._node_registry.values())[1023]
    assert leaf.content == "chain-1023" and leaf.line_start == leaf.line_end == 1024
    changes: list[tuple[Any, str, object]] = ([(leaf, "content", "chain-xxxx")] if field == "content" else
               [(leaf, "line_start", 1023), (leaf, "line_end", 1023)])
    with _native_mutation(native_small_graphs, changes):
        with pytest.raises(AssertionError, match="^small workload semantic mismatch$"):
            _semantics().assert_small_graph_semantics(graph, graph_root=native_small_graphs.root)


@pytest.mark.parametrize("case", [
    "alias-target", "missing-page", "extra-page", "source-key", "page-refs",
    "registry-ghost", "registry-order", "alias-key", "backlink-order", "backlink-source",
    "lower-title", "duplicate-uuid", "shared-node", "deep-cycle", "late-nested-property",
    "cross-page-shared", "node-content", "node-tags", "node-links", "page-alias",
])
def test_native_mutations_are_rejected(
    native_small_graphs: _NativeSmallGraphs, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    graph = native_small_graphs.first
    first_page = graph.pages["runtime-evidence-page-0001"]
    other_page = graph.pages["runtime-evidence-page-0002"]
    last_page = graph.pages["runtime-evidence-page-0095"]
    node = first_page.root_nodes[0]
    registry = list(graph._node_registry.items())
    leaf = registry[1023][1]
    changed_pages = dict(graph.pages)
    changed_sources = dict(graph._source_pages)
    changed_registry = dict(registry)
    changed_backlinks = dict(graph._backlink_registry)
    changed_lower = dict(graph._lower_title_map)
    changes: list[tuple[Any, str, object]]
    if case == "alias-target":
        changed_pages["runtime-evidence-alias-0001"] = other_page
        changes = [(graph, "pages", changed_pages)]
    elif case == "missing-page":
        del changed_pages["runtime-evidence-page-0001"]
        changes = [(graph, "pages", changed_pages)]
    elif case == "extra-page":
        changed_pages["extra"] = first_page
        changes = [(graph, "pages", changed_pages)]
    elif case == "source-key":
        del changed_sources[first_page.source_path]
        changed_sources[str(native_small_graphs.root / "elsewhere.md")] = first_page
        changes = [(graph, "_source_pages", changed_sources)]
    elif case == "page-refs":
        changes = [(first_page, "refs", list(reversed(first_page.refs)))]
    elif case == "registry-ghost":
        changed_registry[node.uuid] = node.model_copy()
        changes = [(graph, "_node_registry", changed_registry)]
    elif case == "registry-order":
        changes = [(graph, "_node_registry", dict([*registry[1:], registry[0]]))]
    elif case == "alias-key":
        del changed_pages["runtime-evidence-alias-0001"]
        changed_pages["unexpected"] = first_page
        changes = [(graph, "pages", changed_pages)]
    elif case == "backlink-order":
        changed_backlinks["runtime-evidence"] = list(reversed(changed_backlinks["runtime-evidence"]))
        changes = [(graph, "_backlink_registry", changed_backlinks)]
    elif case == "backlink-source":
        changed_backlinks["runtime-evidence-deep"] = [node.uuid]
        changes = [(graph, "_backlink_registry", changed_backlinks)]
    elif case == "lower-title":
        changed_lower[first_page.title.lower()] = other_page.title
        changes = [(graph, "_lower_title_map", changed_lower)]
    elif case == "duplicate-uuid":
        changes = [(first_page.root_nodes[1], "uuid", node.uuid)]
    elif case == "shared-node":
        changes = [(first_page, "root_nodes", [node, node, *first_page.root_nodes[2:]])]
    elif case == "deep-cycle":
        changes = [(leaf, "children", [graph.pages["runtime-evidence-deep"].root_nodes[0]])]
    elif case == "late-nested-property":
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        changes = [(last_page, "properties", {"alias": cyclic})]
    elif case == "cross-page-shared":
        changes = [(last_page, "root_nodes", first_page.root_nodes)]
    elif case == "node-content":
        changes = [(node, "content", node.content.replace("block", "other", 1))]
    elif case == "node-tags":
        changes = [(node, "tags", ["another-evidence"])]
    elif case == "node-links":
        changes = [(node, "wikilinks", ["runtime-evidence-page-0003"])]
    else:
        assert case == "page-alias"
        changes = [(first_page, "properties", {"alias": "runtime-evidence-alias-0002"})]
    calls: list[str] = []
    with _native_mutation(native_small_graphs, changes):
        with monkeypatch.context() as scoped:
            if case == "late-nested-property":
                from tests.parser_assurance import invariants
                def forbidden(*args: Any, **kwargs: Any) -> Any:
                    calls.append("invariants")
                    raise AssertionError("legacy helper reached before full validation")
                scoped.setattr(invariants, "assert_tree_invariants", forbidden)
            with pytest.raises(AssertionError, match="^small workload (structure|semantic) mismatch$"):
                _semantics().assert_small_graph_semantics(graph, graph_root=native_small_graphs.root)
    assert calls == []


def test_native_mutation_restoration_survives_failure(native_small_graphs: _NativeSmallGraphs) -> None:
    graph = native_small_graphs.first
    original = graph.pages
    with pytest.raises(AssertionError, match="injected native failure"):
        with _native_mutation(native_small_graphs, [(graph, "pages", {})]):
            raise AssertionError("injected native failure")
    assert graph.pages is original
