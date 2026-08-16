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

First verify the live source revision, issue state, documentation policy, and
delivery state. Continue through the dependency-ordered milestones until every
applicable completion item has authoritative current evidence. Do not redo work
already proved in the plan.

The initial checkpoint `8806205c35b104ed65d00a273acc9eeca572ae38` is rejected
pre-correction evidence. Corrective implementation
`996c5a52b08f2670ecd80fb3f1515b65ae567465` passed local exact-head checks, but
its evidence head `6fcf4b274a3a04ef4c9783cf83149d6ef4aeeabb` was rejected by
the first frozen Sol review and is now superseded. These historical checkpoints
must not be presented or pushed independently as publication-ready evidence.
Corrective implementation `9e8708eef9cfa63fd9f392f5b5a9e7df564072e7` passed local
qualification but was superseded after frozen review head
`5007dc357e05775c6221c8aa84f9a11edc695e0d` returned `NEEDS_CORRECTION` for
unequal-backtick shielding parity. Non-amending corrective implementation
`7870b84` changed only `tests/parser_assurance/projection.py` and
`tests/test_compat_corpus.py` and passed exact-head local qualification with
584 tests and 92.16% coverage on a clean worktree.
Before any push, re-verify the live anchor, review the frozen full diff with GPT-5.6
Sol again, and follow the
[post-correction handoff](../internal/M1A_CORRECTIVE_HARDENING_RESTART_HANDOFF_2026-08-16.md).
The refreshed documentation-evidence commit containing this pointer must
receive exact-head qualification. Then freeze the raw full diff, record its
unfiltered SHA-256 and line count, rerun a final GPT-5.6 Sol review, and stop
before push.

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
