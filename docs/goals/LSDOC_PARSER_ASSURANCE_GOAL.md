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
last_verified: 2026-08-20
verified: 2026-08-20
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

M1 merged through [PR #161](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/161).
M3, M4, and M2 subsequently merged through [PR #162](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/162),
[PR #163](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/163), and
[PR #164](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/164), as
`172be70`, `5d38e01`, and `98bc5aa` on `main`. M3 remains a project-owned,
bounded adversarial laboratory; M4 remains a Python-native, test-only,
deterministic work model. Neither expands #103, #87, or #111 ownership or
constitutes a release claim.

M5 was delivered through [PR #168](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/168)
and adds an optional aggregate-only local assurance CLI with a fresh worker,
file/byte/time bounds, symlink rejection, ordinary-socket denial, safe report
validation, and a project-owned synthetic self-test. It does not emit or retain
vault-derived content, paths, titles, UUIDs, exception text, or host names.

M6 was delivered through [PR #169](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/169).
Its accepted source-location RFC retains one-based logical line fields as the
only supported coordinates; offset and source-map expansion stays behind its
admission gate.

M7 was delivered through [PR #170](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/170)
and closes child issue [#165](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/165).
The private line-classification extraction preserves parser state reduction,
node creation, identities, graph behavior, public imports, and dependencies.
The broader #108 epic remains open for later gated phase slices.

M2 is complete through the accepted negative
[ADR-001](../decisions/ADR-001-external-oracle-boundary.md): no external
`mldoc` executable may be installed, invoked, pinned, packaged, or integrated
under the current boundary. The ADR is a conservative engineering decision, not
legal advice. M3, M4, and M5 use only project-owned evidence. Any future
external-oracle, retention, upload, or richer source-derived reporting proposal
requires a superseding ADR meeting every listed reconsideration condition,
including a maintainer-approved process boundary.

The direct GPT-5.6 Sol review found and corrected unsafe runtime-string
admission, parent-side symlink-loop disclosure, dangling root-link acceptance,
and ignored global graph input in self-test mode. These corrections are now
published through PR #168; the M5 privacy and non-retention boundary remains
part of the supported contract.

The v1.8.0 release gates are complete. Release preparation merged through
[PR #171](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/171) as
`06a1d6cb3dcbb215c6aa108ce82d37da530d52a5`, and tag `v1.8.0` published through
the exact [release workflow run](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/32324328464).
The run passed both Python pre-flight jobs, package contract, SBOM and license
evidence, checksum verification, GitHub attestations, PyPI publication, and
GitHub Release creation. The public [GitHub Release](https://github.com/MarcoPorcellato/logseq-matryca-parser/releases/tag/v1.8.0)
and [PyPI package](https://pypi.org/project/logseq-matryca-parser/1.8.0/)
were checked after publication. The broader #104, #103, #87, #111, and #108
acceptance work remains open where the plan still marks it incomplete.

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
The historical post-correction handoff remains available for provenance, but
its pre-publication stop condition is superseded by the merged M1–M7 evidence
and the completed v1.8.0 release receipt above.

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
