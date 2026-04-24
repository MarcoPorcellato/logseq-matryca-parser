"""
Logseq Matryca Parser - LOGOS ENGINE
------------------------------------
Author: Marco Porcellato (Matryca.ai)
License: Apache 2.0

Descrizione: Implementazione della Stack-based State Machine per 
l'estrazione deterministica dell'Abstract Syntax Tree (AST) da Logseq.
"""
import re
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from .logos_core import LogosNode

logger = logging.getLogger(__name__)

class LogosParser:
    """Motore di parsing FSM per il Protocollo Logos."""
    
    def __init__(self, tab_size: int = 2):
        self.tab_size = tab_size
        # Regex per catturare i bullet point spaziali
        self.bullet_regex = re.compile(r'^(\s*)[-\*]\s+(.*)')
        # Regex per estrarre l'ID nativo di Logseq (block properties)
        self.id_regex = re.compile(r'id::\s*([a-f0-9\-]+)')
        # Regex generica per le properties (es. title:: , custom::)
        self.prop_regex = re.compile(r'^([a-zA-Z0-9_-]+)::\s*(.*)')

    def _generate_deterministic_uuid(self, context: str, text: str) -> str:
        """Genera un UUID stabile per i blocchi che non hanno un ID nativo."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"matryca.ai/logos/{context}/{text}"))

    def parse_file(self, path: Path) -> List[LogosNode]:
        """
        Legge un file Markdown di Logseq e restituisce l'AST come lista di nodi root.
        """
        if not path.exists():
            raise FileNotFoundError(f"Pergamena non trovata: {path}")

        content = path.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning(f"Il file {path} è vuoto.")
            return []

        lines = content.splitlines()
        
        # Rilevamento automatico dell'indentazione a tab
        uses_tabs = any(line.startswith('\t') for line in lines if line.strip())
        current_tab_size = 1 if uses_tabs else self.tab_size
        
        stack: List[LogosNode] = []
        roots: List[LogosNode] = []
        current_node: Optional[LogosNode] = None

        for line in lines:
            if not line.strip():
                continue
            
            match = self.bullet_regex.match(line)
            if match:
                # 1. Calcolo livello topologico
                indentation = match.group(1)
                indent_count = indentation.count('\t') if uses_tabs else len(indentation)
                level = indent_count // current_tab_size
                raw_text = match.group(2)
                
                # 2. Generazione o Estrazione ID
                id_match = self.id_regex.search(raw_text)
                node_uuid = id_match.group(1) if id_match else self._generate_deterministic_uuid(path.stem, raw_text)
                
                new_node = LogosNode(
                    uuid=node_uuid,
                    content=raw_text,
                    indent_level=level
                )
                
                # 3. State Machine: Risalita (Pop) se torniamo indietro nell'indentazione
                while stack and stack[-1].indent_level >= level:
                    stack.pop()
                    
                # 4. State Machine: Assegnazione Parent (Push)
                if stack:
                    new_node.parent_id = stack[-1].uuid
                    stack[-1].add_child(new_node)
                else:
                    roots.append(new_node)
                    
                stack.append(new_node)
                current_node = new_node
                
            else:
                # 5. Gestione Multi-linea e Properties
                if current_node:
                    prop_match = self.prop_regex.match(line.strip())
                    if prop_match:
                        key, val = prop_match.groups()
                        current_node.properties[key] = val
                        
                        # Se la property è un ID di Logseq, sovrascriviamo l'UUID generato a caso
                        if key == "id":
                            current_node.uuid = val
                        
                        # IMPORTANTE: Non accodiamo questa riga a current_node.content!
                    else:
                        # È testo multi-linea normale, lo accodiamo
                        current_node.content += f"\n{line}"

        return roots