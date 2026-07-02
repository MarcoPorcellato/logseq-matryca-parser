# Quality & architecture audits

Maintainer-facing triage and backlog for Clean Architecture / Clean Code work.

| Document | Purpose |
|----------|---------|
| [`GITHUB_CLEAN_ARCH_ROADMAP.md`](GITHUB_CLEAN_ARCH_ROADMAP.md) | Milestone, project board, epic + phase issues (v1.6) |
| [`ISSUE_TRIAGE_2026-07.md`](ISSUE_TRIAGE_2026-07.md) | July 2026 backlog triage vs v1.6 track |
| [`CLEAN_ARCH_BACKLOG.md`](CLEAN_ARCH_BACKLOG.md) | Residual SOLID debt after v1.5.0 — prioritized slices |
| [`../BUG_HUNT_REPORT.md`](../BUG_HUNT_REPORT.md) | Full bug-hunt report (2026-06) with runtime evidence |
| [`../CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md) | **SSOT** — rings, module maps, contributor checklist |
| [`../internal/LOCAL_CODE_STUDY.md`](../internal/LOCAL_CODE_STUDY.md) | Maintainer local code audit runbook |

## Triage verdicts (summary)

| Verdict | Meaning |
|---------|---------|
| **Shipped** | Fixed in v1.4.x–v1.5.0 (see CHANGELOG) |
| **Tracked** | Open GitHub issue or GFI entry |
| **By design** | Documented v1 trade-off — do not "fix" without epic |
| **Rejected** | Audit claim obsolete vs current `src/` |

## Filing new findings

Use the six-section template in [`CLEAN_CODE_ARCHITECTURE.md`](../CLEAN_CODE_ARCHITECTURE.md#filing-github-issues-audit-template). Public issues must **not** name vendor AST tools — cite "local code study wave N" instead.
