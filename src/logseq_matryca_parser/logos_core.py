"""
Logseq Matryca Parser - LOGOS CORE
Author: Marco Porcellato (Matryca.ai)
License: Apache 2.0
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

class LogosNode(BaseModel):
    """Nodo fondamentale del Protocollo Logos."""
    model_config = ConfigDict(strict=True)

    uuid: str = Field(..., description="UUID Logseq")
    content: str = Field(..., description="Testo raw")
    indent_level: int = Field(..., description="Livello topologico")
    properties: Dict[str, str] = Field(default_factory=dict)
    parent_id: Optional[str] = None
    children: List["LogosNode"] = Field(default_factory=list)

    def add_child(self, node: "LogosNode"):
        self.children.append(node)

LogosNode.model_rebuild()