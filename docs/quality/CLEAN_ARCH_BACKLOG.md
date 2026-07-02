# Clean Architecture — Residual Backlog

**Status:** 2026-07-02 · post **v1.5.0**  
**SSOT:** [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md)  
**Evidence:** [`../BUG_HUNT_REPORT.md`](../BUG_HUNT_REPORT.md) §6

---

## Executive scorecard

| Verdict | Items |
|---------|-------|
| **Shipped (DEBT-001)** | `iter_canonical_pages()`, `page_for_node()` — v1.4.0+ |
| **Shipped (bugs)** | BUG-001…031 addressed in v1.4.0–v1.5.0 (see CHANGELOG) |
| **Open — structural** | DEBT-005, DEBT-006, DEBT-007 |
| **By design** | Flat module layout; lazy optional imports in adapters |

---

## SOLID residual debt

| ID | Principle | Observation | Module | Action | Priority |
|----|-----------|-------------|--------|--------|----------|
| DEBT-005 | **SRP** | `kinetic.py` ~710 lines; dead `_parse_graph` removed in v1.5.1 slice | `kinetic.py` | Extract `_export_*` to `kinetic_export.py` or registry | P2 |
| DEBT-006 | **OCP** | Monolithic embed expansion loop | `synapse.py` | Strategy per embed type — [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) | P2 |
| DEBT-007 | **DIP** | Watcher used `_resolved_path_is_tracked_markdown` (private) | `graph.py` | Public `is_tracked_markdown_path()` — **shipped** v1.5.1 | ~~P3~~ |
| — | **LSP** | `LogosNode` legacy vs frozen `LogseqNode` | `logos_core.py` | No new `LogosNode` consumers | P4 |
| — | **DIP** | Lazy `logseq_paths` in `resolve_asset_path` | `logos_core.py` | Acceptable cycle avoidance | by design |

---

## Enforcement shipped

| Mechanism | File |
|-----------|------|
| Layer import boundaries | `tests/test_layer_boundary.py` |
| Import cycles | `0` — verify via local code audit `check(cycles)` ([`internal/LOCAL_CODE_STUDY.md`](../internal/LOCAL_CODE_STUDY.md)) |

---

## Recommended remediation order

| Step | Action | Est. |
|------|--------|------|
| 1 | ~~`is_tracked_markdown_path()` public API~~ | done |
| 2 | ~~Remove dead `_parse_graph` in kinetic~~ | done |
| 3 | GFI-36: extend boundary tests if new modules added | 1 h |
| 4 | DEBT-005: kinetic export extraction (maintainer) | 3–4 h |
| 5 | DEBT-006: SYNAPSE embed strategy slice ([#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70)) | 4–6 h |

---

## Rejected / by design (do not re-file)

| Claim | Why |
|-------|-----|
| Immediate `domain/ports.py` hexagonal split | Library scope; use incremental module extraction |
| Merge `graph.py` into `logos_parser.py` | Different reasons to change (parse vs index) |
| Add vendor AST indexer to CI | Ghost Tooling policy — local maintainer only |

---

*Update this file when closing a DEBT-* item or opening a new architecture issue.*
