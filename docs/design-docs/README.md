---
type: Document
---
> ⚠️ **Notice:** For the active documentation index, please refer to the main [README.md](../../README.md).

# Historical design documents

For contributors: These files are Document-Driven Development blueprints from the initial Logos Protocol scaffolding. They explain design intent and mldoc parity research — they are not the live implementation contract.

For current architecture and APIs, use:

* [ARCHITECTURE.md](../ARCHITECTURE.md) — active system design
* [logseq_ast_primer.md](../logseq_ast_primer.md) — Logseq Spatial Markdown domain rules
* [README.md](../../README.md) — documentation index

Each file in this folder includes a historical banner. When implementing parser
behavior, start with the [current compatibility evidence](../quality/OFFICIAL_LOGSEQ_MARKDOWN_COMPATIBILITY_2026-10-10.md)
and [parser tests](../../tests/test_logos_parser.py), then confirm against the
current implementation. [OFFICIAL_MLDOC_SPECS.md](OFFICIAL_MLDOC_SPECS.md)
remains historical mldoc research, not a current official-conformance contract.
