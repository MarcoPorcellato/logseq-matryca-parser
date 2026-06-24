# Documentation index

Use this page to find **active** documentation. Files under [`design-docs/`](design-docs/) are historical blueprints from the Document-Driven Development phase — see [`design-docs/README.md`](design-docs/README.md) before implementing from those specs.

## Active documentation

| Document | Audience | Purpose |
| :--- | :--- | :--- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Contributors, integrators | LOGOS, SYNAPSE, `LogseqGraph`, agents, data flow |
| [`logseq_ast_primer.md`](logseq_ast_primer.md) | Parser contributors | Logseq Spatial Markdown domain rules |
| [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) | New contributors | Curated starter tasks ([#19](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/19)–[#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52); wave 1 landed in **v1.4.1**) |
| [`COOKBOOK.md`](COOKBOOK.md) | Integrators | Copy-paste recipes (Synapse, graph query, watcher, agents, contributor test patterns) |
| [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md) | Maintainers | Semver, tag, and PyPI publish checklist |
| [`CODEQL.md`](CODEQL.md) | Maintainers | CodeQL default setup notes |
| [`BUG_HUNT_REPORT.md`](BUG_HUNT_REPORT.md) | Maintainers, contributors | Local static analysis bug audit (Clean Architecture lens, runtime evidence) |
| [`rfc/OLLAMA_RAG.md`](rfc/OLLAMA_RAG.md) | Integrators | Draft RFC for local Ollama RAG (issue [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34)) |
| [`roadmaps/`](roadmaps/) | Historians | Executed architectural contracts (Waves 2–12) |

## Historical / reference only

| Path | Note |
| :--- | :--- |
| [`design-docs/`](design-docs/) | Original DDD scaffolds and mldoc parity research |
| [`error_log.md`](error_log.md) | Informal internal fix log |

## Root-level docs

- [`../README.md`](../README.md) — project overview and quickstart
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — setup, `make all`, PR workflow, **Your first PR**
- [`../CHANGELOG.md`](../CHANGELOG.md) — shipped releases and Unreleased changes
- [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) — community standards
- [`../SECURITY.md`](../SECURITY.md) — private vulnerability reporting

## Examples

- [`../examples/run_demo.py`](../examples/run_demo.py) — parse journal fixture, print FORGE output
- [`../examples/demo_logseq_journal.md`](../examples/demo_logseq_journal.md) — sample Spatial Markdown input
