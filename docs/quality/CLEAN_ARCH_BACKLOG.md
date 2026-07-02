# Clean Architecture — Residual Backlog

**Status:** 2026-07-02 · post **v1.6.0** (structural v1 **complete**)  
**SSOT:** [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md)  
**Roadmap:** [`GITHUB_CLEAN_ARCH_ROADMAP.md`](GITHUB_CLEAN_ARCH_ROADMAP.md)  
**Evidence:** [`../BUG_HUNT_REPORT.md`](../BUG_HUNT_REPORT.md) §6

---

## Executive scorecard

| Verdict | Items |
|---------|-------|
| **Shipped (DEBT-001)** | `iter_canonical_pages()`, `page_for_node()` — v1.4.0+ |
| **Shipped (DEBT-005)** | `kinetic_export.py` — [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80) |
| **Shipped (DEBT-006)** | `synapse_embed.py` OCP — [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) |
| **Shipped (DEBT-007)** | `is_tracked_markdown_path()` — v1.5.1 / [#68](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/68) |
| **Shipped (ISP)** | `iter_attached_nodes()` public — [#81](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/81) |
| **Shipped (KINETIC SRP)** | `kinetic_commands.py` — [#82](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/82) |
| **Open — v2** | `logos_parser.py` split (CRITICAL hub — epic after v1.6) |
| **By design** | Flat module layout; lazy optional imports in adapters |

---

## SOLID residual debt

| ID | Principle | Observation | Module | Action | GitHub | Priority |
|----|-----------|-------------|--------|--------|--------|----------|
| DEBT-005 | **SRP** | ~~`kinetic.py` export handlers~~ | `kinetic_export.py` | **Shipped** v1.6 | [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80) | ~~P2~~ |
| DEBT-006 | **OCP** | ~~Monolithic embed expansion loop~~ | `synapse_embed.py` | **Shipped** v1.6 | [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) | ~~P2~~ |
| DEBT-007 | **DIP** | ~~Watcher private path check~~ | `graph.py` | **Shipped** v1.5.1 | [#68](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/68) | ~~P3~~ |
| — | **ISP** | ~~Private `_iter_attached_nodes`~~ | `graph.py` | **Shipped** v1.6 | [#81](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/81) | ~~P3~~ |
| — | **LSP** | `LogosNode` legacy vs frozen `LogseqNode` | `logos_core.py` | No new `LogosNode` consumers | — | P4 |
| — | **DIP** | Lazy `logseq_paths` in `resolve_asset_path` | `logos_core.py` | Acceptable cycle avoidance | — | by design |

---

## Enforcement shipped

| Mechanism | File |
|-----------|------|
| Layer import boundaries | `tests/test_layer_boundary.py` |
| Import cycles | `0` — verify via local code audit `check(cycles)` ([`internal/LOCAL_CODE_STUDY.md`](../internal/LOCAL_CODE_STUDY.md)) |
| Vendor-free public docs | `scripts/check_vendor_free_docs.sh` |

---

## v2 epic (not in v1.6 scope)

| Action | Est. |
|--------|------|
| Split `logos_parser.py` stack machine (requires `impact(_refresh_node)` gate) | epic |
| GFI-37: extend boundary tests when adding new driver satellites | 1 h |

---

## Rejected / by design (do not re-file)

| Claim | Why |
|-------|-----|
| Immediate `domain/ports.py` hexagonal split | Library scope; use incremental module extraction |
| Merge `graph.py` into `logos_parser.py` | Different reasons to change (parse vs index) |
| Add vendor AST indexer to CI | Ghost Tooling policy — local maintainer only |

---

*v1 structural backlog complete. Update when opening v2 epic or new architecture issue.*
