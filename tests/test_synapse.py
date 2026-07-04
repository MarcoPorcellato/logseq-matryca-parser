from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from logseq_matryca_parser.graph import LogseqGraph
from logseq_matryca_parser.logos_core import LogseqNode
from logseq_matryca_parser.synapse import (
    SynapseAdapter,
    _strip_markdown_for_embedding,
    build_synapse_metadata,
)


class FakeDocument:
    def __init__(self, page_content: str, metadata: dict[str, object]) -> None:
        self.page_content = page_content
        self.metadata = metadata


@dataclass
class FakeRelatedNodeInfo:
    node_id: str


@dataclass
class FakeTextNode:
    id_: str
    text: str
    metadata: dict[str, object]
    relationships: dict[object, object] = field(default_factory=dict)


def build_ast() -> list[LogseqNode]:
    child = LogseqNode(
        uuid="child-1",
        content="Child content",
        clean_text="Child clean",
        indent_level=1,
        parent_id="root-1",
        source_uuid="native-child-uuid",
        refs=["[[ref-child]]"],
        path=["Root", "Child"],
        left_id="left-child",
        task_status="TODO",
        task_priority="A",
        scheduled_at=1_700_000_000,
        deadline_at=1_800_000_000,
        repeater="+1w",
        created_at=111,
    )
    root = LogseqNode(
        uuid="root-1",
        content="Root content",
        clean_text="Root clean",
        indent_level=0,
        refs=["[[ref-root]]"],
        path=["Root"],
        left_id="left-root",
        created_at=100,
        properties={"topic": "alpha"},
        children=[child],
    )
    return [root]


def test_to_langchain_documents_raises_when_dependency_missing() -> None:
    with patch("logseq_matryca_parser.synapse.Document", None):
        with pytest.raises(ImportError, match="LangChain"):
            SynapseAdapter.to_langchain_documents(build_ast(), source_name="test.md")


def test_to_langchain_documents_uses_visitor_and_graph_metadata() -> None:
    with patch("logseq_matryca_parser.synapse.Document", FakeDocument):
        docs = SynapseAdapter.to_langchain_documents(build_ast(), source_name="graph.md")

    assert len(docs) == 2
    root_doc = docs[0]
    child_doc = docs[1]

    assert root_doc.page_content == "Root clean"
    assert root_doc.metadata["source"] == "graph.md"
    assert root_doc.metadata["path"] == "Root"
    assert root_doc.metadata["left_id"] == "left-root"
    assert root_doc.metadata["refs"] == "[[ref-root]]"
    assert root_doc.metadata["created_at"] == 100
    assert root_doc.metadata["topic"] == "alpha"

    assert child_doc.metadata["parent_id"] == "root-1"
    assert child_doc.metadata["task_status"] == "TODO"
    assert child_doc.metadata["task_priority"] == "A"
    assert child_doc.metadata["scheduled_at"] == 1_700_000_000
    assert child_doc.metadata["deadline_at"] == 1_800_000_000
    assert child_doc.metadata["source_uuid"] == "native-child-uuid"
    assert child_doc.metadata["repeater"] == "+1w"
    assert child_doc.metadata["path"] == "Root > Child"


def test_to_llamaindex_nodes_raises_when_dependency_missing() -> None:
    with (
        patch("logseq_matryca_parser.synapse.TextNode", None),
        patch("logseq_matryca_parser.synapse.NodeRelationship", None),
        patch("logseq_matryca_parser.synapse.RelatedNodeInfo", None),
    ):
        with pytest.raises(ImportError, match="LlamaIndex"):
            SynapseAdapter.to_llamaindex_nodes(build_ast())


def test_to_llamaindex_nodes_injects_parent_child_relationships() -> None:
    fake_relationship = SimpleNamespace(
        PARENT="PARENT",
        CHILD="CHILD",
        SOURCE="SOURCE",
        NEXT="NEXT",
        PREVIOUS="PREVIOUS",
    )
    page_source_id = "page-source-uuid"
    with (
        patch("logseq_matryca_parser.synapse.TextNode", FakeTextNode),
        patch("logseq_matryca_parser.synapse.NodeRelationship", fake_relationship),
        patch("logseq_matryca_parser.synapse.RelatedNodeInfo", FakeRelatedNodeInfo),
    ):
        nodes = SynapseAdapter.to_llamaindex_nodes(
            build_ast(),
            page_title="graph.md",
            page_source_id=page_source_id,
        )

    assert len(nodes) == 2
    root_node = nodes[0]
    child_node = nodes[1]

    assert root_node.relationships["SOURCE"].node_id == page_source_id
    assert child_node.relationships["SOURCE"].node_id == page_source_id
    assert child_node.relationships["PARENT"].node_id == "root-1"
    assert root_node.relationships["CHILD"][0].node_id == "child-1"
    assert root_node.metadata["path"] == "Root"
    assert child_node.metadata["task_status"] == "TODO"
    assert child_node.metadata["task_priority"] == "A"


def test_to_llamaindex_nodes_assigns_distinct_source_per_page() -> None:
    """Multi-page root lists receive independent LlamaIndex ``SOURCE`` ids (BUG-018)."""
    fake_relationship = SimpleNamespace(
        PARENT="PARENT",
        CHILD="CHILD",
        SOURCE="SOURCE",
        NEXT="NEXT",
        PREVIOUS="PREVIOUS",
    )
    root_a = LogseqNode(
        uuid="root-a",
        content="Page A",
        clean_text="Page A",
        indent_level=0,
        source_path="/vault/pages/A.md",
    )
    root_b = LogseqNode(
        uuid="root-b",
        content="Page B",
        clean_text="Page B",
        indent_level=0,
        source_path="/vault/pages/B.md",
    )
    with (
        patch("logseq_matryca_parser.synapse.TextNode", FakeTextNode),
        patch("logseq_matryca_parser.synapse.NodeRelationship", fake_relationship),
        patch("logseq_matryca_parser.synapse.RelatedNodeInfo", FakeRelatedNodeInfo),
    ):
        nodes = SynapseAdapter.to_llamaindex_nodes([root_a, root_b])

    source_ids = {nodes[0].relationships["SOURCE"].node_id, nodes[1].relationships["SOURCE"].node_id}
    assert len(source_ids) == 2


def test_to_llamaindex_nodes_wires_sibling_next_and_previous() -> None:
    fake_relationship = SimpleNamespace(
        PARENT="PARENT",
        CHILD="CHILD",
        SOURCE="SOURCE",
        NEXT="NEXT",
        PREVIOUS="PREVIOUS",
    )
    first = LogseqNode(
        uuid="sibling-a",
        content="First",
        clean_text="First",
        indent_level=1,
        parent_id="root-1",
    )
    second = LogseqNode(
        uuid="sibling-b",
        content="Second",
        clean_text="Second",
        indent_level=1,
        parent_id="root-1",
        left_id="sibling-a",
    )
    root = LogseqNode(
        uuid="root-1",
        content="Root",
        clean_text="Root",
        indent_level=0,
        children=[first, second],
    )
    with (
        patch("logseq_matryca_parser.synapse.TextNode", FakeTextNode),
        patch("logseq_matryca_parser.synapse.NodeRelationship", fake_relationship),
        patch("logseq_matryca_parser.synapse.RelatedNodeInfo", FakeRelatedNodeInfo),
    ):
        nodes = SynapseAdapter.to_llamaindex_nodes([root], page_source_id="page-doc")

    by_id = {node.id_: node for node in nodes}
    assert by_id["sibling-b"].relationships["PREVIOUS"].node_id == "sibling-a"
    assert by_id["sibling-a"].relationships["NEXT"].node_id == "sibling-b"


def test_to_context_enriched_chunks_raises_when_dependency_missing(tmp_path: Path) -> None:
    with patch("logseq_matryca_parser.synapse.Document", None):
        with pytest.raises(ImportError, match="LangChain"):
            graph = LogseqGraph(graph_path=tmp_path, pages={})
            SynapseAdapter.to_context_enriched_chunks([], graph)


def test_synapse_context_enriched_chunking(tmp_path: Path) -> None:
    """Deep nodes embed page and ancestor markers inside ``page_content``; metadata keeps clean text."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text(
        "tags:: research\n"
        "project:: matryca-demo\n"
        "\n"
        "- Section **Alpha** [[SomePage]]\n"
        "  - Deep leaf line\n",
        encoding="utf-8",
    )
    graph = LogseqGraph.load_directory(graph_root)
    demo = graph.pages["Demo"]

    with patch("logseq_matryca_parser.synapse.Document", FakeDocument):
        chunks = SynapseAdapter.to_context_enriched_chunks(demo.root_nodes, graph)

    assert len(chunks) == 2
    child_chunk = chunks[1]
    assert child_chunk.metadata["clean_text"] == "Deep leaf line"
    assert "effective_properties" in child_chunk.metadata
    eff = child_chunk.metadata["effective_properties"]
    assert isinstance(eff, dict)
    assert eff.get("tags") == "research"
    assert eff.get("project") == "matryca-demo"
    assert child_chunk.metadata.get("source_path")
    assert child_chunk.metadata.get("line_start") is not None
    assert child_chunk.metadata.get("parent_id")
    assert "Demo" in child_chunk.page_content
    assert "Section" in child_chunk.page_content and "Alpha" in child_chunk.page_content
    assert "Deep leaf line" in child_chunk.page_content
    assert child_chunk.page_content.startswith("[")
    assert "]" in child_chunk.page_content


def test_synapse_recursive_embed_expansion(tmp_path: Path) -> None:
    """``page_content`` substitutes ``{{embed ((uuid))}}`` and ``{{embed [[Page]]}}`` with expanded text."""
    block_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "EmbedTarget.md").write_text(
        f"- Secret transcluded line\n  id:: {block_id}\n",
        encoding="utf-8",
    )
    (pages / "EmbedHost.md").write_text(
        "- Before {{embed ((" + block_id + "))}} after\n",
        encoding="utf-8",
    )
    (pages / "SnippetPage.md").write_text("- Line one from snippet\n- Line two from snippet\n", encoding="utf-8")
    (pages / "PageEmbedHost.md").write_text("- Start {{embed [[SnippetPage]]}} end\n", encoding="utf-8")

    graph = LogseqGraph.load_directory(graph_root)

    with patch("logseq_matryca_parser.synapse.Document", FakeDocument):
        host_chunks = SynapseAdapter.to_context_enriched_chunks(
            graph.pages["EmbedHost"].root_nodes, graph
        )
        page_embed_chunks = SynapseAdapter.to_context_enriched_chunks(
            graph.pages["PageEmbedHost"].root_nodes, graph
        )

    assert len(host_chunks) == 1
    host_pc = host_chunks[0].page_content
    assert "Secret transcluded line" in host_pc
    assert "{{embed" not in host_pc
    assert host_chunks[0].metadata["clean_text"] == "Before {{embed }} after"

    assert len(page_embed_chunks) == 1
    pe = page_embed_chunks[0].page_content
    assert "Line one from snippet" in pe and "Line two from snippet" in pe
    assert "{{embed [[" not in pe


def test_expand_embed_missing_page_completes_without_hang(tmp_path: Path) -> None:
    """Unresolved page embeds must not loop forever (BUG-001)."""
    from logseq_matryca_parser.synapse import _expand_macros_and_embeds

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "P.md").write_text("- x {{embed [[NoSuchPage]]}}\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    text = graph.pages["P"].root_nodes[0].content

    expanded = _expand_macros_and_embeds(text, graph, set())

    assert "{{embed [[NoSuchPage]]}}" not in expanded
    assert expanded.strip() == "x"


def test_expand_page_embed_resolves_case_insensitive_title(tmp_path: Path) -> None:
    from logseq_matryca_parser.synapse import _expand_macros_and_embeds

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "Target.md").write_text("- shared body\n", encoding="utf-8")
    (pages / "P.md").write_text("- {{embed [[target]]}}\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    text = graph.pages["P"].root_nodes[0].content

    expanded = _expand_macros_and_embeds(text, graph, set())

    assert "shared body" in expanded


def test_expand_cyclic_page_embed_does_not_duplicate_parent_text(tmp_path: Path) -> None:
    """A embeds B embeds A must not re-inline parent literal text (#65)."""
    from logseq_matryca_parser.synapse import _expand_macros_and_embeds

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("- before {{embed [[B]]}} after\n", encoding="utf-8")
    (pages / "B.md").write_text("- inner {{embed [[A]]}}\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    host_page = graph.pages["A"]
    text = host_page.root_nodes[0].content
    chain = frozenset({host_page.title})

    expanded = _expand_macros_and_embeds(text, graph, set(), embed_page_chain=chain)

    assert expanded.strip() == "before inner after"


def test_expand_missing_block_embed_completes_without_hang(tmp_path: Path) -> None:
    from logseq_matryca_parser.synapse import _expand_macros_and_embeds

    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    missing = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    (pages / "P.md").write_text(f"- {{{{embed (({missing}))}}}}\n", encoding="utf-8")
    graph = LogseqGraph.load_directory(graph_root)
    text = graph.pages["P"].root_nodes[0].content

    expanded = _expand_macros_and_embeds(text, graph, set())

    assert "{{embed" not in expanded


class TestEmbedExpansionEdgeCases:
    """Table-driven tests for embed expansion edge cases (cycles, missing targets, happy path)."""

    @pytest.fixture(scope="class")
    def graph(self, tmp_path_factory: pytest.TempPathFactory) -> LogseqGraph:
        vault = tmp_path_factory.mktemp("embed_edge_vault")
        pages = vault / "pages"
        pages.mkdir(parents=True)

        # Happy path page embed: A → B
        (pages / "B.md").write_text("- Content from page B\n", encoding="utf-8")
        (pages / "AEmbedsB.md").write_text(
            "- Before {{embed [[B]]}} after\n", encoding="utf-8"
        )

        # Cycle detection: A ↔ B
        (pages / "CycleA.md").write_text(
            "- before {{embed [[CycleB]]}} after\n", encoding="utf-8"
        )
        (pages / "CycleB.md").write_text(
            "- inner {{embed [[CycleA]]}}\n", encoding="utf-8"
        )

        # Missing page target
        (pages / "MissingPage.md").write_text(
            "- x {{embed [[NoSuchPage]]}}\n", encoding="utf-8"
        )

        # Missing block target
        missing_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        (pages / "MissingBlock.md").write_text(
            f"- {{{{embed (({missing_uuid}))}}}}\n", encoding="utf-8"
        )

        # Happy path block embed
        block_uuid = "bbbbbbbb-cccc-cccc-cccc-dddddddddddd"
        (pages / "BlockTarget.md").write_text(
            f"- Secret transcluded line\n  id:: {block_uuid}\n", encoding="utf-8"
        )
        (pages / "BlockHost.md").write_text(
            f"- Before {{{{embed (({block_uuid}))}}}} after\n", encoding="utf-8"
        )

        return LogseqGraph.load_directory(vault)

    @pytest.mark.parametrize(
        ("page_title", "embed_page_chain", "expected", "unexpected"),
        [
            (
                "AEmbedsB",
                frozenset(),
                ["Content from page B"],
                ["{{embed [[B]]}}"],
            ),
            (
                "CycleA",
                frozenset({"CycleA"}),
                ["before inner after"],
                ["before inner before"],
            ),
            (
                "MissingPage",
                frozenset(),
                ["x"],
                ["{{embed [[NoSuchPage]]}}"],
            ),
            (
                "MissingBlock",
                frozenset(),
                [],
                ["{{embed"],
            ),
            (
                "BlockHost",
                frozenset(),
                ["Secret transcluded line", "Before", "after"],
                ["{{embed (("],
            ),
        ],
    )
    def test_expand_macros_and_embeds_edge_cases(
        self,
        graph: LogseqGraph,
        page_title: str,
        embed_page_chain: frozenset[str],
        expected: list[str],
        unexpected: list[str],
    ) -> None:
        from logseq_matryca_parser.synapse import _expand_macros_and_embeds

        page = graph.pages[page_title]
        text = page.root_nodes[0].content
        expanded = _expand_macros_and_embeds(
            text, graph, set(), embed_page_chain=embed_page_chain
        )

        for sub in expected:
            assert sub in expanded, f"Expected {sub!r} in {expanded!r}"
        for sub in unexpected:
            assert sub not in expanded, f"Found unexpected {sub!r} in {expanded!r}"

class TestStripMarkdownForEmbedding:
    """Table-driven tests for ``_strip_markdown_for_embedding()`` cleaner."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("plain text", "plain text"),
            ("[[Simple Link]]", "Simple Link"),
            ("[[Page|Alias]]", "Page"),
            ("**bold text**", "bold text"),
            ("*italic text*", "italic text"),
            ("`code span`", "code span"),
            ("text with #tag removed", "text with removed"),
            ("**bold** and *italic* and `code`", "bold and italic and code"),
            ("  extra spaces  ", "extra spaces"),
            ("", ""),
        ],
    )
    def test_strip_markdown(self, text, expected):
        assert _strip_markdown_for_embedding(text) == expected

    def test_combined_formatting(self):
        result = _strip_markdown_for_embedding(
            "See **[[Project Page]]** for `details` #todo"
        )
        assert result == "See Project Page for details"


# ── build_synapse_metadata schema (issue #51) ──────────────────────────


class TestBuildSynapseMetadata:
    """Direct schema tests for ``build_synapse_metadata()`` output."""

    def test_includes_core_keys(self):
        node = LogseqNode(uuid="abc", content="Test", indent_level=0)
        meta = build_synapse_metadata(node, source="test")
        for key in ("uuid", "indent_level", "source", "path", "refs",
                     "task_status", "task_priority"):
            assert key in meta

    def test_property_serialization(self):
        node = LogseqNode(uuid="x", content="T", indent_level=1,
                          properties={"tags": "ai", "status": "done"})
        meta = build_synapse_metadata(node, source="s")
        assert meta["tags"] == "ai"
        assert meta["status"] == "done"

    def test_extra_kwarg_merged(self):
        node = LogseqNode(uuid="y", content="T2", indent_level=0)
        meta = build_synapse_metadata(node, source="s", extra={"custom": 42})
        assert meta["custom"] == 42

    def test_nullable_fields_are_none(self):
        node = LogseqNode(uuid="n", content="X", indent_level=0)
        meta = build_synapse_metadata(node, source="s")
        assert meta["parent_id"] is None
        assert meta["scheduled_at"] is None
