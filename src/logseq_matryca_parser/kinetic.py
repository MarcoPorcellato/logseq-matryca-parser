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