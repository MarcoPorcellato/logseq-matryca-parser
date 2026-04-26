"""KINETIC command line interface for Logseq graph parsing."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from logseq_matryca_parser.forge import ForgeExporter
from logseq_matryca_parser.lens import GraphVisualizer
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import LogosParser
from logseq_matryca_parser.synapse import SynapseAdapter

logger = logging.getLogger(__name__)
app = typer.Typer(help="KINETIC CLI for parsing and exporting Logseq graphs.", no_args_is_help=True)
console = Console()


class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    LANGCHAIN = "langchain"


def _discover_graph_files(graph_path: Path) -> list[Path]:
    files: list[Path] = []
    for folder_name in ("pages", "journals"):
        target = graph_path / folder_name
        if not target.exists():
            logger.debug("Skipping missing graph subdirectory: %s", target)
            continue
        files.extend(sorted(target.rglob("*.md")))
    logger.debug("Discovered %d markdown files in graph %s", len(files), graph_path)
    return files


def _iter_nodes(nodes: Iterable[LogseqNode]) -> Iterable[LogseqNode]:
    for node in nodes:
        yield node
        if node.children:
            yield from _iter_nodes(node.children)


def _parse_graph(graph_path: Path) -> list[LogseqPage]:
    parser = LogosParser()
    files = _discover_graph_files(graph_path)
    if not files:
        return []

    pages: list[LogseqPage] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Parsing Logseq graph", total=len(files))
        for file_path in files:
            logger.debug("Parsing graph file: %s", file_path)
            pages.append(parser.parse_page_file(file_path))
            progress.advance(task_id)
    return pages


def _build_stats_table(pages: list[LogseqPage]) -> Table:
    total_blocks = 0
    total_tags = 0
    total_tasks = 0

    for page in pages:
        for node in _iter_nodes(page.root_nodes):
            total_blocks += 1
            total_tags += len(node.tags)
            if node.task_status is not None:
                total_tasks += 1

    table = Table(title="Graph Scan Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="bold green")
    table.add_row("Total Pages", str(len(pages)))
    table.add_row("Total Blocks", str(total_blocks))
    table.add_row("Total Tags extracted", str(total_tags))
    table.add_row("Total Tasks found", str(total_tasks))
    return table


def _build_deep_stats_tables(stats: dict[str, Any]) -> tuple[Table, Table, Table]:
    overview_table = Table(title="LENS Deep Statistics")
    overview_table.add_column("Metric", style="cyan")
    overview_table.add_column("Value", justify="right", style="bold green")
    overview_table.add_row("Total Nodes", str(stats["total_nodes"]))
    overview_table.add_row("Total Edges", str(stats["total_edges"]))

    connectivity_table = Table(title="Top 10 Most Connected Nodes")
    connectivity_table.add_column("Node", style="cyan")
    connectivity_table.add_column("Group", style="magenta")
    connectivity_table.add_column("Degree", justify="right", style="bold green")
    for entry in stats["top_connected_nodes"]:
        connectivity_table.add_row(str(entry["node"]), str(entry["group"]), str(entry["degree"]))

    largest_pages_table = Table(title="Top 5 Largest Pages")
    largest_pages_table.add_column("Page", style="cyan")
    largest_pages_table.add_column("Block Count", justify="right", style="bold green")
    for entry in stats["largest_pages"]:
        largest_pages_table.add_row(str(entry["page"]), str(entry["block_count"]))

    return overview_table, connectivity_table, largest_pages_table


def _build_official_logseq_demo_pages() -> list[LogseqPage]:
    """Synthetic pages mimicking the official Logseq example graph (no disk I/O)."""
    # Star hub: "Logseq" at center, spokes to core concepts, journals, and a tag.
    hub_refs: list[str] = [
        "[[Contents]]",
        "[[Graph]]",
        "[[Page]]",
        "[[Block]]",
        "[[Journal]]",
        "2023_01_01",
        "2024_06_15",
        "logseq",
    ]
    hub = LogseqNode(
        uuid="showcase-hub",
        content="Logseq is a local-first, privacy-focused outliner and graph for knowledge work.",
        clean_text="Logseq is a local-first, privacy-focused outliner and graph for knowledge work.",
        indent_level=0,
        refs=hub_refs,
        tags=["logseq", "outliner"],
    )
    # Secondary block for a little depth (cross-link to [[Page]]).
    branch = LogseqNode(
        uuid="showcase-branch",
        content="A block is a node in a tree. Blocks can nest and reference others.",
        clean_text="A block is a node in a tree. Blocks can nest and reference others.",
        indent_level=1,
        parent_id=hub.uuid,
        refs=["[[Block]]", "[[Page]]", "logseq"],
        tags=["logseq"],
    )
    root_tree = hub.model_copy(update={"children": [branch]})
    return [
        LogseqPage(
            title="Logseq",
            raw_content="",
            source_path=None,
            graph_root=None,
            root_nodes=[root_tree],
        )
    ]


@app.command()
def scan(graph_path: Path = typer.Argument(..., help="Path to the Logseq graph root.")) -> None:
    """Scan a graph and print aggregate parsing statistics."""
    if not graph_path.exists() or not graph_path.is_dir():
        console.print(f"[bold red]Invalid graph path:[/] {graph_path}")
        raise typer.Exit(code=1)

    pages = _parse_graph(graph_path.resolve())
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    console.print(_build_stats_table(pages))


@app.command()
def visualize(
    graph_path: Path = typer.Argument(..., help="Path to the Logseq graph root."),
    output_html: Path = typer.Argument(..., help="Output HTML path for network visualization."),
) -> None:
    """Parse a graph, compute deep topology stats, and export an interactive HTML network."""
    if not graph_path.exists() or not graph_path.is_dir():
        console.print(f"[bold red]Invalid graph path:[/] {graph_path}")
        raise typer.Exit(code=1)

    pages = _parse_graph(graph_path.resolve())
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    visualizer = GraphVisualizer(pages=pages)
    visualizer.build_network()
    stats = visualizer.get_deep_statistics()

    overview_table, connectivity_table, largest_pages_table = _build_deep_stats_tables(stats)
    console.print(overview_table)
    console.print(connectivity_table)
    console.print(largest_pages_table)

    visualizer.export_html(output_html)
    console.print(f"[bold green]Visualization HTML written:[/] {output_html}")


@app.command()
def demo(
    output_html: Path = typer.Argument(
        Path("showcase.html"),
        help="Path for the standalone showcase HTML (default: showcase.html in cwd).",
    ),
) -> None:
    """Build a sample graph from the official Logseq demo topology and write showcase HTML (no graph files read)."""
    pages = _build_official_logseq_demo_pages()
    visualizer = GraphVisualizer(pages=pages)
    visualizer.build_network()
    visualizer.export_html(output_html.resolve())
    console.print(
        f"[bold green]Showcase example written:[/] {output_html.resolve()} "
        f"(open in a browser to preview the LENS graph)."
    )


def _export_json(pages: list[LogseqPage], output_path: Path) -> Path:
    payload: list[dict[str, Any]] = []
    for page in pages:
        page_payload = {
            "title": page.title,
            "source_path": page.source_path,
            "graph_root": page.graph_root,
            "properties": page.properties,
            "refs": page.refs,
            "created_at": page.created_at,
            "updated_at": page.updated_at,
            "ast": json.loads(ForgeExporter.to_json(page.root_nodes)),
        }
        payload.append(page_payload)
    destination = output_path / "graph.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def _export_markdown(pages: list[LogseqPage], output_path: Path) -> Path:
    destination = output_path / "graph.md"
    sections: list[str] = []
    for page in pages:
        sections.append(f"# {page.title}")
        sections.append(ForgeExporter.to_clean_markdown(page.root_nodes))
        sections.append("")
    destination.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return destination


def _export_langchain(pages: list[LogseqPage], output_path: Path) -> Path:
    payload: list[dict[str, Any]] = []
    for page in pages:
        docs = SynapseAdapter.to_langchain_documents(page.root_nodes, source_name=page.title)
        payload.extend(
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in docs
        )
    destination = output_path / "langchain.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


@app.command()
def export(
    graph_path: Path = typer.Argument(..., help="Path to the Logseq graph root."),
    output_path: Path = typer.Argument(..., help="Output directory for exported artifacts."),
    format: ExportFormat = typer.Option(ExportFormat.JSON, "--format", "-f", help="Export format."),
) -> None:
    """Parse an entire graph and export it to the selected format."""
    if not graph_path.exists() or not graph_path.is_dir():
        console.print(f"[bold red]Invalid graph path:[/] {graph_path}")
        raise typer.Exit(code=1)

    pages = _parse_graph(graph_path.resolve())
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    output_path.mkdir(parents=True, exist_ok=True)

    try:
        if format is ExportFormat.JSON:
            destination = _export_json(pages, output_path)
        elif format is ExportFormat.MARKDOWN:
            destination = _export_markdown(pages, output_path)
        else:
            destination = _export_langchain(pages, output_path)
    except ImportError as exc:
        console.print(f"[bold red]Export failed:[/] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Export completed:[/] {destination}")


if __name__ == "__main__":
    app()