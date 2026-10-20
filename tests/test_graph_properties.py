"""Bounded property checks for graph identity across public constructors."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from string import ascii_lowercase

import pytest
from hypothesis import given, note, settings
from hypothesis import strategies as st

from logseq_matryca_parser import LogseqGraph, SnapshotPage
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from tests.parser_assurance.projection import IdentityPolicy, project_page

_ROUNDTRIP_IDENTITY_POLICY = IdentityPolicy(
    synthetic_uuid="recomputed",
    source_uuid="absent",
    relations="outline_paths",
)
_MAX_FILE_BYTES = 1 * 1024
_MAX_TOTAL_BYTES = 4 * 1024
_REPLAY_SCHEMA_VERSION = 1
_RECIPE_BASELINE_REVISION = "3070a8f1d788a295849ad34f263f63ef83b464ab"
_REPLAY_BOUNDS = {
    "page_count": [2, 4],
    "alias_ascii_letters": [1, 8],
    "blocks_per_page": [1, 3],
    "ring_link_occurrences": [1, 2],
    "file_bytes": _MAX_FILE_BYTES,
    "aggregate_bytes": _MAX_TOTAL_BYTES,
    "outline_depth": 0,
    "hypothesis": {
        "max_examples": 40,
        "derandomize": True,
        "database": "disabled",
        "deadline_ms": None,
        "print_blob": True,
        "suppressed_healthchecks": [],
    },
}
_REPLAY_FIELDS = {
    "schema_version",
    "recipe",
    "recipe_baseline_revision",
    "test_file_sha256",
    "model",
    "bounds",
    "source_digest",
}


@dataclass(frozen=True)
class PageModel:
    """Independent literal description of one finite generated Markdown page."""

    alias: str
    block_count: int
    use_alias_for_ring_link: bool
    duplicate_ring_link: bool


@dataclass(frozen=True)
class VaultModel:
    """Small ring of canonical pages and unique aliases."""

    pages: tuple[PageModel, ...]

    @property
    def titles(self) -> tuple[str, ...]:
        return tuple(f"Page{index}" for index in range(len(self.pages)))


def _vault_model_strategy() -> st.SearchStrategy[VaultModel]:
    @st.composite
    def build(draw: st.DrawFn) -> VaultModel:
        page_count = draw(st.integers(min_value=2, max_value=4))
        aliases = draw(
            st.lists(
                st.text(alphabet=ascii_lowercase, min_size=1, max_size=8),
                min_size=page_count,
                max_size=page_count,
                unique_by=str.casefold,
            )
        )
        pages = tuple(
            PageModel(
                alias=f"Alias{aliases[index]}",
                block_count=draw(st.integers(min_value=1, max_value=3)),
                use_alias_for_ring_link=draw(st.booleans()),
                duplicate_ring_link=draw(st.booleans()),
            )
            for index in range(page_count)
        )
        return VaultModel(pages)

    return build()


def _render_vault(model: VaultModel) -> dict[str, str]:
    sources: dict[str, str] = {}
    for index, page in enumerate(model.pages):
        next_index = (index + 1) % len(model.pages)
        target = (
            model.pages[next_index].alias
            if page.use_alias_for_ring_link
            else model.titles[next_index]
        )
        lines = [f"alias:: {page.alias}", ""]
        for block_index in range(page.block_count):
            content = f"Block{index}_{block_index}"
            if block_index == 0:
                content += f" [[{target}]]"
                if page.duplicate_ring_link:
                    content += f" [[{target}]]"
            lines.append(f"- {content}")
        sources[f"pages/{model.titles[index]}.md"] = "\n".join(lines) + "\n"
    return sources


def _source_digest(sources: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for logical_path, source in sorted(sources.items()):
        path_bytes = logical_path.encode("ascii")
        source_bytes = source.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(4, "big"))
        digest.update(path_bytes)
        digest.update(len(source_bytes).to_bytes(8, "big"))
        digest.update(source_bytes)
    return digest.hexdigest()


def _test_file_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _model_payload(model: VaultModel) -> dict[str, object]:
    return {
        "pages": [
            {
                "alias": page.alias,
                "block_count": page.block_count,
                "use_alias_for_ring_link": page.use_alias_for_ring_link,
                "duplicate_ring_link": page.duplicate_ring_link,
            }
            for page in model.pages
        ]
    }


def _replay_metadata(model: VaultModel) -> str:
    sources = _render_vault(model)
    payload = {
        "schema_version": _REPLAY_SCHEMA_VERSION,
        "recipe": "ascii-alias-flat-page-ring-v1",
        "recipe_baseline_revision": _RECIPE_BASELINE_REVISION,
        "test_file_sha256": _test_file_digest(),
        "model": _model_payload(model),
        "bounds": _REPLAY_BOUNDS,
        "source_digest": _source_digest(sources),
    }
    return json.dumps(payload, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _load_replay_metadata(serialized: str) -> VaultModel:
    payload = json.loads(serialized, parse_constant=_reject_json_constant)
    if not isinstance(payload, dict) or set(payload) != _REPLAY_FIELDS:
        raise ValueError("replay metadata fields do not match schema")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("unsupported replay metadata schema")
    if payload["recipe"] != "ascii-alias-flat-page-ring-v1":
        raise ValueError("unsupported replay recipe")
    if payload["recipe_baseline_revision"] != _RECIPE_BASELINE_REVISION:
        raise ValueError("unexpected recipe baseline revision")
    if payload["bounds"] != _REPLAY_BOUNDS:
        raise ValueError("replay bounds differ from the approved finite recipe")
    if not isinstance(payload["test_file_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", payload["test_file_sha256"]
    ):
        raise ValueError("invalid test implementation digest")
    if not isinstance(payload["source_digest"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", payload["source_digest"]
    ):
        raise ValueError("invalid generated source digest")

    model_payload = payload["model"]
    if not isinstance(model_payload, dict) or set(model_payload) != {"pages"}:
        raise ValueError("invalid model fields")
    pages_payload = model_payload["pages"]
    if not isinstance(pages_payload, list) or not 2 <= len(pages_payload) <= 4:
        raise ValueError("page count is outside replay bounds")

    pages: list[PageModel] = []
    aliases: set[str] = set()
    expected_page_fields = {
        "alias",
        "block_count",
        "use_alias_for_ring_link",
        "duplicate_ring_link",
    }
    for page_payload in pages_payload:
        if not isinstance(page_payload, dict) or set(page_payload) != expected_page_fields:
            raise ValueError("invalid page model fields")
        alias = page_payload["alias"]
        block_count = page_payload["block_count"]
        use_alias = page_payload["use_alias_for_ring_link"]
        duplicate = page_payload["duplicate_ring_link"]
        if not isinstance(alias, str) or not re.fullmatch(r"Alias[a-z]{1,8}", alias):
            raise ValueError("alias is outside finite ASCII recipe")
        if alias.casefold() in aliases:
            raise ValueError("aliases must be unique")
        aliases.add(alias.casefold())
        if type(block_count) is not int or not 1 <= block_count <= 3:
            raise ValueError("block count is outside replay bounds")
        if type(use_alias) is not bool or type(duplicate) is not bool:
            raise ValueError("recipe switches must be booleans")
        pages.append(PageModel(alias, block_count, use_alias, duplicate))

    model = VaultModel(tuple(pages))
    if _source_digest(_render_vault(model)) != payload["source_digest"]:
        raise ValueError("generated source digest does not match replay model")
    return model


def _write_vault(graph_root: Path, sources: dict[str, str]) -> None:
    for logical_path, source in sources.items():
        encoded = source.encode("utf-8")
        assert len(encoded) <= _MAX_FILE_BYTES
        path = graph_root / logical_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
    assert sum(len(source.encode("utf-8")) for source in sources.values()) <= _MAX_TOTAL_BYTES


def _attached_slots(
    graph: LogseqGraph,
) -> tuple[dict[tuple[str, tuple[int, ...]], LogseqNode], dict[int, tuple[str, tuple[int, ...]]]]:
    by_slot: dict[tuple[str, tuple[int, ...]], LogseqNode] = {}
    by_identity: dict[int, tuple[str, tuple[int, ...]]] = {}

    def visit(page: LogseqPage, node: LogseqNode) -> None:
        slot = (page.title, tuple(node.outline_path))
        assert slot not in by_slot, f"attached graph slot must be unique: {slot!r}"
        by_slot[slot] = node
        by_identity[id(node)] = slot
        for child in node.children:
            visit(page, child)

    for page in graph.iter_canonical_pages():
        for root in page.root_nodes:
            visit(page, root)
    return by_slot, by_identity


def _assert_matches_model(
    graph: LogseqGraph,
    model: VaultModel,
    graph_root: Path,
    *,
    backlink_lookup: Callable[[str], list[LogseqNode]] | None = None,
) -> None:
    titles = model.titles
    canonical_pages = list(graph.iter_canonical_pages())
    assert len(canonical_pages) == len(titles)
    assert [page.title for page in canonical_pages] == list(titles)
    assert set(graph.pages) == {
        name for page in model.pages for name in (page.alias,)
    } | set(titles)

    slots_to_nodes, identities_to_slots = _attached_slots(graph)
    canonical_by_title = {page.title: page for page in canonical_pages}
    for index, page_model in enumerate(model.pages):
        title = titles[index]
        canonical = canonical_by_title[title]
        assert canonical.source_path == str(
            (graph_root / "pages" / f"{title}.md").resolve()
        )
        assert graph.pages[title] is canonical
        assert graph.pages[page_model.alias] is canonical, (
            f"alias route for {page_model.alias!r} must target {title!r} by identity"
        )
        roots = canonical.root_nodes
        assert len(roots) == page_model.block_count, (
            f"root count for {title!r} must match independent model"
        )
        expected_root_slots = [(root_index,) for root_index in range(1, page_model.block_count + 1)]
        assert [tuple(node.outline_path) for node in roots] == expected_root_slots, (
            f"ordered root slots for {title!r} must match independent model"
        )
        assert all(not node.children for node in roots), "flat recipe pages must have no children"

    lookup = backlink_lookup or graph.get_backlinks
    for target_index, page_model in enumerate(model.pages):
        expected_source = (titles[(target_index - 1) % len(titles)], (1,))
        expected_node = slots_to_nodes.get(expected_source)
        assert expected_node is not None, f"model-selected source slot must be attached: {expected_source!r}"
        for target in (titles[target_index], page_model.alias):
            observed_nodes = lookup(target)
            observed_slots: list[tuple[str, tuple[int, ...]]] = []
            for node in observed_nodes:
                slot = identities_to_slots.get(id(node))
                assert slot is not None and slots_to_nodes.get(slot) is node, (
                    "backlink must be the attached graph-owned node for its slot"
                )
                assert node is expected_node or slot != expected_source, (
                    "backlink source must be the model-selected attached object"
                )
                observed_slots.append(slot)
            assert len(observed_slots) == len(set(observed_slots)), (
                "backlinks must deduplicate source nodes, not link occurrences"
            )
            assert Counter(observed_slots) == Counter([expected_source]), (
                f"backlink slots for {target!r} must match independent model"
            )


@settings(
    max_examples=40,
    derandomize=True,
    deadline=None,
    database=None,
    print_blob=True,
)
@given(model=_vault_model_strategy())
def test_generated_vault_graph_constructors_match_independent_model_and_each_other(
    tmp_path_factory: pytest.TempPathFactory,
    model: VaultModel,
) -> None:
    sources = _render_vault(model)
    replay_metadata = _replay_metadata(model)
    note(replay_metadata)
    with tempfile.TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as temporary_root:
        graph_root = Path(temporary_root) / "vault"
        _write_vault(graph_root, sources)
        graph_root = graph_root.resolve()

        disk_graph = LogseqGraph.load_directory(graph_root)
        reversed_snapshots = [
            SnapshotPage(logical_path=logical_path, text=sources[logical_path])
            for logical_path in reversed(list(sources))
        ]
        sequence_graph = LogseqGraph.from_snapshot_pages(graph_root, reversed_snapshots)
        reordered_mapping = {
            logical_path: sources[logical_path] for logical_path in reversed(list(sources))
        }
        mapping_graph = LogseqGraph.from_snapshot_pages(graph_root, reordered_mapping)

        # Check every constructor independently before comparing their projections.
        for graph in (disk_graph, sequence_graph, mapping_graph):
            _assert_matches_model(graph, model, graph_root)

        for title in model.titles:
            disk_page = disk_graph.get_page(title)
            sequence_page = sequence_graph.get_page(title)
            mapping_page = mapping_graph.get_page(title)
            assert disk_page is not None
            assert sequence_page is not None
            assert mapping_page is not None
            disk_projection = project_page(
                disk_page,
                profile="semantic_roundtrip_v1",
                identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
            )
            assert disk_projection == project_page(
                sequence_page,
                profile="semantic_roundtrip_v1",
                identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
            )
            assert disk_projection == project_page(
                mapping_page,
                profile="semantic_roundtrip_v1",
                identity_policy=_ROUNDTRIP_IDENTITY_POLICY,
            )


def _fixed_graph(tmp_path: Path) -> tuple[LogseqGraph, VaultModel, Path]:
    model = VaultModel(
        pages=(
            PageModel("Aliaszero", 2, False, True),
            PageModel("Aliasone", 1, True, False),
        )
    )
    graph_root = tmp_path / "oracle-vault"
    _write_vault(graph_root, _render_vault(model))
    graph_root = graph_root.resolve()
    return LogseqGraph.load_directory(graph_root), model, graph_root


def test_replay_metadata_reconstructs_model_and_digest_without_source_or_paths() -> None:
    model = VaultModel(
        pages=(
            PageModel("Aliaszero", 2, False, True),
            PageModel("Aliasone", 1, True, False),
        )
    )
    serialized = _replay_metadata(model)
    payload = json.loads(serialized)
    sources = _render_vault(model)

    assert _load_replay_metadata(serialized) == model
    assert payload["recipe_baseline_revision"] == _RECIPE_BASELINE_REVISION
    assert re.fullmatch(r"[0-9a-f]{64}", payload["test_file_sha256"])
    assert payload["source_digest"] == _source_digest(sources)
    assert payload["source_digest"] == _source_digest(dict(reversed(list(sources.items()))))
    assert all(source not in serialized for source in sources.values())
    assert "pages/" not in serialized


def test_replay_metadata_rejects_unknown_fields() -> None:
    payload = json.loads(_replay_metadata(_fixed_graph_model()))
    payload["unexpected"] = "value"

    with pytest.raises(ValueError, match="fields do not match schema"):
        _load_replay_metadata(json.dumps(payload))


def test_replay_metadata_rejects_nonfinite_alias_text() -> None:
    payload = json.loads(_replay_metadata(_fixed_graph_model()))
    payload["model"]["pages"][0]["alias"] = "Aliasx\n- injected"

    with pytest.raises(ValueError, match="alias is outside finite ASCII recipe"):
        _load_replay_metadata(json.dumps(payload))


def test_replay_metadata_rejects_expanded_bounds() -> None:
    payload = json.loads(_replay_metadata(_fixed_graph_model()))
    payload["bounds"]["page_count"][1] = 5

    with pytest.raises(ValueError, match="bounds differ"):
        _load_replay_metadata(json.dumps(payload))


def _fixed_graph_model() -> VaultModel:
    return VaultModel(
        pages=(
            PageModel("Aliaszero", 2, False, True),
            PageModel("Aliasone", 1, True, False),
        )
    )


def test_graph_oracle_rejects_alias_routed_to_another_legitimate_page(tmp_path: Path) -> None:
    graph, model, graph_root = _fixed_graph(tmp_path)
    _assert_matches_model(graph, model, graph_root)
    graph.pages[model.pages[0].alias] = graph.pages[model.titles[1]]

    with pytest.raises(AssertionError, match="alias route"):
        _assert_matches_model(graph, model, graph_root)


@pytest.mark.parametrize("corruption", ["swapped", "duplicate", "missing", "extra"])
def test_graph_oracle_rejects_backlink_source_slot_corruption(
    tmp_path: Path,
    corruption: str,
) -> None:
    graph, model, graph_root = _fixed_graph(tmp_path)
    _assert_matches_model(graph, model, graph_root)
    target_key = model.titles[1].lower()
    original_sources = list(dict.fromkeys(graph._backlink_registry[target_key]))
    assert len(original_sources) == 1

    if corruption == "swapped":
        graph._backlink_registry[target_key] = [graph.pages[model.titles[1]].root_nodes[0].uuid]
        lookup = graph.get_backlinks
    elif corruption == "missing":
        graph._backlink_registry[target_key] = []
        lookup = graph.get_backlinks
    elif corruption == "extra":
        graph._backlink_registry[target_key] = [
            *original_sources,
            graph.pages[model.titles[1]].root_nodes[0].uuid,
        ]
        lookup = graph.get_backlinks
    else:
        original_lookup = graph.get_backlinks
        expected_source_node = graph.pages[model.titles[0]].root_nodes[0]

        def lookup(target: str) -> list[LogseqNode]:
            result = original_lookup(target)
            if target.casefold() in {model.titles[1].casefold(), model.pages[1].alias.casefold()}:
                return [*result, expected_source_node]
            return result

    expected_message = (
        "deduplicate source nodes" if corruption == "duplicate" else "backlink slots"
    )
    with pytest.raises(AssertionError, match=expected_message):
        _assert_matches_model(graph, model, graph_root, backlink_lookup=lookup)


def test_graph_oracle_rejects_duplicate_page_qualified_outline_slot(tmp_path: Path) -> None:
    graph, model, graph_root = _fixed_graph(tmp_path)
    _assert_matches_model(graph, model, graph_root)
    page = graph.pages[model.titles[0]]
    duplicate_slot_node = page.root_nodes[1].model_copy(update={"outline_path": [1]})
    corrupted_page = page.model_copy(
        update={"root_nodes": [page.root_nodes[0], duplicate_slot_node]}
    )
    graph.pages[model.titles[0]] = corrupted_page
    graph.pages[model.pages[0].alias] = corrupted_page

    with pytest.raises(AssertionError, match="attached graph slot must be unique"):
        _assert_matches_model(graph, model, graph_root)
