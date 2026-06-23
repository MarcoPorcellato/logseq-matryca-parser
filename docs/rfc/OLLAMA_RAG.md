# RFC: Ollama one-click local RAG

> **Status:** Draft placeholder — full design tracked in [GitHub issue #34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34). Contributions welcome.

## Problem

README roadmap lists **Ollama Integration: One-click local RAG setup**. Users want a sovereign pipeline: local Logseq vault → structured chunks → local embeddings → Ollama chat — without cloud lock-in.

## Proposed scope (to refine)

| Layer | Role |
| :--- | :--- |
| **LOGOS + SYNAPSE** | Parse vault; export LangChain/LlamaIndex documents with lineage metadata |
| **Embeddings** | Ollama embedding API or pluggable local model |
| **Vector store** | User choice (Chroma, LanceDB, etc.) — out of core package |
| **CLI / script** | Thin wrapper: `matryca-parse export … --format langchain` + sample pipeline script |

## Non-goals

- Hosted inference or telemetry
- Replacing Logseq desktop
- Bundling Ollama binary inside this package

## Open questions

1. Ship a `examples/ollama_rag.py` or a new `matryca-parse` subcommand?
2. Minimum `[ai]` extra vs dedicated `[ollama]` extra?
3. Default chunk strategy: one block per `Document` (current SYNAPSE default) vs enriched chunks?

## Next steps

1. Comment on [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34) with use cases.
2. Split implementation into follow-up issues after RFC approval.
