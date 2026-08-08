# Logseq Matryca Parser repository instructions

Read [`../AGENTS.md`](../AGENTS.md) before planning or changing this repository.
Use [`../docs/index.md`](../docs/index.md) as the canonical maintained knowledge
map and [`../llms.txt`](../llms.txt) as the concise capability index.

- Logseq Markdown is the source of truth; graphs, registries, exports, and AI
  chunks are derived views.
- Preserve deterministic AST identity, hierarchy, order, line ranges,
  properties, references, and parse/serialize round trips.
- Prefer documented package-root imports and keep optional integrations lazy.
- Treat vault containment, symlinks, asset paths, target identity, atomic
  replacement, and bounded writes as security boundaries.
- Use impact analysis before changing parser or graph hub symbols named in
  `AGENTS.md`.
- Keep user-facing documentation, diagnostics, examples, and operator messages
  in English.
- Add focused regression tests for behavior changes.
- Run `make all`, `make vendor-name-check`, and the zero-import-cycle check
  before proposing completion.
- Never commit credentials, vault data, local tool caches, generated audit data,
  or `.matryca_xray_state.json`.
