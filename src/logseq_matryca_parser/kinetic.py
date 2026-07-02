"""KINETIC command line interface for Logseq graph parsing."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

import typer
from rich.console import Console

from logseq_matryca_parser.kinetic_export import (
    export_json,
    export_langchain,
    export_langchain_enriched,
    export_markdown,
    export_obsidian,
)
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

logger = logging.getLogger(__name__)
app = typer.Typer(
    help="KINETIC CLI for parsing and exporting Logseq graphs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    graph: Path | None = typer.Option(
        None,
        "--graph",
        help="Default Logseq graph root (used when a command omits the positional graph path).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
) -> None:
    """Matryca KINETIC — deterministic Logseq graph tooling."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["graph"] = graph.resolve() if graph is not None else None
    if verbose:
        logging.getLogger("logseq_matryca_parser").setLevel(logging.DEBUG)


def _cli_context(ctx: typer.Context) -> dict[str, Any]:
    obj = ctx.obj
    return obj if isinstance(obj, dict) else {}


def _resolve_graph_path(ctx: typer.Context, graph_path: Path | None) -> Path:
    """Resolve graph root from positional argument or global ``--graph`` callback option."""
    if graph_path is not None:
        candidate = graph_path.expanduser()
    else:
        default_graph = _cli_context(ctx).get("graph")
        if default_graph is None:
            console.print(
                "[bold red]Graph path required:[/] pass a positional path or set "
                "[cyan]--graph[/]."
            )
            raise typer.Exit(code=1)
        candidate = Path(str(default_graph)).expanduser()
    if not candidate.exists() or not candidate.is_dir():
        console.print(f"[bold red]Invalid graph path:[/] {candidate}")
        raise typer.Exit(code=1)
    return candidate.resolve()


class ExportFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    LANGCHAIN = "langchain"
    LANGCHAIN_ENRICHED = "langchain-enriched"
    OBSIDIAN = "obsidian"


def _iter_nodes(nodes: Iterable[LogseqNode]) -> Iterable[LogseqNode]:
    for node in nodes:
        yield node
        if node.children:
            yield from _iter_nodes(node.children)


def _canonical_pages_from_graph(graph_path: Path) -> list[LogseqPage]:
    """Load a graph directory and return deduplicated canonical pages for export."""
    from logseq_matryca_parser.graph import LogseqGraph

    graph = LogseqGraph.load_directory(graph_path)
    return list(graph.iter_canonical_pages())


def _build_official_logseq_demo_pages() -> list[LogseqPage]:
    """Synthetic pages mimicking the official Logseq example graph (no disk I/O)."""
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


def _require_absolute_path(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        console.print(f"[bold red]{label} must be an absolute path:[/] {path}")
        raise typer.Exit(code=1)
    return expanded.resolve()


@app.command()
def export(
    ctx: typer.Context,
    graph_path: Path | None = typer.Argument(
        None,
        help="Path to the Logseq graph root.",
    ),
    output_path: Path = typer.Argument(..., help="Output directory for exported artifacts."),
    format: ExportFormat = typer.Option(ExportFormat.JSON, "--format", "-f", help="Export format."),
) -> None:
    """Parse an entire graph and export it to the selected format."""
    resolved_graph = _resolve_graph_path(ctx, graph_path)

    if format is ExportFormat.LANGCHAIN_ENRICHED:
        from logseq_matryca_parser.graph import LogseqGraph

        graph = LogseqGraph.load_directory(resolved_graph)
        if not graph.pages:
            console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
            raise typer.Exit(code=0)
        output_path.mkdir(parents=True, exist_ok=True)
        try:
            destination, chunk_count = export_langchain_enriched(graph, output_path)
        except ImportError:
            console.print(
                "[bold red]Missing AI export dependencies.[/] Please install them using: "
                "[cyan]uv sync --extra ai[/]"
            )
            raise typer.Exit(1) from None
        console.print(
            f"[bold green]Synthesized[/] [cyan]{chunk_count}[/] contextual chunks; "
            f"[bold green]written to[/] {destination}"
        )
        return

    if format is ExportFormat.OBSIDIAN:
        from logseq_matryca_parser.graph import LogseqGraph

        graph = LogseqGraph.load_directory(resolved_graph)
        if not graph.pages:
            console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
            raise typer.Exit(code=0)
        output_path.mkdir(parents=True, exist_ok=True)
        file_count = export_obsidian(graph, output_path)
        console.print(
            f"[bold green]Obsidian vault export completed:[/] [cyan]{file_count}[/] markdown "
            f"files under {output_path.resolve()}"
        )
        return

    pages = _canonical_pages_from_graph(resolved_graph)
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    output_path.mkdir(parents=True, exist_ok=True)

    if format is ExportFormat.JSON:
        destination = export_json(pages, output_path)
    elif format is ExportFormat.MARKDOWN:
        destination = export_markdown(pages, output_path)
    else:
        try:
            destination = export_langchain(pages, output_path)
        except ImportError:
            console.print(
                "[bold red]Missing AI export dependencies.[/] Please install them using: "
                "[cyan]uv sync --extra ai[/]"
            )
            raise typer.Exit(1) from None

    console.print(f"[bold green]Export completed:[/] {destination}")


from logseq_matryca_parser import kinetic_commands as _kinetic_commands  # noqa: F401

if __name__ == "__main__":
    app()
