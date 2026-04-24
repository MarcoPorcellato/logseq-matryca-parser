"""
Logos Protocol - Unit Tests
---------------------------
Author: Marco Porcellato (Matryca.ai)

Test suite per verificare il determinismo gerarchico e spaziale del motore FSM.
"""
import pytest
from pathlib import Path
from logseq_matryca_parser.logos_parser import LogosParser

# Fixture: creiamo un file temporaneo simulando un grafo Logseq complesso
@pytest.fixture
def mock_logseq_file(tmp_path: Path) -> Path:
    content = """- Nodo Radice A
  - Figlio A1
    - Nipote A1.1
  - Figlio A2
- Nodo Radice B
  id:: 1234-abcd
  - Figlio B1
    custom_prop:: value123
"""
    file_path = tmp_path / "test_graph.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path

def test_ast_hierarchy(mock_logseq_file: Path):
    """Verifica che l'albero padre-figlio venga ricostruito correttamente."""
    parser = LogosParser(tab_size=2)
    roots = parser.parse_file(mock_logseq_file)
    
    # 1. Verifica Radici
    assert len(roots) == 2, "Dovrebbero esserci esattamente 2 nodi radice"
    assert roots[0].content == "Nodo Radice A"
    assert roots[1].content == "Nodo Radice B"
    
    # 2. Verifica Figli e Nipoti (Profondità)
    figlio_a1 = roots[0].children[0]
    assert figlio_a1.content == "Figlio A1"
    assert len(figlio_a1.children) == 1
    
    nipote = figlio_a1.children[0]
    assert nipote.content == "Nipote A1.1"
    assert nipote.parent_id == figlio_a1.uuid

def test_property_extraction(mock_logseq_file: Path):
    """Verifica che le properties (id::, custom::) vengano separate dal testo."""
    parser = LogosParser(tab_size=2)
    roots = parser.parse_file(mock_logseq_file)
    
    radice_b = roots[1]
    figlio_b1 = radice_b.children[0]
    
    # L'id nativo deve sovrascrivere l'UUID generato
    assert radice_b.uuid == "1234-abcd"
    
    # La property custom deve finire nel dizionario properties, non nel testo
    assert "custom_prop" in figlio_b1.properties
    assert figlio_b1.properties["custom_prop"] == "value123"
    assert "custom_prop::" not in figlio_b1.content