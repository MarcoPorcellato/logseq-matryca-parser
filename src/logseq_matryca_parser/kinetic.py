"""KINETIC command line interface for Logseq graph parsing."""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logseq_matryca_parser.graph import LogseqGraph

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from logseq_matryca_parser import logseq_agent_write
from logseq_matryca_parser.forge import ForgeExporter
from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from logseq_matryca_parser.logos_parser import LogosParser
from logseq_matryca_parser.logseq_paths import discover_graph_files
from logseq_matryca_parser.synapse import SynapseAdapter

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


def _parse_graph(graph_path: Path) -> list[LogseqPage]:
    parser = LogosParser()
    files = discover_graph_files(graph_path)
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


def _canonical_pages_from_graph(graph_path: Path) -> list[LogseqPage]:
    """Load a graph directory and return deduplicated canonical pages for export."""
    from logseq_matryca_parser.graph import LogseqGraph

    graph = LogseqGraph.load_directory(graph_path)
    return list(graph.iter_canonical_pages())


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
def scan(
    ctx: typer.Context,
    graph_path: Path | None = typer.Argument(
        None,
        help="Path to the Logseq graph root.",
    ),
) -> None:
    """Scan a graph and print aggregate parsing statistics."""
    resolved = _resolve_graph_path(ctx, graph_path)

    pages = _canonical_pages_from_graph(resolved)
    if not pages:
        console.print("[yellow]No Markdown files found under pages/ or journals/.[/]")
        raise typer.Exit(code=0)

    console.print(_build_stats_table(pages))


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


def _export_langchain_enriched(graph: LogseqGraph, output_path: Path) -> tuple[Path, int]:
    """Serialize context-enriched LangChain documents for the full loaded graph."""
    all_roots: list[LogseqNode] = []
    for page in graph.iter_canonical_pages():
        all_roots.extend(page.root_nodes)
    docs = SynapseAdapter.to_context_enriched_chunks(all_roots, graph)
    payload: list[dict[str, Any]] = [
        {"page_content": doc.page_content, "metadata": doc.metadata} for doc in docs
    ]
    destination = output_path / "langchain_enriched.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination, len(payload)


def _page_tree_contains_node_uuid(roots: list[LogseqNode], needle_uuid: str) -> bool:
    for node in roots:
        if node.uuid == needle_uuid:
            return True
        if node.children and _page_tree_contains_node_uuid(node.children, needle_uuid):
            return True
    return False


def _safe_obsidian_vault_relative_path(page_title: str) -> Path:
    segments = [
        re.sub(r'[<>:"|?*\\]', "_", segment) for segment in page_title.split("/") if segment
    ]
    if not segments:
        return Path("untitled.md")
    *parents, leaf = segments
    if not parents:
        return Path(f"{leaf}.md")
    return Path(*parents) / f"{leaf}.md"


def _export_obsidian(graph: LogseqGraph, output_path: Path) -> int:
    """Write one Obsidian-compatible Markdown file per page (namespace folders)."""
    pages_list = list(graph.iter_canonical_pages())
    targets = ForgeExporter.vault_wide_embed_targets(pages_list)
    suffix_map = ForgeExporter.build_vault_obsidian_suffix_map(
        pages_list,
        vault_wide_ref_targets=targets,
    )

    def embed_resolver(ref: str) -> tuple[str, str] | None:
        node = graph.get_node_by_embed_ref(ref)
        if node is None:
            return None
        for page in pages_list:
            if _page_tree_contains_node_uuid(page.root_nodes, node.uuid):
                anchor = suffix_map.get(node.uuid, node.uuid.replace("-", "")[:8])
                return page.title, anchor
        return None

    count = 0
    for page in pages_list:
        props = {**page.properties, "title": page.title}
        md = ForgeExporter.to_obsidian_markdown(
            page.root_nodes,
            props,
            embed_resolver=embed_resolver,
            global_suffix_map=suffix_map,
            vault_wide_ref_targets=targets,
        )
        rel = _safe_obsidian_vault_relative_path(page.title)
        out_file = output_path / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(md, encoding="utf-8")
        count += 1
    return count


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
            destination, chunk_count = _export_langchain_enriched(graph, output_path)
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
        file_count = _export_obsidian(graph, output_path)
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
        destination = _export_json(pages, output_path)
    elif format is ExportFormat.MARKDOWN:
        destination = _export_markdown(pages, output_path)
    else:
        try:
            destination = _export_langchain(pages, output_path)
        except ImportError:
            console.print(
                "[bold red]Missing AI export dependencies.[/] Please install them using: "
                "[cyan]uv sync --extra ai[/]"
            )
            raise typer.Exit(1) from None

    console.print(f"[bold green]Export completed:[/] {destination}")


def _require_absolute_path(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        console.print(f"[bold red]{label} must be an absolute path:[/] {path}")
        raise typer.Exit(code=1)
    return expanded.resolve()


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


if __name__ == "__main__":
    app()