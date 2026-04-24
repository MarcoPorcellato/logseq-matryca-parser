"""
Logseq Matryca Parser - SYNAPSE ADAPTER
---------------------------------------
Author: Marco Porcellato (Matryca.ai)
License: Apache 2.0

Descrizione: Il modulo Synapse funge da ponte (sinapsi) tra l'AST Logos 
e gli ecosistemi AI standard come LangChain.
"""
from typing import List, Dict, Any
from pathlib import Path

# Nota: Queste dipendenze sono standard nel mondo RAG
try:
    from langchain_core.documents import Document
except ImportError:
    # Fallback se LangChain non è installato (per mantenere il core leggero)
    Document = None

from .logos_core import LogosNode
from .logos_parser import LogosParser

class SynapseAdapter:
    """Trasforma la gerarchia Logos in oggetti pronti per i framework AI."""

    @staticmethod
    def to_langchain_documents(nodes: List[LogosNode], source_name: str) -> List['Document']:
        """
        Converte ricorsivamente i nodi Logos in una lista di LangChain Documents.
        Ogni blocco Logseq diventa un'unità atomica arricchita da metadati gerarchici.
        """
        if Document is None:
            raise ImportError("LangChain non rilevato. Installa 'langchain-core' per usare Synapse.")

        documents = []

        def _traverse(node_list: List[LogosNode]):
            for node in node_list:
                # Costruzione dei metadati: l'anima del RAG avanzato
                metadata = {
                    "uuid": node.uuid,
                    "parent_id": node.parent_id,
                    "indent_level": node.indent_level,
                    "source": source_name,
                    **node.properties
                }

                # Creazione del Documento LangChain
                doc = Document(
                    page_content=node.content,
                    metadata=metadata
                )
                documents.append(doc)

                # Continua la ricorsione nell'albero
                if node.children:
                    _traverse(node.children)

        _traverse(nodes)
        return documents

    @classmethod
    def load_and_convert(cls, file_path: Path) -> List['Document']:
        """
        Utility high-level: legge un file via LogosParser e lo sputa fuori 
        direttamente come lista di Documenti LangChain.
        """
        parser = LogosParser()
        nodes = parser.parse_file(file_path)
        return cls.to_langchain_documents(nodes, source_name=file_path.name)