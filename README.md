# 🔱 Logseq Matryca Parser (The Logos Protocol)

[![CI/CD Status](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)](#)
![Origin: Matryca.ai](https://img.shields.io/badge/Origin-Matryca.ai-gold?style=for-the-badge)

> **Giving LLMs the vision to read hierarchical thought.**

<p align="center">
  <video src="https://github.com/user-attachments/assets/24f73c6d-3eca-4adb-8442-981f2ba4cccd" autoplay loop muted playsinline width="800"></video>
</p>

[👉 **TRY THE LIVE INTERACTIVE DEMO**](https://MarcoPorcellato.github.io/logseq-matryca-parser/) 

[📘 **READ THE ARCHITECTURE (LLM OS Vision)**](docs/ARCHITECTURE.md)

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
# Install via pip or uv
pip install -e .

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