---
type: Document
---
# Clean Architecture — Residual Backlog

**Current scope verified:** 2026-10-21 · delivered v1.6 structural slices remain historical; residual parser work is tracked by #108.

**SSOT:** [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md)  
**Current roadmap:** [`../ROADMAP_2026-2027.md`](../ROADMAP_2026-2027.md)

**Historical v1.6 roadmap:** [`GITHUB_CLEAN_ARCH_ROADMAP.md`](GITHUB_CLEAN_ARCH_ROADMAP.md)

**Evidence:** [`../BUG_HUNT_REPORT.md`](../BUG_HUNT_REPORT.md) §6

---

## Executive scorecard

| Verdict | Items |
|---------|-------|
| **Shipped (DEBT-001)** | `iter_canonical_pages()`, `page_for_node()` — v1.4.0+ |
| **Shipped (DEBT-005)** | `kinetic_export.py` — [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80) |
| **Shipped (DEBT-006)** | `synapse_embed.py` OCP — [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) |
| **Shipped (DEBT-007)** | `is_tracked_markdown_path()` — v1.6.0 / [#68](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/68) |
| **Shipped (ISP)** | `iter_attached_nodes()` public — [#81](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/81) |
| **Shipped (KINETIC SRP)** | `kinetic_commands.py` — [#82](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/82) |
| **Delivered private parser phases** | Line classification and lexical-state extraction; see [#108](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/108) |
| **Residual — #108** | Private reducer/enrichment extraction after #104 acceptance and #111 decision benchmarks; no broad package split |
| **By design** | Flat module layout; lazy optional imports in adapters |

---

## SOLID residual debt

| ID | Principle | Observation | Module | Action | GitHub | Priority |
|----|-----------|-------------|--------|--------|--------|----------|
| DEBT-005 | **SRP** | ~~`kinetic.py` export handlers~~ | `kinetic_export.py` | **Shipped** v1.6 | [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80) | ~~P2~~ |
| DEBT-006 | **OCP** | ~~Monolithic embed expansion loop~~ | `synapse_embed.py` | **Shipped** v1.6 | [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) | ~~P2~~ |
| DEBT-007 | **DIP** | ~~Watcher private path check~~ | `graph.py` | **Shipped** v1.6.0 | [#68](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/68) | ~~P3~~ |
| — | **ISP** | ~~Private `_iter_attached_nodes`~~ | `graph.py` | **Shipped** v1.6 | [#81](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/81) | ~~P3~~ |
| — | **LSP** | `LogosNode` legacy vs frozen `LogseqNode` | `logos_core.py` | No new `LogosNode` consumers | — | P4 |
| — | **DIP** | Lazy `logseq_paths` in `resolve_asset_path` | `logos_core.py` | Acceptable cycle avoidance | — | by design |

---

## Enforcement shipped

| Mechanism | File |
|-----------|------|
| Layer import boundaries | `tests/test_layer_boundary.py` |
| Import cycles | `0` is the required target, not a fresh measured result; verify via local code audit `check(cycles)` ([`internal/LOCAL_CODE_STUDY.md`](../internal/LOCAL_CODE_STUDY.md)) |
| Vendor-free public docs | `scripts/check_vendor_free_docs.sh` |

---

## Residual parser work — existing issue #108

The v1.6 structural completion did not complete all later parser decomposition.
The authoritative [#108 scope](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/108)
is incremental private extraction, not a new v2 package-reorganization epic.

| Action | Entry and exit gates |
|--------|----------------------|
| Accept the delivered semantic-assurance scope | [#104 acceptance record](PARSER_ASSURANCE_ACCEPTANCE_2026-10-18.md); no automatic new randomized tranche |
| Complete comparative performance decisions | [#111](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/111); separate cache/executor GO or NO-GO evidence, not an optimization implementation |
| Select one residual reducer or semantic-enrichment child slice | Separately reviewed #108 child scope, exact-hub impact analysis, required HIGH/CRITICAL approval, frozen corpus equivalence and regression gates |

Broader driver-cycle or sidecar-contract observations require their own bounded
designs. This documentation update neither confirms a fresh cycle count nor
authorizes any source, dependency, public API or filesystem-behavior change.

---

## Rejected / by design (do not re-file)

| Claim | Why |
|-------|-----|
| Immediate `domain/ports.py` hexagonal split | Library scope; use incremental module extraction |
| Merge `graph.py` into `logos_parser.py` | Different reasons to change (parse vs index) |
| Add vendor AST indexer to CI | Ghost Tooling policy — local maintainer only |

---

The closed v1.6 structural work remains complete within its original scope.
Use existing issue #108 and its dependencies for residual parser work; do not
reopen that historical milestone or create a competing extraction epic.
