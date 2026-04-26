"""LENS topology extraction and interactive graph visualization."""

from __future__ import annotations

import logging
import re
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
        page_block_counts = {page.title: self._count_page_blocks(page) for page in self._pages}
        for page in self._pages:
            self._graph.add_node(page.title, group="page")
            visitor = NetworkXVisitor(graph=self._graph, page_title=page.title)
            for root_node in page.root_nodes:
                root_node.accept(visitor)

        degree_by_node = dict(self._graph.degree())
        for node_name in self._graph.nodes:
            group = self._classify_node_group(node_name)
            degree = int(degree_by_node.get(node_name, 0))
            page_block_count = page_block_counts.get(node_name)
            title = (
                f"<b>{node_name}</b><br>"
                f"Group: {group}<br>"
                f"Connections: {degree}"
            )
            if page_block_count is not None:
                title = f"{title}<br>Blocks: {page_block_count}"

            self._graph.nodes[node_name].update(
                {
                    "group": group,
                    "value": degree + 1,
                    "title": title,
                }
            )
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

    @staticmethod
    def _classify_node_group(node_name: str) -> str:
        normalized_name = node_name.strip()
        if normalized_name.lower().startswith("progetti___"):
            return "project"
        if normalized_name.startswith("#"):
            return "tag"
        if GraphVisualizer._looks_like_journal(normalized_name):
            return "journal"
        return "page"

    @staticmethod
    def _looks_like_journal(node_name: str) -> bool:
        if re.match(r"^\d{4}_\d{2}_\d{2}$", node_name):
            return True
        if re.match(r"^\d{4}-\d{2}-\d{2}$", node_name):
            return True
        return bool(re.match(r"^\[\[[A-Za-z]{3} \d{1,2}(st|nd|rd|th), \d{4}\]\]$", node_name))

    def export_html(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        network = Network(height="900px", width="100%", bgcolor="#111827", font_color="white")
        network.from_nx(self._graph)
        network.repulsion(node_distance=100, spring_length=200, damping=0.2)
        network.show_buttons(filter_=["physics", "nodes"])
        network.set_options(
            """
            var options = {
              "nodes": {
                "shape": "dot",
                "scaling": {"min": 8, "max": 42, "label": {"enabled": true}}
              },
              "edges": {
                "color": {"inherit": true, "opacity": 0.35},
                "smooth": {"enabled": true, "type": "dynamic"}
              },
              "physics": {
                "enabled": true,
                "barnesHut": {
                  "gravitationalConstant": -25000,
                  "centralGravity": 0.18,
                  "springLength": 180,
                  "springConstant": 0.02,
                  "damping": 0.12,
                  "avoidOverlap": 0.85
                },
                "stabilization": {"enabled": true, "iterations": 800}
              },
              "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "navigationButtons": true,
                "hoverConnectedEdges": true
              }
            }
            """
        )
        network.save_graph(str(output_path))
        logger.debug("LENS HTML graph exported to %s", output_path)
