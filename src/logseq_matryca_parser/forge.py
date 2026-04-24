"""
Logseq Matryca Parser - FORGE EXPORTER
--------------------------------------
Author: Marco Porcellato (Matryca.ai)
License: Apache 2.0

Descrizione: La Fucina del Protocollo Logos. Converte l'AST in formati
ottimizzati per l'ingestione in sistemi RAG e AI.
"""
import json
from typing import List, Dict, Any
from .logos_core import LogosNode

class ForgeExporter:
    """Trasforma i nodi Logos in artefatti pronti per il consumo AI."""

    @staticmethod
    def to_json(nodes: List[LogosNode], indent: int = 2) -> str:
        """Esporta l'intero albero in un JSON strutturato."""
        return json.dumps([node.model_dump() for node in nodes], indent=indent)

    @staticmethod
    def to_flat_list(nodes: List[LogosNode]) -> List[Dict[str, Any]]:
        """
        Appiattisce l'albero in una lista di blocchi.
        Ogni blocco mantiene i metadati del genitore (parent_id) 
        per permettere ricostruzioni dinamiche nei vector store.
        """
        flat_list = []

        def _flatten(node_list: List[LogosNode]):
            for node in node_list:
                # Creiamo un dizionario con i dati del blocco escludendo i figli ricorsivi
                block_data = node.model_dump(exclude={'children'})
                flat_list.append(block_data)
                if node.children:
                    _flatten(node.children)

        _flatten(nodes)
        return flat_list

    @staticmethod
    def to_clean_markdown(nodes: List[LogosNode], depth: int = 0) -> str:
        """
        Genera un Markdown ottimizzato per RAG ("Clean-RAG").
        Preserva l'indentazione visiva ma pulisce il rumore sintattico
        inutile per gli embedding, facilitando la comprensione del contesto.
        """
        lines = []
        for node in nodes:
            # Crea l'indentazione spaziale basata sulla profondità reale nell'albero
            prefix = "  " * depth + "- "
            content = node.content.replace("\n", " ") # Normalizza i multi-linea in una sola riga per blocco
            lines.append(f"{prefix}{content}")
            
            # Aggiunge le proprietà se presenti (formattate per essere leggibili dall'AI)
            if node.properties:
                for k, v in node.properties.items():
                    if k != "id": # L'ID interno non serve all'LLM per la semantica
                        lines.append(f"  {'  ' * depth}  [:{k} {v}]")

            if node.children:
                lines.append(ForgeExporter.to_clean_markdown(node.children, depth + 1))
        
        return "\n".join(lines)
    