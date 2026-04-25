# 🔱 Logseq Sovereign Parser (English Translation)

![CI/CD Status](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/workflows/ci.yml/badge.svg)
![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)
![Author: Marco Porcellato](https://img.shields.io/badge/Author-Marco_Porcellato-purple?style=for-the-badge)
![Origin: Matryca.ai](https://img.shields.io/badge/Origin-Matryca.ai-gold?style=for-the-badge)

> "Giving LLMs the vision to read hierarchical thought."
> — *Marco Porcellato*

Standard RAG parsers destroy the semantic structure of Logseq. **Logseq Sovereign Parser** is the deterministic engine built at [Matryca.ai](https://matryca.ai) by **Marco Porcellato** to preserve the AST (Abstract Syntax Tree) of your graphs.

We guarantee that artificial intelligence understands spatial hierarchy, not just flat text.

## 🏗️ System Architecture

*Want to understand why standard parsing fails on Logseq? Read our [Logseq AST Primer](docs/logseq_ast_primer.md).*

* **LOGOS (Core):** Finite state parsing engine for indentation reconstruction.
* **SYNAPSE (Adapters):** Connectors for LangChain and LlamaIndex to power RAG systems.
* **FORGE (Exporters):** Transformation forge for optimized JSON and Markdown output.
* **KINETIC (CLI):** High-performance command-line interface.

## ⚖️ Why Logos?
Unlike traditional chunkers that "cut" text randomly, Logos respects the user's **thought sovereignty**, keeping parent-child block relationships intact.


🛡️ Sovereign & Privacy First
Designed to run locally. Zero telemetry. Zero training on your data. GDPR-compliant by EEA protocol design.

Architected by Marco Porcellato | Powered by Matryca.ai
Building the future of Sovereign Knowledge Management.

---


# 🔱 Logseq Sovereign Parser

![CI/CD Status](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/workflows/ci.yml/badge.svg)
![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)
![Author: Marco Porcellato](https://img.shields.io/badge/Author-Marco_Porcellato-purple?style=for-the-badge)
![Origin: Matryca.ai](https://img.shields.io/badge/Origin-Matryca.ai-gold?style=for-the-badge)

> "Diamo agli LLM la vista per leggere il pensiero gerarchico."
> — *Marco Porcellato*

I parser RAG standard distruggono la struttura semantica di Logseq. **Logseq Sovereign Parser** è il motore deterministico costruito in [Matryca.ai](https://matryca.ai) da **Marco Porcellato** per preservare l'AST (Abstract Syntax Tree) dei tuoi grafi. 

Garantiamo che l'intelligenza artificiale comprenda la gerarchia spaziale, non solo il testo piatto.

## 🏗️ Architettura del Sistema
* **LOGOS (Core):** Motore di parsing a stati finiti per la ricostruzione dell'indentazione.
* **SYNAPSE (Adapters):** Connettori per LangChain e LlamaIndex per alimentare i RAG.
* **FORGE (Exporters):** Fucina di trasformazione per output in JSON e Markdown ottimizzato.
* **KINETIC (CLI):** Interfaccia a riga di comando ad alte prestazioni.

## ⚖️ Perché Logos?
A differenza dei chunker tradizionali che "tagliano" il testo a caso, Logos rispetta la **sovranità del pensiero** dell'utente, mantenendo intatte le relazioni padre-figlio dei blocchi.


🛡️ Sovereign & Privacy First
Progettato per girare in locale. Zero telemetria. Zero training sui tuoi dati. GDPR-compliant per protocollo EEA.

Architected by Marco Porcellato | Powered by Matryca.ai
Costruiamo il futuro del Knowledge Management Sovrano.

---

