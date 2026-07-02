# GitHub roadmap — Clean Architecture v1.6

**Status:** 2026-07-02  
**SSOT (code):** [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md)  
**Backlog:** [`CLEAN_ARCH_BACKLOG.md`](CLEAN_ARCH_BACKLOG.md)  
**Triage:** [`ISSUE_TRIAGE_2026-07.md`](ISSUE_TRIAGE_2026-07.md)

---

## Milestone

| Field | Value |
|-------|-------|
| **Title** | `v1.6 — Clean Architecture & Code Quality` |
| **Target release** | **v1.6.0** (minor — docs + internal refactors, no public API break) |
| **Close when** | Epic complete + tag `v1.6.0` published |

Bootstrap: `bash .github/scripts/create_clean_arch_issues.sh`

---

## GitHub Project

**Name:** `Logseq Parser — Clean Architecture v1.6`

| Column | Meaning |
|--------|---------|
| Backlog | Open, unassigned |
| Ready | Full body + acceptance criteria |
| In progress | Linked open PR |
| Review | PR open, CI green |
| Done | Merged + issue closed |

**Suggested filter:** `label:architecture` OR `label:clean-code` OR milestone:`v1.6 — Clean Architecture & Code Quality`

---

## Epic and phases

Update issue numbers after running the bootstrap script (see `.github/clean_arch_issue_numbers.txt`).

| Phase | Issue | Title | PR branch |
|-------|-------|-------|-----------|
| — | [#78](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/78) | Epic: Clean Architecture v1.6 | — |
| 0 | [#79](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/79) | docs SSOT + layer CI + runbook | `docs/clean-architecture-ssot` |
| 0 | [#67](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/67) | remove `_parse_graph` | same as Phase 0 |
| 0 | [#68](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/68) | `is_tracked_markdown_path()` public | same as Phase 0 |
| 1 | [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80) | `kinetic_export.py` (DEBT-005) | `refactor/kinetic-export` |
| 2 | [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) | SYNAPSE embed OCP (DEBT-006) | `refactor/synapse-embed-ocp` |
| 2 | [#71](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/71) | table-driven embed tests | same or follow-up |
| 3 | [#81](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/81) | `iter_attached_nodes()` public | `refactor/kinetic-commands-isp` |
| 3 | [#82](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/82) | `kinetic_commands.py` | same PR |
| 3/4 | [#61](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/61) | agent_write assert guard | Phase 3 or 4 |
| 4 | [#83](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/83) | hardening + doc links | `chore/clean-arch-v1-hardening` |

---

## Labels

| Label | Use |
|-------|-----|
| `architecture` | Layer boundaries, dependency rule |
| `clean-code` | Uncle Bob / SOLID slice |
| `enhancement` | Structural refactor (non-bug) |

Sync: `gh label sync -f .github/labels.yml`

---

## Issue template

Use **Clean Architecture slice** when filing new structural work:  
`.github/ISSUE_TEMPLATE/clean_architecture.yml`

---

## Out of scope (v2)

| Item | Tracking |
|------|----------|
| Split `logos_parser.py` | Future epic after v1.6 |
| `domain/ports.py` hexagonal | Rejected in backlog |
| Vendor indexer in CI | Ghost Tooling policy |

---

*Update epic checkboxes and this table when phase PRs merge.*
