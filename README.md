# 🔱 Logseq Matryca Parser (The Logos Protocol)

[![CI/CD Status](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)](#)
![Origin: Matryca.ai](https://img.shields.io/badge/Origin-Matryca.ai-gold?style=for-the-badge)

> **"Turning a forest of local plain-text files into a unified semantic powerhouse."**

<p align="center">
  <video src="https://github.com/user-attachments/assets/24f73c6d-3eca-4adb-8442-981f2ba4cccd" autoplay loop muted playsinline width="800"></video>
</p>

[👉 **TRY THE LIVE INTERACTIVE DEMO**](https://MarcoPorcellato.github.io/logseq-matryca-parser/) 

[📘 **READ THE ARCHITECTURE (LLM OS Vision)**](docs/ARCHITECTURE.md)

---

## 🌐 The Vision: Virtual Centralization vs. Binary Lock-in

The PKM (Personal Knowledge Management) world is currently forcing users to make a painful choice between **Data Longevity** and **AI Power**. 

* **Vanilla Logseq / Obsidian** is a "Forest" of decentralized Markdown files. It guarantees the Lindy effect (plain-text lasts forever) and perfect Git versioning, but standard AI chunkers treat it like a blender, destroying the outliner hierarchy.
* **Tana** is a centralized "Tree". It offers incredible semantic power, but traps your brain in a proprietary cloud database.
* **The new Logseq DB (SQLite)** aims for database speed, but at a huge cost: it locks your notes inside a binary `.db` file. You lose human-readable files, you lose line-by-line Git diffs, and you lose the immortality of plain-text.

### 🔱 The Matryca Solution: The Best of Both Worlds
**Logseq Matryca Parser** is the ultimate bridge. It allows you to **keep your sovereign, future-proof Markdown files**, while synthesizing a **Virtual Global Graph** in RAM at runtime.

It acts as the strict **File System Driver** for your LLM OS. By using a deterministic Stack-Machine to parse your outliner topology, it feeds LangChain or LlamaIndex with the exact parent-child context of every single block. 

*You get the reasoning power of a centralized relational database, without sacrificing the plain-text soul of your Second Brain in Logseq.*

---

## ⚖️ The PKM Landscape

| Feature | Vanilla Markdown | **Matryca Parser** | Logseq DB (SQLite) | Tana |
| :--- | :--- | :--- | :--- | :--- |
| **Data Format** | Plain-text (.md) | **Plain-text (.md)** | Binary (.db) | Proprietary Cloud |
| **Version Control** | Perfect (Git) | **Perfect (Git)** | Poor (Binary blob) | None |
| **Data Structure** | Decentralized Forest | **Virtually Centralized Graph** | Relational Database | Centralized Tree |
| **AI Readiness** | Low (Linear Chunks) | **High (Topological AST)** | TBD (Requires SQL) | High (Proprietary) |
| **Sovereignty** | 100% Local | **100% Local (Sovereign AI)** | 100% Local | Cloud-Only |

---

### 🚀 The Problem
Standard RAG pipelines treat your notes like a blender. They chop Markdown into random shards, destroying the **parent-child hierarchy** that makes Logseq powerful.

### 🔱 The Solution
Logseq Matryca Parser is a deterministic **Stack-Machine engine** that acts as the **File System Driver** for your LLM. It preserves the true topology of your thoughts, ensuring AI understands spatial hierarchy, time, and block-lineage.

---

## 🏗️ Core Capabilities

| Feature | Description |
| :--- | :--- |
| **LOGOS Engine** | Deterministic AST parsing. No regex-guessing. Handles `id::`, aliases, and multiline blocks. |
| **SYNAPSE Adapter** | Native exports for **LangChain** and **LlamaIndex** with automated lineage metadata. |
| **LENS Visualizer** | 60FPS interactive graph rendering (10k+ nodes) with Glassmorphism HUD. |
| **Sovereign AI** | 100% Local. Zero telemetry. Private by design. |

---

## 🛠️ Quickstart

```bash
# Install from GitHub (not yet published to PyPI)
pip install git+https://github.com/MarcoPorcellato/logseq-matryca-parser.git

# 1. Visualize your local graph (LENS)
matryca-parse visualize /path/to/logseq/graph my-map.html

# 2. Export for AI/RAG (SYNAPSE)
matryca-parse export /path/to/logseq/graph output --format langchain
```

### Python API
```python
from logseq_matryca_parser.logos_parser import LogosParser
from logseq_matryca_parser.synapse import SynapseAdapter

# Parse to AST
page = LogosParser().parse_page_file("page.md")

# Export to LangChain with lineage metadata
docs = SynapseAdapter.to_langchain_documents(page.root_nodes)
```

### 🤖 Agentic Write Access (Append-Only)

Agents such as Hermes or OpenClaw can record structured notes into a Logseq graph **without rewriting existing pages**. The helper `logseq_agent_write` only **opens the weekly agent page in append mode** (`"a"`), writes a new bullet (journal link + optional tag links + body), and never truncates or replaces prior content—so routine logging cannot wipe blocks that already live in that file.

Point it at your graph’s **`pages`** directory and **`config.edn`** so journal titles match Logseq’s `:journal/page-title-format` (including ordinal days when you use `do` in the pattern).

```python
from logseq_matryca_parser import logseq_agent_write

result = logseq_agent_write(
    "Summarized user intent and proposed next steps.",
    config_path="/path/to/logseq/config.edn",
    pages_dir="/path/to/logseq/pages",
    context_tags=["agent/hermes", "#session"],
)
assert result["status"] == "success"
# result["path"] → e.g. .../pages/2026-18-agent.md
```
---

## 🗺️ Roadmap
- [ ] **Desktop GUI:** Standalone app for non-technical users. [(Join the RFC)](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/3)
- [ ] **Obsidian Adapter:** Native export for Obsidian vaults.
- [ ] **Ollama Integration:** One-click local RAG setup.

## ☕ Support & Enterprise
Logseq Matryca Parser is open-source. If it powers your pipeline, consider a star ⭐ or a sponsorship!

**💖 [Sponsor me on GitHub](https://github.com/sponsors/MarcoPorcellato)**

Need custom RAG integrations or consulting? Contact: [marco@marcoporcellato.it](mailto:marco@marcoporcellato.it)

---
Architected by **Marco Porcellato** | Powered by **Matryca.ai**
