---
type: PersistentGoal
title: lsdoc reference parser assurance goal
description: Concise execution pointer to the license-safe parser assurance plan.
status: draft
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-16
verified: 2026-08-16
stale_after: 2026-11-14
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# lsdoc reference parser assurance goal

Complete the license-safe parser assurance program defined in
[`docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`](../LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md).
This goal is an execution pointer subordinate to the repository stellar roadmap
and has no independent scope authority.

M1 was merged through [PR #161](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/161).
M3 is locally qualified at `3edbefb` but remains unpublished. The active next
step is M4 only: a Python-native, test-only deterministic parser work model on
an isolated branch based on that exact M3 commit. It must use original fixed-
seed, size-scaled inputs; count only declared Python-owned operations; reject
unexplained superlinear work; prove structural and semantic contracts; classify
parent-enforced timeouts; and emit source-free receipts with platform-labelled,
non-gating timing and memory observations.

M4 must not change parser runtime behavior, public APIs, package metadata,
dependencies, or the valid-fixture manifest. It must not claim #103
incremental/cold-load snapshot equivalence, #87 pathological-latency ownership,
#111 wall-time/p95/RSS/vault-scale ownership, an external-oracle result, or
release qualification. A new regression fixture is allowed only after a
minimized original input has been reviewed for provenance, privacy, and
licensing.

Before any push or pull request, re-verify the live base, freeze the raw full
diff, qualify its exact head, obtain an independent GPT-5.6 Sol full-patch
review, adjudicate every finding, and stop before publication unless separately
authorized.

Preserve the Apache-2.0 boundary: do not copy or adapt lsdoc code, tests,
corpora, schemas, module structure, control flow, or documentation. Keep lsdoc
out of runtime, build, package, and CI dependencies unless the plan's explicit
license and architecture gates are separately approved.

Use deterministic tools first and delegate only bounded, non-overlapping,
low-risk work to the cheapest suitable worker. Keep license, architecture,
security, oracle adjudication, API promotion, release, and merge decisions with
the primary agent.

Treat commit, push, pull request, merge, release, external deployment, and
license change as separate gates. Do not call partial, skipped, running,
mismatched, or unverified evidence a pass.
