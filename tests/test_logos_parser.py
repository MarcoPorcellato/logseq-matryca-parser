from pathlib import Path
from logseq_matryca_parser.logos_parser import LogosParser

def test_logos_parser_indentation_hierarchy(tmp_path: Path):
    """
    Verifica che il LogosParser costruisca correttamente l'AST e le relazioni 
    parent_id per 3 livelli di indentazione spaziale.
    """
    # Contenuto Markdown con 3 livelli di indentazione (oltre alla root)
    # Root (0 spazi)
    #   Livello 1 (2 spazi)
    #     Livello 2 (4 spazi)
    #       Livello 3 (6 spazi)
    md_content = """- Root Node
  - Child 1
    - Child 2
      - Child 3
"""
    
    test_file = tmp_path / "test.md"
    test_file.write_text(md_content, encoding="utf-8")
    
    parser = LogosParser(tab_size=2)
    roots = parser.parse_file(test_file)
    
    # Ci aspettiamo un solo nodo radice
    assert len(roots) == 1
    root_node = roots[0]
    
    # Verifica Root Node
    assert root_node.content == "Root Node"
    assert root_node.indent_level == 0
    assert root_node.parent_id is None
    assert len(root_node.children) == 1
    
    # Verifica Child 1
    child_1 = root_node.children[0]
    assert child_1.content == "Child 1"
    assert child_1.indent_level == 1
    assert child_1.parent_id == root_node.uuid
    assert len(child_1.children) == 1
    
    # Verifica Child 2
    child_2 = child_1.children[0]
    assert child_2.content == "Child 2"
    assert child_2.indent_level == 2
    assert child_2.parent_id == child_1.uuid
    assert len(child_2.children) == 1
    
    # Verifica Child 3
    child_3 = child_2.children[0]
    assert child_3.content == "Child 3"
    assert child_3.indent_level == 3
    assert child_3.parent_id == child_2.uuid
    assert len(child_3.children) == 0
