---
type: PersistentGoal
title: Static analysis adoption goal
description: Concise execution pointer for evidence-led static analysis pilots and integration decisions.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-26
verified: 2026-08-26
stale_after: 2027-02-22
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Static analysis adoption goal

Execute only the maintainer-approved pilots from
[`docs/quality/STATIC_ANALYSIS_EVALUATION_2026-08-25.md`](../quality/STATIC_ANALYSIS_EVALUATION_2026-08-25.md).

The initial `actionlint`, offline `zizmor`, and `deptry` pilots are complete.
Their measured evidence and dispositions are in
[`docs/quality/STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md`](../quality/STATIC_ANALYSIS_PILOT_RESULTS_2026-08-26.md).
The next gate is an explicit per-tool integration decision: bounded blocking
design for `actionlint`, finding remediation and exception design for `zizmor`,
and periodic non-blocking design for `deptry`.

Start by re-verifying the exact repository state, candidate release, license,
artifact provenance, platform support, and network behavior. Run each tool in
an isolated advisory mode, classify every finding, measure cost and noise, and
stop for an explicit integration decision. Prefer expanding Ruff and Mypy or a
small project-owned deterministic check when they close the same gap with less
burden.

Do not retain or integrate a tool, modify dependencies, change pre-commit or CI,
publish a branch, open or merge a pull request, or release a package unless the
maintainer has authorized that exact gate. Preserve the Ghost Tooling boundary:
restricted or experimental graph indexers remain local-only and unnamed in
public artifacts.

Completion requires a documented disposition for every approved pilot,
reviewed configuration without broad suppressions, focused regression tests for
behavioral changes, the complete repository and package gates, and exact-head
evidence for any published integration.
