"""
Logos Protocol - Live Demo Script
---------------------------------
Author: Marco Porcellato (Matryca.ai)
"""
import sys
from pathlib import Path

# Aggiunge la cartella 'src' al path di sistema per permettere l'import locale
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir / "src"))

try:
    from logseq_matryca_parser.logos_parser import LogosParser
    from logseq_matryca_parser.forge import ForgeExporter
    from rich.console import Console
    from rich.panel import Panel
except ImportError as e:
    print(f"Errore: Assicurati di aver installato le dipendenze (pip install rich typer pydantic). {e}")
    sys.exit(1)

console = Console()

def run_demo():
    # 1. Configurazione percorsi
    example_file = root_dir / "examples" / "demo_logseq_journal.md"
    
    console.print(Panel("[bold gold1]🔱 Logos Protocol - Live Extraction Demo[/]", expand=False))
    
    # 2. Inizializzazione Motore Logos
    console.print(f"[cyan]Reading file:[/] {example_file.name}...")
    parser = LogosParser()
    
    # 3. Parsing (Estrazione AST)
    try:
        ast_nodes = parser.parse_file(example_file)
        console.print(f"[green]✅ AST Extracted:[/] {len(ast_nodes)} root nodes identified.\n")
        
        # 4. Forgiatura (Output pulito per RAG)
        console.print("[bold]Forge Output (Clean Markdown for AI):[/]")
        console.print("=" * 40)
        
        clean_output = ForgeExporter.to_clean_markdown(ast_nodes)
        console.print(clean_output)
        
        console.print("=" * 40)
        console.print("\n[bold green]Success:[/] The hierarchy is intact and ready for RAG ingestion.")
        
    except Exception as e:
        console.print(f"[bold red]Error during parsing:[/] {e}")

if __name__ == "__main__":
    run_demo()