from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import networkx as nx  # type: ignore[import-untyped]

from logseq_matryca_parser.lens import GraphVisualizer, NetworkXVisitor
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage


def _build_fake_page() -> LogseqPage:
    child = LogseqNode(
        uuid="node-child",
        content="Child #alpha",
        indent_level=1,
        refs=["#alpha", "[[ChildRef]]"],
    )
    root = LogseqNode(
        uuid="node-root",
        content="Root block",
        indent_level=0,
        refs=["#alpha", "[[TargetPage]]"],
        children=[child],
    )
    return LogseqPage(
        title="MainPage",
        raw_content="- Root block",
        root_nodes=[root],
    )


def test_networkx_visitor_adds_nodes_and_edges_from_refs() -> None:
    page = _build_fake_page()
    graph = nx.Graph()
    visitor = NetworkXVisitor(graph=graph, page_title=page.title)

    for node in page.root_nodes:
        node.accept(visitor)

    assert graph.has_node("MainPage")
    assert graph.nodes["MainPage"]["group"] == "page"
    assert graph.nodes["#alpha"]["group"] == "tag"
    assert graph.nodes["[[TargetPage]]"]["group"] == "page"
    assert graph.has_edge("MainPage", "#alpha")
    assert graph.has_edge("MainPage", "[[TargetPage]]")
    assert graph.has_edge("MainPage", "[[ChildRef]]")


def test_graph_visualizer_build_network_creates_expected_topology() -> None:
    visualizer = GraphVisualizer(pages=[_build_fake_page()])
    visualizer.build_network()

    graph = visualizer.graph
    assert graph.number_of_nodes() == 4
    assert graph.number_of_edges() == 3

    stats = visualizer.get_deep_statistics()
    assert stats["total_nodes"] == 4
    assert stats["total_edges"] == 3
    assert stats["largest_pages"] == [{"page": "MainPage", "block_count": 2}]
    assert stats["top_connected_nodes"][0]["node"] == "MainPage"
    assert stats["top_connected_nodes"][0]["degree"] == 3


def test_export_html_calls_save_graph_with_mocked_pyvis(tmp_path: Path) -> None:
    visualizer = GraphVisualizer(pages=[_build_fake_page()])
    visualizer.build_network()
    destination = tmp_path / "lens-graph.html"

    def _fake_save_graph(path: str) -> None:
        Path(path).write_text('<div id="loadingBar"></div>', encoding="utf-8")

    with patch("logseq_matryca_parser.lens.Network.save_graph") as save_graph_mock:
        save_graph_mock.side_effect = _fake_save_graph
        visualizer.export_html(destination)

    save_graph_mock.assert_called_once_with(str(destination))
    body = destination.read_text(encoding="utf-8")
    assert 'style="display: none !important;"' in body
