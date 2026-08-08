# AI agent orientation

## Product in one paragraph

Logseq Matryca Parser turns a directory of sovereign Logseq Markdown files into
a deterministic typed AST and an in-memory graph. It preserves outline
hierarchy, block UUIDs, page aliases, backlinks, properties, tasks, timestamps,
and assets so humans and AI systems can retrieve, inspect, export, visualize,
and safely extend a vault without flattening its structure.

Markdown files are the source of truth. The in-memory graph, registries,
backlinks, exports, visualizations, and AI chunks are derived views.

## Capability map

| Layer | Use it for | Primary entry point |
|---|---|---|
| **LOGOS** | Parse Logseq Markdown into a deterministic AST | `LogosParser`, `StackMachineParser` |
| **Graph** | Load a vault, resolve pages and aliases, query nodes, inspect backlinks | `LogseqGraph` |
| **SYNAPSE** | Export lineage-aware LangChain documents, LlamaIndex nodes, and enriched chunks | `SynapseAdapter` |
| **FORGE** | Serialize JSON, clean Markdown, Logseq pages, and Obsidian-compatible output | `ForgeExporter`, `serialize_logseq_page` |
| **KINETIC** | Run CLI parse, export, scan, visualize, agent-read, and agent-write workflows | `matryca-parse` |
| **LENS** | Build an interactive graph visualization | `GraphVisualizer` |
| **Agent access** | Read a token-efficient X-Ray outline or perform bounded writes | `agent-read`, `agent-write`, `logseq_agent_write` |

## Start here

- For installation and a first run, use [`README.md`](README.md).
- For integration recipes, use [`docs/COOKBOOK.md`](docs/COOKBOOK.md).
- For stable imports and compatibility guarantees, use
  [`docs/reference/API_STABILITY.md`](docs/reference/API_STABILITY.md).
- For architecture and ownership boundaries, use
  [`docs/CLEAN_CODE_ARCHITECTURE.md`](docs/CLEAN_CODE_ARCHITECTURE.md).
- For the maintained machine-readable knowledge map, use
  [`docs/index.md`](docs/index.md).
- For historical release capabilities, use
  [`RELEASE_HIGHLIGHTS.md`](RELEASE_HIGHLIGHTS.md).

Prefer imports from the package root when they are part of the documented
stable API. Before editing, identify whether the task affects parsing, graph
identity, serialization, filesystem writes, optional adapters, or CLI-only
presentation. Do not infer runtime contracts from release history.

## Repository working contract

```bash
uv sync --all-extras
make all
make vendor-name-check
```

- Keep all user-facing documentation and operator messages in English.
- Preserve deterministic UUIDs, tree order, parent and left pointers, source
  line ranges, and parse/serialize round trips.
- Treat paths, symlinks, `file://` assets, atomic replacement, and vault
  containment as security boundaries.
- Keep optional integrations lazy; the base parser must remain lightweight.
- Add focused regression tests for behavioral changes and do not lower the
  coverage floor.
- Do not commit local caches, generated audit data, vault contents, credentials,
  or `.matryca_xray_state.json`.

## Audit code — maintainer intelligence

Maintainers may use **audit code** (local graph-based static analysis) to understand call chains, blast radius, and import cycles before structural work. **Do not** name specific third-party indexer products anywhere in this repository (issues, PRs, CHANGELOG, public docs, or agent config).

### Always do

- Run **impact analysis** before editing hub symbols (`StackMachineParser._refresh_node`, `_expand_macros_and_embeds_impl`, `LogseqGraph.load_directory`, `invalidate_and_reload_page`).
- Use **query** / **context** for cross-module flows instead of guessing from grep alone.
- Run `check(cycles)` — expect **0** import cycles in `src/`.
- Run `make all` (and `make vendor-name-check`) after behavior or documentation changes.

### Never do

- NEVER add vendor AST indexers to CI, Dockerfiles, or `pyproject.toml`.
- NEVER ignore **HIGH** or **CRITICAL** impact warnings on parser/graph hubs without explicit user approval.
- NEVER commit tool-specific cache directories — use `.git/info/exclude` locally (Ghost Tooling policy).

### SSOT

| Document | Purpose |
|----------|---------|
| [`docs/CLEAN_CODE_ARCHITECTURE.md`](docs/CLEAN_CODE_ARCHITECTURE.md) | Uncle Bob rings, SOLID, public graph APIs |
| [`docs/internal/LOCAL_CODE_STUDY.md`](docs/internal/LOCAL_CODE_STUDY.md) | Maintainer audit-code runbook (generic MCP surface) |
| [`docs/internal/STATIC_ANALYSIS_POLICY.md`](docs/internal/STATIC_ANALYSIS_POLICY.md) | Ghost Tooling policy |

When the maintainer instructs you to use audit code tooling, follow their workflow — do not document product names in artifacts.
