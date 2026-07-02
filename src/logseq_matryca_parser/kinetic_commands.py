"""KINETIC Typer subcommands (SRP slice — scan, visualize, agent CLI)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.table import Table

from logseq_matryca_parser import logseq_agent_write
from logseq_matryca_parser.kinetic import (
    _build_official_logseq_demo_pages,
    _iter_nodes,
    _require_absolute_path,
    _resolve_graph_path,
    app,
    console,
)
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph


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


def _build_broken_references_table(
    graph: LogseqGraph, broken_nodes: list[LogseqNode]
) -> Table:
    table = Table(title="Broken Block References")
    table.add_column("Page", style="cyan")
    table.add_column("Block UUID", style="magenta")
    table.add_column("Missing Block Ref", style="bold red")

    for node in broken_nodes:
        page = graph.page_for_node(node)
        page_title = page.title if page is not None else "<unknown>"
        missing_refs = [
            ref for ref in node.block_refs if graph.get_node_by_embed_ref(ref) is None
        ]
        table.add_row(
            page_title,
            node.uuid,
            ", ".join(f"(({ref}))" for ref in missing_refs),
        )
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


@app.command()
def scan(
    ctx: typer.Context,
    graph_path: Path | None = typer.Argument(
        None,
        help="Path to the Logseq graph root.",
    ),
    broken_refs: bool = typer.Option(
        False,
        "--broken-refs",
        help="Print unresolved block references and exit 1 when any are found.",
    ),
) -> None:
    """Scan a graph and print aggregate parsing statistics."""
    resolved = _resolve_graph_path(ctx, graph_path)

    from logseq_matryca_parser.graph import LogseqGraph

    graph = LogseqGraph.load_directory(resolved)
    pages = list(graph.iter_canonical_pages())
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    console.print(_build_stats_table(pages))

    if broken_refs:
        broken = graph.get_broken_references()
        if not broken:
            console.print("[green]No unresolved block references found.[/]")
            raise typer.Exit(code=0)

        console.print("")
        console.print(_build_broken_references_table(graph, broken))
        raise typer.Exit(code=1)


@app.command()
def visualize(
    ctx: typer.Context,
    graph_path: Path | None = typer.Argument(
        None,
        help="Path to the Logseq graph root.",
    ),
    output_html: Path = typer.Argument(..., help="Output HTML path for network visualization."),
) -> None:
    """Parse a graph, compute deep topology stats, and export an interactive HTML network."""
    resolved = _resolve_graph_path(ctx, graph_path)

    from logseq_matryca_parser.graph import LogseqGraph

    loaded = LogseqGraph.load_directory(resolved)
    pages = list(loaded.iter_canonical_pages())
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    try:
        from logseq_matryca_parser.lens import GraphVisualizer

        visualizer = GraphVisualizer(pages=pages, graph=loaded)
    except ImportError:
        console.print(
            "[bold red]Missing visualization dependencies.[/] Please install them using: "
            "[cyan]uv sync --extra viz[/]"
        )
        raise typer.Exit(1) from None

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
    ctx: typer.Context,
    output_html: Path = typer.Argument(
        Path("showcase.html"),
        help="Path for the standalone showcase HTML (default: showcase.html in cwd).",
    ),
) -> None:
    """Build a sample graph from the official Logseq demo topology and write showcase HTML (no graph files read)."""
    _ = ctx
    pages = _build_official_logseq_demo_pages()
    try:
        from logseq_matryca_parser.lens import GraphVisualizer

        visualizer = GraphVisualizer(pages=pages)
    except ImportError:
        console.print(
            "[bold red]Missing visualization dependencies.[/] Please install them using: "
            "[cyan]uv sync --extra viz[/]"
        )
        raise typer.Exit(1) from None

    visualizer.build_network()
    visualizer.export_html(output_html.resolve())
    console.print(
        f"[bold green]Showcase example written:[/] {output_html.resolve()} "
        f"(open in a browser to preview the LENS graph)."
    )


@app.command()
def append(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="Markdown text to append to the agent file."),
    config: Path = typer.Option(
        ...,
        "--config",
        help="Absolute path to the Logseq config.edn file.",
        metavar="PATH",
    ),
    pages: Path = typer.Option(
        ...,
        "--pages",
        help="Absolute path to the Logseq pages directory.",
        metavar="PATH",
    ),
    tags: list[str] = typer.Option(
        [],
        "--tags",
        help="Optional context tags for the block (repeat for multiple).",
    ),
) -> None:
    """Append a block to the weekly agent page via logseq_agent_write."""
    _ = ctx
    config_path = _require_absolute_path(config, "--config")
    pages_dir = _require_absolute_path(pages, "--pages")

    result = logseq_agent_write(
        content,
        str(config_path),
        str(pages_dir),
        context_tags=tags or None,
    )

    if result.get("status") == "success":
        path_str = result.get("path", "")
        console.print(
            f"[bold green]Appended to agent page:[/] {path_str}",
            no_wrap=True,
            overflow="ignore",
            crop=False,
        )
        return

    message = result.get("message", "Unknown error.")
    console.print(f"[bold red]Append failed:[/] {message}")
    raise typer.Exit(code=1)


@app.command()
def agent_read(
    ctx: typer.Context,
    graph_path: Path | None = typer.Argument(
        None,
        help="Path to the Logseq graph root.",
    ),
    tag: str | None = typer.Option(None, "--tag", help="Filter nodes by tag."),
    query: str | None = typer.Option(None, "--query", help="Substring search on clean_text."),
) -> None:
    """Load a graph, filter nodes, and print ultra-dense X-Ray text to stdout (no Rich)."""
    resolved = _resolve_graph_path(ctx, graph_path)
    from logseq_matryca_parser.agent_press import (
        XRAY_STATE_FILENAME,
        SessionAliasRegistry,
        to_xray_markdown,
    )
    from logseq_matryca_parser.graph import LogseqGraph

    graph = LogseqGraph.load_directory(resolved)
    if tag is not None:
        nodes = graph.query().has_tag(tag).execute()
    elif query is not None:
        nodes = graph.search_content(query)
    else:
        nodes = graph.query().execute()

    registry = SessionAliasRegistry()
    registry.generate_aliases(nodes)
    state_path = resolved / XRAY_STATE_FILENAME
    registry.save_to_disk(state_path)

    output = to_xray_markdown(nodes, registry)
    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")


@app.command("agent-write")
def agent_write(
    ctx: typer.Context,
    graph_path: Path | None = typer.Argument(
        None,
        help="Path to the Logseq graph root.",
    ),
    content: str = typer.Option(..., "--content", help="Markdown body for the new child bullet."),
    alias: int | None = typer.Option(
        None,
        "--alias",
        help="Session alias from a prior agent-read (resolved via .matryca_xray_state.json).",
    ),
    target_uuid: str | None = typer.Option(
        None,
        "--target-uuid",
        help="Parent block UUID (bypasses alias registry).",
    ),
    state_file: Path | None = typer.Option(
        None,
        "--state-file",
        help="Alias registry JSON (default: <graph>/.matryca_xray_state.json).",
    ),
) -> None:
    """Append a child block under a parent via headless AST markdown splicing."""
    from logseq_matryca_parser.agent_press import XRAY_STATE_FILENAME, SessionAliasRegistry
    from logseq_matryca_parser.agent_writer import append_child_to_node
    from logseq_matryca_parser.graph import LogseqGraph

    resolved = _resolve_graph_path(ctx, graph_path)

    if alias is None and target_uuid is None:
        print("Provide --alias or --target-uuid.", file=sys.stderr)
        raise typer.Exit(code=1)
    if alias is not None and target_uuid is not None:
        print("Use only one of --alias or --target-uuid.", file=sys.stderr)
        raise typer.Exit(code=1)

    graph = LogseqGraph.load_directory(resolved)

    parent_uuid = target_uuid
    if alias is not None:
        registry_path = state_file or (resolved / XRAY_STATE_FILENAME)
        if not registry_path.is_file():
            print(f"Alias state file not found: {registry_path}", file=sys.stderr)
            raise typer.Exit(code=1)
        from logseq_matryca_parser.exceptions import SessionAliasRegistryError

        try:
            registry = SessionAliasRegistry.load_from_disk(registry_path)
        except SessionAliasRegistryError as exc:
            print(str(exc), file=sys.stderr)
            raise typer.Exit(code=1) from exc
        parent_uuid = registry.resolve_alias(alias)
        if parent_uuid is None:
            print(f"Unknown alias: {alias}", file=sys.stderr)
            raise typer.Exit(code=1)

    if parent_uuid is None:
        print("Parent block UUID could not be resolved.", file=sys.stderr)
        raise typer.Exit(code=1)
    try:
        append_child_to_node(graph, parent_uuid, content)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Appended child under[/] {parent_uuid}",
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
