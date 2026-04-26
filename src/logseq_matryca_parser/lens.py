"""LENS topology extraction and interactive graph visualization."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
from pyvis.network import Network  # type: ignore[import-untyped]

from logseq_matryca_parser.logos_core import ASTVisitor, LogseqNode, LogseqPage

logger = logging.getLogger(__name__)


class NetworkXVisitor(ASTVisitor):
    """Populate a NetworkX graph from Logseq node references."""

    def __init__(self, graph: nx.Graph, page_title: str) -> None:
        self._graph = graph
        self._page_title = page_title

    def visit_node(self, node: LogseqNode) -> None:
        if not self._graph.has_node(self._page_title):
            self._graph.add_node(self._page_title, group="page")

        for ref in node.refs:
            ref_group = "tag" if ref.startswith("#") else "page"
            if not self._graph.has_node(ref):
                self._graph.add_node(ref, group=ref_group)
            self._graph.add_edge(self._page_title, ref)

        logger.debug(
            "LENS visit_node page=%s refs=%d cumulative_edges=%d",
            self._page_title,
            len(node.refs),
            self._graph.number_of_edges(),
        )

    def depart_node(self, node: LogseqNode) -> None:
        _ = node


class GraphVisualizer:
    """Build and visualize a Logseq topology graph."""

    def __init__(self, pages: list[LogseqPage]) -> None:
        self._pages = pages
        self._graph: nx.Graph = nx.Graph()

    @property
    def graph(self) -> nx.Graph:
        return self._graph

    def build_network(self) -> None:
        self._graph = nx.Graph()
        for page in self._pages:
            self._graph.add_node(page.title, group="page")
            visitor = NetworkXVisitor(graph=self._graph, page_title=page.title)
            for root_node in page.root_nodes:
                root_node.accept(visitor)
        logger.debug(
            "LENS build_network completed nodes=%d edges=%d",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    def get_deep_statistics(self) -> dict[str, Any]:
        degree_items = sorted(
            self._graph.degree(),
            key=lambda item: item[1],
            reverse=True,
        )
        top_connected = [
            {
                "node": node_name,
                "degree": degree,
                "group": str(self._graph.nodes[node_name].get("group", "unknown")),
            }
            for node_name, degree in degree_items[:10]
        ]

        largest_pages: list[dict[str, str | int]] = [
            {"page": page.title, "block_count": self._count_page_blocks(page)}
            for page in self._pages
        ]
        largest_pages = sorted(
            largest_pages,
            key=lambda item: int(item["block_count"]),
            reverse=True,
        )[:5]

        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "top_connected_nodes": top_connected,
            "largest_pages": largest_pages,
        }

    @staticmethod
    def _count_page_blocks(page: LogseqPage) -> int:
        total_blocks = 0
        stack = list(page.root_nodes)
        while stack:
            current_node = stack.pop()
            total_blocks += 1
            stack.extend(current_node.children)
        return total_blocks

    def export_html(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        network = Network(height="900px", width="100%", bgcolor="#111827", font_color="white")
        network.from_nx(self._graph)
        network.set_options(
            """
            var options = {
              "nodes": {"shape": "dot", "size": 18},
              "edges": {"color": {"inherit": true}, "smooth": false},
              "physics": {
                "enabled": true,
                "barnesHut": {"gravitationalConstant": -18000, "springLength": 140}
              },
              "interaction": {"hover": true, "navigationButtons": true}
            }
            """
        )
        network.save_graph(str(output_path))
        logger.debug("LENS HTML graph exported to %s", output_path)
