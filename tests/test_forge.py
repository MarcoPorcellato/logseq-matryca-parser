import pytest
from logseq_matryca_parser.logos_core import LogosNode
from logseq_matryca_parser.forge import ForgeExporter

@pytest.fixture
def sample_ast():
    root = LogosNode(uuid="123", content="Radice", indent_level=0)
    child = LogosNode(uuid="456", content="Figlio", indent_level=1, properties={"custom": "valore"})
    root.add_child(child)
    child.parent_id = root.uuid
    return [root]

def test_forge_clean_markdown(sample_ast):
    md_output = ForgeExporter.to_clean_markdown(sample_ast)
    assert "- Radice" in md_output
    assert "  - Figlio" in md_output
    assert "[:custom valore]" in md_output

def test_forge_flat_list(sample_ast):
    flat = ForgeExporter.to_flat_list(sample_ast)
    assert len(flat) == 2
    assert flat[1]["parent_id"] == "123"