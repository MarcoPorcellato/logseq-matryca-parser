# 🔱 Logseq Matryca Parser (Logos Protocol)

![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge)
![Author: Marco_Porcellato](https://img.shields.io/badge/Author-Marco_Porcellato-purple?style=for-the-badge)
![Ecosystem: Matryca.ai](https://img.shields.io/badge/Ecosystem-Matryca.ai-gold?style=for-the-badge)

Il **Protocollo Logos** è il motore di estrazione dati deterministico creato per l'ecosistema [Matryca.ai](https://matryca.ai). Sviluppato da **Marco Porcellato**, questo parser trasforma il caos dei file Markdown di Logseq in un AST (Abstract Syntax Tree) puro, pronto per l'era dei Large Language Models.

## 🏗️ Architettura del Sistema
* **LOGOS (Core):** Motore di parsing a stati finiti per la ricostruzione dell'indentazione.
* **SYNAPSE (Adapters):** Connettori per LangChain e LlamaIndex per alimentare i RAG.
* **FORGE (Exporters):** Fucina di trasformazione per output in JSON e Markdown ottimizzato.
* **KINETIC (CLI):** Interfaccia a riga di comando ad alte prestazioni.

## ⚖️ Perché Logos?
A differenza dei chunker tradizionali che "tagliano" il testo a caso, Logos rispetta la **sovranità del pensiero** dell'utente, mantenendo intatte le relazioni padre-figlio dei blocchi.

---
**Architected by Marco Porcellato** | **Part of the Matryca.ai Intelligence Suite**