"""
Logseq Matryca Parser - KINETIC CLI
-----------------------------------
Author: Marco Porcellato (Matryca.ai)
License: Apache 2.0

Descrizione: Interfaccia a riga di comando (CLI) ad alte prestazioni.
POSIX-compliant: telemetria su stderr, output dati puro su stdout.
"""
import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List

# Importiamo il motore e la fucina
from .logos_parser import LogosParser
from .forge import ForgeExporter

app = typer.Typer(
    name="matryca-parse",
    help="⚡ KINETIC: Il motore CLI del Protocollo Logos per Matryca.ai.",
    no_args_is_help=True,
    add_completion=False
)

# Separazione dei canali (Standard Enterprise)
err_console = Console(stderr=True)  # UI, Errori, Progress Bar
out_console = Console()             # JSON/Dati puri per il piping (| jq)

def version_callback(value: bool):
    if value:
        err_console.print("[bold gold1]Logos Protocol[/] v0.1.0 - Architected by Marco Porcellato")
        raise typer.Exit()

@app.command()
def extract(
    target: Path = typer.Argument(..., help="Path al file o directory Logseq (.md)"),
    format: str = typer.Option("json", "--format", "-f", help="Target format: json, md, flat"),
    output: Optional[Path] = typer.Option(None, "--out", "-o", help="File di destinazione (opzionale)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Attiva telemetria dettagliata")
):
    """
    Estrae l'AST dai file Markdown target e lo forgia nel formato richiesto.
    """
    if not target.exists():
        err_console.print(f"[bold red]❌ ERRORE:[/] Il target '{target}' non esiste nel filesystem.")
        raise typer.Exit(code=1)

    # Gestione file singolo o scansione directory
    files_to_parse: List[Path] = [target] if target.is_file() else list(target.rglob("*.md"))
    
    if not files_to_parse:
        err_console.print("[bold yellow]⚠️ VUOTO:[/] Nessun file Markdown trovato in questa locazione.")
        raise typer.Exit()

    if verbose:
        err_console.print(Panel(
            f"[bold gold1]⚡ KINETIC ENGINE - Avvio Protocollo Logos[/]\n"
            f"[cyan]Target:[/] {target}\n"
            f"[cyan]Formato:[/] {format.upper()}\n"
            f"[cyan]File Rilevati:[/] {len(files_to_parse)}",
            border_style="gold1"
        ))

    parser = LogosParser()
    results = []
    
    # UI Reattiva
    with Progress(
        SpinnerColumn(spinner_name="dots2"),
        TextColumn("[progress.description]{task.description}"),
        console=err_console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[cyan]Estrazione AST in corso su {len(files_to_parse)} file...", total=len(files_to_parse))
        
        for file_path in files_to_parse:
            if verbose:
                progress.print(f"[dim]Parsing: {file_path.name}[/dim]")
            
            # Motore LOGOS
            roots = parser.parse_file(file_path)
            
            # Motore FORGE
            if format.lower() == "json":
                artefatto = ForgeExporter.to_json(roots)
            elif format.lower() == "md":
                artefatto = ForgeExporter.to_clean_markdown(roots)
            elif format.lower() == "flat":
                import json
                artefatto = json.dumps(ForgeExporter.to_flat_list(roots), indent=2)
            else:
                err_console.print(f"[bold red]❌ Formato non supportato:[/] {format}")
                raise typer.Exit(code=1)

            results.append((file_path.name, artefatto, len(roots)))
            progress.advance(task)

    # Routing dell'Output
    if output:
        with open(output, "w", encoding="utf-8") as f:
            if len(results) == 1:
                f.write(results[0][1])
            else:
                # Merge per salvataggi massivi
                merged = ",\n".join([r[1] for r in results])
                f.write(f"[\n{merged}\n]")
        err_console.print(f"[bold green]✅ Estrazione completata.[/] Dati forgiati in [white]{output}[/]")
    else:
        # RAW Stdout per concatenazioni (Piping)
        for _, artefatto, _ in results:
            out_console.print(artefatto, highlight=False)

    # Telemetria finale
    if verbose:
        table = Table(title="Telemetria Logos", border_style="gold1", title_style="bold cyan")
        table.add_column("File Target", style="white")
        table.add_column("Nodi Radice (AST)", justify="right", style="bold green")
        for name, _, count in results:
            table.add_row(name, str(count))
        err_console.print(table)

@app.callback()
def main(version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, is_eager=True)):
    pass

if __name__ == "__main__":
    app()