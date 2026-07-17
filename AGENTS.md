# Audit code — maintainer intelligence

Maintainers may use **audit code** (local graph-based static analysis) to understand call chains, blast radius, and import cycles before structural work. **Do not** name specific third-party indexer products anywhere in this repository (issues, PRs, CHANGELOG, public docs, or agent config).

## Always do

- Run **impact analysis** before editing hub symbols (`StackMachineParser._refresh_node`, `_expand_macros_and_embeds_impl`, `LogseqGraph.load_directory`, `invalidate_and_reload_page`).
- Use **query** / **context** for cross-module flows instead of guessing from grep alone.
- Run `check(cycles)` — expect **0** import cycles in `src/`.
- Run `make all` (and `make vendor-name-check`) after behavior or documentation changes.

## Never do

- NEVER add vendor AST indexers to CI, Dockerfiles, or `pyproject.toml`.
- NEVER ignore **HIGH** or **CRITICAL** impact warnings on parser/graph hubs without explicit user approval.
- NEVER commit tool-specific cache directories — use `.git/info/exclude` locally (Ghost Tooling policy).

## SSOT

| Document | Purpose |
|----------|---------|
| [`docs/CLEAN_CODE_ARCHITECTURE.md`](docs/CLEAN_CODE_ARCHITECTURE.md) | Uncle Bob rings, SOLID, public graph APIs |
| [`docs/internal/LOCAL_CODE_STUDY.md`](docs/internal/LOCAL_CODE_STUDY.md) | Maintainer audit-code runbook (generic MCP surface) |
| [`docs/internal/STATIC_ANALYSIS_POLICY.md`](docs/internal/STATIC_ANALYSIS_POLICY.md) | Ghost Tooling policy |

When the maintainer instructs you to use audit code tooling, follow their workflow — do not document product names in artifacts.
