---
name: gitnexus-logseq-parser
description: >-
  GitNexus graph intelligence for logseq-matryca-parser (The Logos Protocol).
  Use before refactors on StackMachineParser, logseq_markdown serialization,
  LogseqGraph, SYNAPSE adapters, or KINETIC CLI. Requires indexed repo
  (make gitnexus-index). Complements grep and docs/design-docs/.
---

# GitNexus — logseq-matryca-parser

Grafo strutturale precomputato in `.gitnexus/` (LadybugDB). MCP server: `user-gitnexus`. Repo name: **`logseq-matryca-parser`**.

> Con 3+ repo indicizzati globalmente, passare sempre `repo: "logseq-matryca-parser"` su ogni tool MCP.

## Bootstrap (ogni sessione agente)

```
1. CallMcpTool list_repos → conferma logseq-matryca-parser (embeddings > 0)
2. FetchMcpResource gitnexus://repo/logseq-matryca-parser/context → staleness
3. (opz.) gitnexus://repo/logseq-matryca-parser/processes
```

Se `staleness.commitsBehind > 0`: `make gitnexus-index` dalla root del repo.

## Moduli chiave → query di partenza

| Area | File / simbolo | Query GitNexus suggerita |
|------|----------------|------------------------|
| Parser stack-machine | `StackMachineParser` in `logos_parser.py` | `query("stack machine parser indentation")` |
| AST core | `LogseqNode`, `LogseqPage` in `logos_core.py` | `context({ name: "LogseqNode" })` |
| Serialize round-trip | `serialize_logseq_page` in `logseq_markdown.py` | `impact({ target: "serialize_logseq_page", direction: "upstream" })` |
| Graph I/O | `LogseqGraph`, `LogseqGraphWatcher` in `graph.py` | `query("graph watcher debounce filesystem")` |
| RAG adapters | `SynapseAdapter`, `build_synapse_metadata` in `synapse.py` | `query("synapse llama index metadata")` |
| CLI | `kinetic.py` | `query("kinetic typer cli")` |
| Path encoding | `logseq_paths.py` | `context({ name: "encode_page_name" })` |
| Spec ground truth | `docs/design-docs/OFFICIAL_MLDOC_SPECS.md` | FTS su File node; leggere il file per edge-case |

## Ricette ad alto valore

### Refactor parser / serialization

1. `impact({ target: "<symbol>", direction: "upstream", summaryOnly: true, repo: "logseq-matryca-parser" })`
2. `context({ name: "<symbol>", repo: "logseq-matryca-parser" })` sui caller a rischio
3. Dopo edit: `detect_changes({ scope: "all", repo: "logseq-matryca-parser" })`

### Capire un flusso parse → AST → export

1. `query({ search_query: "parse page roundtrip", repo: "logseq-matryca-parser", goal: "execution flow" })`
2. Resource `gitnexus://repo/logseq-matryca-parser/process/{label}` per trace step-by-step

### Pre-commit / PR

```bash
make lint && make check
```

Poi MCP: `detect_changes({ scope: "compare", base_ref: "main", repo: "logseq-matryca-parser" })`.

## Re-index

```bash
make gitnexus-index          # embeddings + skip AGENTS.md/skills bundled
gitnexus analyze --force     # rebuild completo
gitnexus status              # verifica commit indicizzato
```

Config persistente: `.gitnexusrc` (`embeddings: true`, `skipAgentsMd`, `skipSkills`).

## Complementarità

| Strumento | Quando |
|-----------|--------|
| **GitNexus** | Call graph, blast radius, processi, diff impact |
| **grep / semantic search** | Stringhe letterali, test fixtures |
| **`docs/design-docs/`** | Spec normative e edge-case |
| **Understand** (`/understand`) | Wiki LLM-oriented — non sostituisce il grafo |

## Skill globale

Workflow generici e tool reference: `~/.cursor/skills/gitnexus-code-eval/SKILL.md`.

## Riferimenti

- [GitNexus README](https://github.com/abhigyanpatwari/GitNexus)
- [analyze command](https://abhigyanpatwari-gitnexus.mintlify.app/api/commands/analyze)
- [hybrid search](https://abhigyanpatwari-gitnexus.mintlify.app/concepts/hybrid-search)
