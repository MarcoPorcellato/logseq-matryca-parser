---
type: SecurityPolicy
title: Dependency advisory exceptions
description: Active and resolved historical dependency advisory exceptions, with fail-closed controls and scope.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-09-27
verified: 2026-09-27
stale_after: 2027-03-26
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Dependency advisory exceptions

This register implements the exception requirements in the
[dependency policy](../reference/DEPENDENCY_LICENSE_POLICY.md). Active
exceptions must be exact, reviewable, temporary, and enforced by repository
tests. Resolved entries remain as historical evidence and do not authorize a
current audit waiver. There are no active Parser dependency exceptions as of
2026-09-27.

## Resolved historical exception: NLTK path traversal (Parser scope)

| Field | Decision |
|---|---|
| Status | Resolved for the Parser on 2026-09-27 |
| Advisory | `PYSEC-2026-3740` / `GHSA-8mgp-746c-j5xp` |
| Package | `nltk 3.10.3` |
| Historical scope | Transitive runtime dependency of the Parser's optional AI extra through `llama-index-core`; absent from the base installation |
| Owner | `@MarcoPorcellato` |
| Review date | 2026-09-05 |
| Resolution date | 2026-09-27 |
| Upstream tracking | [NLTK security advisory](https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp) |

### Historical decision and resolution evidence

The exception was introduced for the then-current optional AI dependency graph.
The Parser did not import NLTK or expose its model import/export APIs, but the
dependency remained in its resolved graph through LlamaIndex. That exception
has been retired by moving native LlamaIndex integration to a separately
maintained companion and removing both `llama-index-core` and `nltk` from the
Parser dependency graph.

The migration lock is SHA-256
`c7c79e872dd42d5007ac501968f56651b2eb809d9fd807e00289aed5a17ac343`. The
all-extras production audit was rerun without an advisory ignore and reported
`No known vulnerabilities found`. The Parser CI and release workflows retain
the all-extras dependency export and fail-closed `pip-audit` command without
`--ignore-vuln`.

This resolves the Parser's dependency exposure only. It does not declare NLTK
or its upstream advisory fixed, and it does not determine the companion's
dependency or exception policy.

Any future Parser change that reintroduces NLTK or another affected package
must be reviewed against the live advisory, locked dependency scope, and
current fail-closed audit before merge. Historical approval is not reusable.
