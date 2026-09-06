---
type: PublicAPIContract
title: Python API stability and typing contract
description: Canonical compatibility policy for package-root exports, versions, typing metadata, and internal modules.
status: stable
classification: canonical
audience: contributors
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-09-05
verified: 2026-09-05
stale_after: 2027-02-03
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Python API stability and typing contract

This document defines which Python interfaces downstream consumers may rely on.
Logseq semantic compatibility and the `matryca-parse` CLI are related but
separate contracts.

## Stability levels

| Level | Compatibility promise | Change policy |
|---|---|---|
| Stable | Supported package-root interface | Breaking changes require a major version, migration guidance, and a changelog entry |
| Experimental | Publicly importable, but still evolving | May change in a minor version after explicit release notes and reasonable migration guidance |
| Internal | Implementation detail outside the package root | No compatibility guarantee; consumers should not import it directly |

Deprecations of stable interfaces should remain available for at least one
minor release unless a security issue makes that unsafe.

## Stable package-root surface

| Area | Stable exports |
|---|---|
| Version | `__version__` |
| Parser | `StackMachineParser`, `LogosParser`, `LogseqPage`, `LogseqNode`, `LogosNode`, `ASTVisitor` |
| Graph | `LogseqGraph`, `SnapshotPage` |
| Diagnostics | `Diagnostic`, `DiagnosticCode`, `DiagnosticSeverity`, `collect_graph_diagnostics` |
| Errors | `LogseqParserError`, `LogseqIndentationError`, `BlockReferenceError`, `PageTitleCollisionError`, `VaultWriteError` |
| Writer preview | `WriteProposal` |
| Markdown | `serialize_logseq_page`, `write_logseq_page`, `format_logseq_page_properties`, `format_logseq_block_property_lines` |
| Paths | `discover_graph_files`, `derive_page_title_from_source_path`, `page_title_to_filename`, `filename_to_page_title`, `page_title_to_relative_path`, `encode_page_title_segment`, `decode_page_title_segment`, `is_excluded_graph_path` |

The exact package-root export manifest and the signatures of the parser and
graph entry points are regression-tested. Adding a new stable symbol requires
updating this table and those tests in the same PR.

`LogseqGraph.load_directory` accepts keyword-only `strict_refs=False` and
`strict_title_collisions=False`. It also accepts `graph_path` as `Path` or `str`;
the loader normalizes a textual path with `Path(graph_path).expanduser().resolve()`.
Both strict modes are opt-in, preserving the
permissive default.

`SnapshotPage(logical_path, text)` and
`LogseqGraph.from_snapshot_pages(graph_path, snapshot_pages, *, strict_refs=False,
strict_title_collisions=False)` are stable additive graph APIs. The factory accepts
either a mapping of graph-relative POSIX Markdown paths to already-captured text or
a sequence of `SnapshotPage` values. It normalizes and orders unique `pages/` and
`journals/` paths deterministically, accepts at most 1,024 pages and 16 MiB of UTF-8
text, parses with the existing in-memory parser, and reuses the ordinary graph index
builders and strict modes. It never discovers or reopens logical source paths.
Synthetic source paths on the resulting models are metadata for graph behavior, not
filesystem-read authority; capture, source selection, hashing, and revisions remain
the caller's responsibility. Its graph-root label is normalized lexically without
expanding, resolving, or inspecting the caller path.

Diagnostic code compatibility, serialization, and path-safety rules are defined
in the [structured diagnostics contract](DIAGNOSTICS.md).
Vault-bound writer and asset-read guarantees are defined in the
[filesystem safety contract](FILESYSTEM_SAFETY.md).

## Experimental package-root surface

The following integrations remain public but experimental:

- agent helpers: `SessionAliasRegistry`, `LogseqConfigReader`,
  `logseq_agent_write`, `ensure_aot_compatibility`;
- exporters: `ForgeExporter`, `FlatListForgeVisitor`, `JSONForgeVisitor`,
  `MarkdownForgeVisitor`, `ObsidianForgeVisitor`;
- optional adapters: `SynapseAdapter`, `GraphVisualizer`;
- lower-level parser and identity helpers: `PageRegistry`, `LOGSEQ_PATTERNS`,
  `clean_node_content`, `is_system_block`, `page_source_node_id`,
  `SovereignNotePackage`.

Everything not exported from `logseq_matryca_parser.__all__` is internal unless
another maintained contract explicitly promotes it.

`GraphVisualizer` remains experimental, compatible, transitional, and
feature-frozen in this release line. Stage 0 changes no API and emits no
deprecation warning. Future user-facing graph intelligence belongs in Matryca
Trama; a compatible deprecation may begin only through a separately reviewed
decision, release notes, and migration guidance.

## Version source

`src/logseq_matryca_parser/_version.py` is the single authoritative version
source. Hatchling derives wheel and source-distribution metadata from that file;
the package root re-exports the same value. Release preparation changes that
one assignment only. Tests compare runtime and installed distribution metadata.

## PEP 561 and wheel qualification

The wheel contains `logseq_matryca_parser/py.typed` and records it in `RECORD`.
CI builds the wheel, checks its metadata and marker, installs it into a clean
environment, and runs a strict downstream Mypy sample without relying on the
source checkout.

## Incremental typing plan

1. Keep entities, parser, graph, paths, and Markdown serialization fully checked.
2. Tighten stable package-root signatures before experimental adapters.
3. Type optional integrations only within their declared extras; do not force
   visualization, watcher, or AI dependencies on core consumers.
4. Promote an experimental interface to stable only with downstream typing and
   semantic compatibility evidence.
