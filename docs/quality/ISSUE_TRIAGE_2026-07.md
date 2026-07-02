# Issue triage — July 2026

**Date:** 2026-07-02  
**Scope:** logseq-matryca-parser open backlog vs Clean Architecture v1.6 milestone  
**Roadmap:** [`GITHUB_CLEAN_ARCH_ROADMAP.md`](GITHUB_CLEAN_ARCH_ROADMAP.md)

---

## Summary

| Action | Count |
|--------|-------|
| Close (shipped locally) | #67, #68, optionally #73 |
| Assign milestone v1.6 | #70, #71, #61, new phase issues |
| Wave 9–10 bugs (linked, no milestone yet) | #59, #62, #63, #66, #69 |
| Product backlog (no v1.6) | GUI/MCP epics, FORGE RFC, GFI docs |

---

## A. Close — already shipped or verified

| Issue | Reason | Action |
|-------|--------|--------|
| **#67** | `_parse_graph` removed from `kinetic.py` | Close with Phase 0 PR — `Fixes #67`, `state_reason: completed` |
| **#68** | `is_tracked_markdown_path()` public on `LogseqGraph` | Close with Phase 0 PR — `Fixes #68` |
| **#60** | X-Ray corrupt JSON | Already closed — in CHANGELOG v1.4.2 |
| **#65** | Cyclic embed guard | Already closed |
| **#72** | Append newline | Already closed |
| **#73** | `append_child` newline regression test | Close if `tests/test_agent_writer.py` covers case; else leave open |

---

## B. Milestone `v1.6 — Clean Architecture & Code Quality`

| Issue | Phase | Note |
|-------|-------|------|
| Epic + PHASE0–4 (bootstrap script) | — | Parent + new children |
| **#70** | 2 | SYNAPSE embed OCP — add `architecture`, `clean-code` |
| **#71** | 2 | GFI tests — link to #70 |
| **#61** | 3/4 | Production assert in `agent_write` |

**Wave 9–10 (optional milestone):**

| Issue | Type | Recommendation |
|-------|------|----------------|
| **#59** | bug (LENS ghost wikilinks) | Link on project board; fix independent of v1.6 |
| **#62** | test (LENS regression) | GFI — no v1.6 milestone |
| **#63** | test (agent_press JSON) | GFI — no v1.6 milestone |
| **#66** | enhancement (embed semantics) | Related to #70 — consider same PR |
| **#69** | chore (Italian ImportError strings) | DX — backlog, not v1.6 |

---

## C. Outside v1.6 (product / GFI)

| Issue | Reason |
|-------|--------|
| #3, #6, #7, #8 | GUI / feature epics |
| #4, #5 | MCP server features |
| #33, #34 | FORGE CSV / Ollama RFC |
| #19, #25, #26, #28 | Good-first docs/tests |
| #64 | Strict indentation mode — parser epic, not v1.6 |

---

## D. Milestone hygiene

| Milestone | Action |
|-----------|--------|
| `v1.0 - The GUI Update` (stale, #3 open) | Rename to `Backlog — GUI & MCP` or close milestone and move #3 to a GUI epic |
| No milestone on #59–#73 | Assign v1.6 only to architecture-track issues |

---

## E. Documentation updates (this triage)

- [`GOOD_FIRST_ISSUES.md`](../GOOD_FIRST_ISSUES.md) — link epic + milestone
- [`CLEAN_ARCH_BACKLOG.md`](CLEAN_ARCH_BACKLOG.md) — GitHub issue column
- [`README.md`](README.md) — link roadmap

---

## F. Execution checklist

- [x] `gh label sync` / `clean-code` label created
- [x] `bash .github/scripts/create_clean_arch_issues.sh`
- [x] GitHub Project board created
- [x] `gh issue edit 70 71 61 67 68 --milestone "v1.6 — Clean Architecture & Code Quality"`
- [ ] Phase 0 PR merges → close #67, #68
- [ ] Update epic checkboxes per phase

---

*Refresh after each phase PR merges.*
