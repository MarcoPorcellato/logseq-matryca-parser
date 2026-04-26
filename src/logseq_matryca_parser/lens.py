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
            ref_group = "tag" if (ref in node.tags or ref.startswith("#")) else "page"
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
            current_group = self._graph.nodes[node_name].get("group")
            group = self._classify_node_group(node_name=node_name, current_group=current_group)
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

    @classmethod
    def _classify_node_group(cls, node_name: str, current_group: Any) -> str:
        normalized_name = node_name.strip()
        if normalized_name.lower().startswith("progetti___"):
            return "project"
        if cls._looks_like_journal(normalized_name):
            return "journal"
        if current_group == "tag" or normalized_name.startswith("#"):
            return "tag"
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
        network = Network(height="100vh", width="100%", bgcolor="#111827", font_color="white")
        network.from_nx(self._graph)
        network.force_atlas_2based(
            gravity=-50,
            central_gravity=0.01,
            spring_length=100,
            spring_strength=0.08,
            damping=0.4,
            overlap=0,
        )
        network.toggle_stabilization(False)
        network.options.edges.smooth = False
        network.show_buttons(filter_=["physics", "nodes"])
        network.save_graph(str(output_path))
        output_html = output_path.read_text(encoding="utf-8")
        if 'name="viewport"' not in output_html:
            output_html = re.sub(
                r"<head([^>]*)>",
                (
                    r'<head\1>'
                    r'<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
                ),
                output_html,
                count=1,
            )
        output_html = output_html.replace(
            '<div id="loadingBar">',
            '<div id="loadingBar" style="display: none !important;">',
        )
        custom_css = """
        html, body, #mynetwork {
          margin: 0;
          padding: 0;
          width: 100vw;
          height: 100vh;
          overflow: hidden;
          background-color: #111827;
        }
        /* Responsive HUD */
        @media (max-width: 600px) {
          #hud-sidebar {
            width: 90% !important;
            left: 5% !important;
            right: 5% !important;
            top: 10px !important;
            max-height: 80vh !important;
          }
          #hud-toggle {
            right: 16px !important;
            top: 10px !important;
          }
        }
        #hud-sidebar {
          position: fixed;
          top: 16px;
          right: 16px;
          width: 350px;
          background: rgba(255, 255, 255, 0.04) !important;
          -webkit-backdrop-filter: blur(10px) !important;
          backdrop-filter: blur(10px) !important;
          border: 1px solid rgba(255, 255, 255, 0.15) !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
          box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5) !important;
          border-radius: 12px !important;
          color: white;
          padding: 15px;
          z-index: 9999;
          max-height: 90vh;
          overflow-y: auto;
          overflow-x: hidden !important;
          transform: translateX(0);
          transition: transform 220ms ease-in-out, opacity 220ms ease-in-out;
          opacity: 1;
        }
        #hud-sidebar.hud-hidden {
          transform: translateX(calc(100% + 28px));
          opacity: 0;
          pointer-events: none;
        }
        #hud-toggle {
          position: fixed;
          top: 16px;
          right: 388px;
          z-index: 10000;
          border: 1px solid rgba(148, 163, 184, 0.35);
          background: rgba(15, 23, 42, 0.92);
          color: #ffffff;
          border-radius: 8px;
          padding: 8px 12px;
          font-family: sans-serif;
          font-size: 13px;
          cursor: pointer;
          box-shadow: 0 8px 20px rgba(2, 6, 23, 0.35);
        }
        #hud-toggle:hover {
          background: rgba(30, 41, 59, 0.95);
        }
        #hud-sidebar #config {
          width: 100%;
          max-width: 100%;
          background: transparent !important;
          background-color: transparent !important;
        }
        /* Nuke all vis-configuration backgrounds except color preview blocks */
        #hud-sidebar .vis-configuration:not(.vis-config-colorBlock):not(.vis-color-picker) {
          background: transparent !important;
          background-color: transparent !important;
          border: none !important;
          color: #e5e7eb !important;
        }

        /* Clean up the labels */
        #hud-sidebar .vis-config-label {
          color: #f9fafb !important;
          font-weight: 500 !important;
          text-shadow: none !important;
          margin-bottom: 2px !important;
        }

        /* Style text/number inputs without breaking native sliders */
        #hud-sidebar input[type="text"],
        #hud-sidebar input[type="number"],
        #hud-sidebar select {
          background-color: #374151 !important;
          color: white !important;
          border: 1px solid #4b5563 !important;
          border-radius: 4px;
          padding: 2px 4px;
          outline: none;
        }

        /* Ensure range sliders and checkboxes remain native and readable */
        #hud-sidebar input[type="range"],
        #hud-sidebar input[type="checkbox"] {
          background: transparent !important;
          margin: 0 5px;
        }

        /* Ensure color blocks have a visible border on dark glass */
        #hud-sidebar .vis-config-colorBlock {
          border: 1px solid #9ca3af !important;
          border-radius: 3px !important;
        }

        /* Prevent horizontal overflow and shrink inputs */
        #hud-sidebar * {
          box-sizing: border-box !important;
        }
        #hud-sidebar .vis-configuration-wrapper {
          width: 100% !important;
          max-width: 100% !important;
        }
        #hud-sidebar .vis-config-item {
          max-width: 100% !important;
          white-space: normal !important;
        }

        /* Shrink the range sliders so they fit next to labels */
        #hud-sidebar input[type="range"] {
          max-width: 100px !important;
          width: 100px !important;
          min-width: 50px !important;
        }

        /* Shrink the number/text input boxes */
        #hud-sidebar input[type="number"],
        #hud-sidebar input[type="text"] {
          max-width: 60px !important;
        }
        """
        custom_js = """
        (function() {
          const configPanel = document.getElementById('config');
          if (!configPanel) {
            return;
          }

          const hudSidebar = document.createElement('div');
          hudSidebar.id = 'hud-sidebar';

          const hudToggle = document.createElement('button');
          hudToggle.id = 'hud-toggle';
          hudToggle.type = 'button';
          hudToggle.textContent = 'Hide Controls';

          document.body.appendChild(hudSidebar);
          document.body.appendChild(hudToggle);

          // 1. Create the Custom Controls HTML
          const customControls = document.createElement('div');
          customControls.innerHTML = `
              <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                  <h3 style="margin-top:0; color: #F9FAFB; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Logseq Filters</h3>
                  <label style="display:flex; align-items:center; gap:8px; font-size: 13px; color: #E5E7EB; cursor:pointer; margin-bottom: 8px;">
                      <input type="checkbox" id="filter-journals" checked style="accent-color: #3B82F6; cursor:pointer;"> Show Daily Journals
                  </label>
                  <label style="display:flex; align-items:center; gap:8px; font-size: 13px; color: #E5E7EB; cursor:pointer; margin-bottom: 12px;">
                      <input type="checkbox" id="filter-tags" checked style="accent-color: #3B82F6; cursor:pointer;"> Show Tags
                  </label>
                  <button id="btn-reset" style="width: 100%; padding: 6px; background: #374151; color: white; border: 1px solid #4B5563; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500; transition: background 0.2s;">
                      🔄 Reset Graph & Physics
                  </button>
              </div>
          `;
          hudSidebar.appendChild(customControls);

          // 2. Append the original config div below our filters
          hudSidebar.appendChild(configPanel);

          // 3. Add Event Listeners for Hover Effects
          const resetButton = document.getElementById('btn-reset');
          const filterJournals = document.getElementById('filter-journals');
          const filterTags = document.getElementById('filter-tags');
          if (!resetButton || !filterJournals || !filterTags) {
            return;
          }
          resetButton.onmouseover = function() { this.style.background = '#4B5563'; };
          resetButton.onmouseout = function() { this.style.background = '#374151'; };

          // 4. Implement Reset Logic
          resetButton.addEventListener('click', () => {
            window.location.reload();
          });

          // 5. Implement Dynamic Filtering using PyVis global 'nodes' DataSet
          function applyFilters() {
            if (typeof nodes !== 'undefined') {
              const updates = [];
              nodes.get().forEach(node => {
                let isHidden = false;
                if (!filterJournals.checked && node.group === 'journal') isHidden = true;
                if (!filterTags.checked && node.group === 'tag') isHidden = true;
                updates.push({ id: node.id, hidden: isHidden });
              });
              nodes.update(updates);
            }
          }
          filterJournals.addEventListener('change', applyFilters);
          filterTags.addEventListener('change', applyFilters);

          hudToggle.onclick = function() {
            const isHidden = hudSidebar.classList.toggle('hud-hidden');
            hudToggle.textContent = isHidden ? 'Show Controls' : 'Hide Controls';
          };

          setTimeout(() => {
            const sidebar = document.getElementById('hud-sidebar');
            const configDiv = document.getElementById('config');
            if (sidebar && configDiv) {
              let lastScroll = 0;

              // Record scroll position continuously
              sidebar.addEventListener('scroll', () => { lastScroll = sidebar.scrollTop; }, { passive: true });
              sidebar.addEventListener('mousedown', () => { lastScroll = sidebar.scrollTop; });

              // Watch for vis.js rebuilding the config panel
              const observer = new MutationObserver(() => {
                sidebar.scrollTop = lastScroll;
              });

              // Observe changes to the children of the config div
              observer.observe(configDiv, { childList: true, subtree: true });
            }
          }, 500);
        })();
        """
        output_html = output_html.replace(
            "</body>",
            f"<style>{custom_css}</style><script>{custom_js}</script></body>",
        )
        output_path.write_text(output_html, encoding="utf-8")
        logger.debug("LENS HTML graph exported to %s", output_path)
