# Local Code Audit — Maintainer Runbook

**Audience:** repository maintainers with a local Cursor / MCP setup  
**Public contract:** [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md) (generic "local code study" language)  
**Policy:** [`STATIC_ANALYSIS_POLICY.md`](STATIC_ANALYSIS_POLICY.md) — Ghost Tooling; **never** add local audit indexers to CI or `pyproject.toml`

This file describes **generic** graph-based code audit workflows. Do not copy vendor tool names into issues, PR descriptions, CHANGELOG bullets, or public docs.

---

## Graph-based code audit (primary indexer)

A **local code audit** indexer builds a knowledge graph over repositories: symbols, call chains ("processes"), import cycles, and impact radius.

### Prerequisites

1. Local code-audit MCP server enabled in Cursor (user-level MCP config — not committed to this repo).
2. Repository indexed locally (`logseq-matryca-parser` path on disk).
3. After large merges, refresh the index if `list_repos` reports `commitsBehind > 0`.

### Tool cheat sheet (generic MCP surface)

| Tool | When to use | Typical args |
|------|-------------|--------------|
| `list_repos` | Discover indexed repos; check staleness | `limit`, `offset` |
| `check` | Import cycle gate | `cycles: true`, `repo: "logseq-matryca-parser"` |
| `query` | Find execution flows for a concept | `search_query`, `task_context`, `repo` |
| `context` | 360° view of one symbol (callers/callees) | `name`, `file_path`, `repo` |
| `impact` | Blast radius before refactor | `target`, `direction: "upstream"`, `repo` |

### Standard audit pipeline (Logos)

```text
1. list_repos          → confirm logseq-matryca-parser indexed
2. check(cycles)       → expect cycleCount: 0
3. query               → e.g. "invalidate_and_reload_page watcher agent-write"
4. context             → hub symbols (LogseqGraph, StackMachineParser._refresh_node)
5. impact(upstream)    → before editing parser FSM or graph index
6. Runtime probe       → uv run python + tmp_path fixture
7. make all            → Ruff + Mypy + pytest
```

### High-risk symbols (always `impact` first)

| Symbol | Typical risk |
|--------|--------------|
| `StackMachineParser._refresh_node` | CRITICAL — parse entrypoints |
| `_expand_macros_and_embeds_impl` | HIGH — SYNAPSE RAG content |
| `LogseqGraph.load_directory` | HIGH — alias / ghost registry |
| `invalidate_and_reload_page` | MEDIUM — watcher freshness |
| `kinetic._resolve_graph_path` | MEDIUM — all CLI subcommands |

### Example MCP calls (Cursor agent)

Use your locally configured code-audit MCP server identifier — **do not commit server names to the public tree**.

```json
{ "server": "<local-code-audit-mcp>", "toolName": "check", "arguments": { "cycles": true, "repo": "logseq-matryca-parser" } }
```

```json
{
  "server": "<local-code-audit-mcp>",
  "toolName": "query",
  "arguments": {
    "search_query": "agent-read xray markdown export",
    "task_context": "Clean Architecture audit kinetic agent_press",
    "repo": "logseq-matryca-parser",
    "limit": 5
  }
}
```

```json
{
  "server": "<local-code-audit-mcp>",
  "toolName": "impact",
  "arguments": {
    "target": "StackMachineParser._refresh_node",
    "direction": "upstream",
    "repo": "logseq-matryca-parser"
  }
}
```

### Cross-repo study (Matryca Plumber)

When verifying adapter contracts, index both repos and pass `repo: "matryca-plumber"` or compare layer boundaries documented in Plumber's [`CLEAN_CODE_ARCHITECTURE.md`](https://github.com/MarcoPorcellato/matryca-plumber/blob/main/docs/CLEAN_CODE_ARCHITECTURE.md).

Parser public APIs consumed by Plumber: `LogseqGraph`, `append_child_to_node`, `StackMachineParser`, `SynapseAdapter`.

---

## Other local tools (optional)

| Tool class | Role | Public mention |
|------------|------|----------------|
| Corpus packers | One-shot export for external review | Forbidden in public PR text |
| Cursor rules | Agent discipline (`.cursor/rules/`) | OK — no vendor names in committed rules |
| CodeQL | CI security (GitHub default) | OK — documented in [`CODEQL.md`](../CODEQL.md) |

---

## Writing audit artifacts

| Document | Vendor names |
|----------|--------------|
| `docs/BUG_HUNT_REPORT.md` | Use "analisi statica locale" / "local code study" |
| `docs/quality/CLEAN_ARCH_BACKLOG.md` | Generic only |
| GitHub issues | Generic only; link BUG_HUNT ID |
| `docs/internal/*` | Generic code-audit terminology only |

---

## Local exclude (Ghost Tooling)

Add indexer cache directories to **`.git/info/exclude`** (never commit `.gitignore` entries that reveal tool names). See [`STATIC_ANALYSIS_POLICY.md`](STATIC_ANALYSIS_POLICY.md) §3.A.
