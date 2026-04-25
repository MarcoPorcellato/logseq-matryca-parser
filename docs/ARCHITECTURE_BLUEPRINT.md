# Logseq Sovereign Parser - Architectural Blueprint

## 1. Core Objective & Problem Statement
- [cite_start]**Objective:** Develop a deterministic, AST-preserving, local-first Logseq parser in Python 3.12+ for enterprise RAG systems.
- [cite_start]**The Problem:** Standard RAG text-splitters and regex-based parsers fail to handle Logseq's indentation-based hierarchy. [cite_start]They suffer from multiline blindness, lookbehind vulnerabilities, and destroy the topological parent-child semantic relationships.
- [cite_start]**The Solution:** Abandon regex for structural parsing. [cite_start]Implement a strict Stack-Machine (Finite State Machine) with O(N) complexity that uses spatial indentation to build a rigorous Abstract Syntax Tree (AST).

## 2. The Pantheon Architecture (Modules)
[cite_start]The library is structured into four hermetic modules, utilizing the **Visitor Pattern** for AST traversal[cite: 1, 3]:
1. **LOGOS (Core):** Pydantic V2 strict models (`LogseqNode`, `LogseqPage`) and the Stack-Machine parser. [cite_start]Uses `LogseqNode.model_rebuild()` to ensure Ahead-Of-Time (AOT) Nuitka compatibility.
2. [cite_start]**SYNAPSE (Adapters):** Integrations for AI frameworks (LangChain `BaseLoader` lazy loading, LlamaIndex `NodeRelationship` injection) implemented via `ASTVisitor`.
3. [cite_start]**FORGE (Exporters):** Serialization engine to export the AST into structured JSON or clean "Flat-Markdown" for LLM context ingestion.
4. **KINETIC (CLI):** POSIX-compliant command-line interface built with `Typer` and `Rich`. [cite_start]Strict separation: telemetry/progress on `stderr`, data payload on `stdout` (piping ready).

## 3. Data Structures & Strict Typing
- [cite_start]**LogseqNode Attributes:** `uuid`, `content`, `clean_text` (purged of properties for vector embeddings), `indent_level`, `properties`, `wikilinks`, `tags`, `block_refs`, `parent_id`, and `children`.
- [cite_start]**State Machine States:** Push (Nesting), Maintain (Sibling), Pop (Ascending) based on white-space indentation tracking.

## 4. Compilation & Deployment Constraints
- **AOT Ready:** Code must be ready for Nuitka C++ compilation. [cite_start]No dynamic imports (`importlib`), strict static typing, and no fork-bombing architectures.
- [cite_start]**Toolchain:** `uv` for fast dependency resolution and `hatchling` as the build backend in `pyproject.toml`[cite: 1, 3].