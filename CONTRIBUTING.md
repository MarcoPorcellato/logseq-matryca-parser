# 🔱 Contributing to the Logos Protocol

First off, thank you for considering contributing to the **Logseq Matryca Parser (Logos Protocol)**! 

This repository is the foundational AST engine for [Matryca.ai](https://matryca.ai), designed to preserve the spatial hierarchy of thought in Logseq graphs. We value deterministic logic, strict typing, and high performance.

To maintain the architectural integrity of the project, please follow the guidelines below.

---

## 🏛️ Architectural Philosophy

Before writing any code, please understand our core principles:
1. **The Graph is Sacred:** Logos does not guess or chunk text arbitrarily. It reconstructs the exact hierarchical tree based on spatial indentation.
2. **Deterministic Output:** Given the same `.md` file, the parser must *always* produce the exact same AST and identical UUIDs.
3. **No Bloat:** We strictly limit external dependencies to maximize compatibility with AOT compilers (like Nuitka) and ensure blazing-fast execution.

*Note: The `logos_core.py` module is the beating heart of the protocol. If your PR proposes changes to the Pydantic V2 models within it, please open an Issue for discussion first.*

---

## 🛠️ Development Setup

To set up your local environment:

1. **Fork and Clone:**
   ```bash
   git clone [https://github.com/YOUR-USERNAME/logseq-matryca-parser.git](https://github.com/YOUR-USERNAME/logseq-matryca-parser.git)
   cd logseq-matryca-parser