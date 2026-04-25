from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from logseq_matryca_parser.logos_core import LogseqNode
from logseq_matryca_parser.synapse import SynapseAdapter


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
        refs=["[[ref-child]]"],
        path=["Root", "Child"],
        left_id="left-child",
        task_status="TODO",
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
    assert root_doc.metadata["path"] == ["Root"]
    assert root_doc.metadata["left_id"] == "left-root"
    assert root_doc.metadata["refs"] == ["[[ref-root]]"]
    assert root_doc.metadata["created_at"] == 100
    assert root_doc.metadata["topic"] == "alpha"

    assert child_doc.metadata["parent_id"] == "root-1"
    assert child_doc.metadata["task_status"] == "TODO"
    assert child_doc.metadata["repeater"] == "+1w"
    assert child_doc.metadata["path"] == ["Root", "Child"]


def test_to_llamaindex_nodes_raises_when_dependency_missing() -> None:
    with (
        patch("logseq_matryca_parser.synapse.TextNode", None),
        patch("logseq_matryca_parser.synapse.NodeRelationship", None),
        patch("logseq_matryca_parser.synapse.RelatedNodeInfo", None),
    ):
        with pytest.raises(ImportError, match="LlamaIndex"):
            SynapseAdapter.to_llamaindex_nodes(build_ast())


def test_to_llamaindex_nodes_injects_parent_child_relationships() -> None:
    fake_relationship = SimpleNamespace(PARENT="PARENT", CHILD="CHILD")
    with (
        patch("logseq_matryca_parser.synapse.TextNode", FakeTextNode),
        patch("logseq_matryca_parser.synapse.NodeRelationship", fake_relationship),
        patch("logseq_matryca_parser.synapse.RelatedNodeInfo", FakeRelatedNodeInfo),
    ):
        nodes = SynapseAdapter.to_llamaindex_nodes(build_ast())

    assert len(nodes) == 2
    root_node = nodes[0]
    child_node = nodes[1]

    assert child_node.relationships["PARENT"].node_id == "root-1"
    assert root_node.relationships["CHILD"][0].node_id == "child-1"
    assert root_node.metadata["path"] == ["Root"]
    assert child_node.metadata["task_status"] == "TODO"
