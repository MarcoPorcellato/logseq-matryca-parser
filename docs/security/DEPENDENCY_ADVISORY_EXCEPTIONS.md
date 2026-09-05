---
type: SecurityPolicy
title: Dependency advisory exceptions
description: Time-bounded, fail-closed exceptions for known dependency advisories without an available patched release.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-09-05
verified: 2026-09-05
stale_after: 2026-10-05
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Dependency advisory exceptions

This register implements the exception requirements in the
[dependency policy](../reference/DEPENDENCY_LICENSE_POLICY.md). Each exception
is exact, reviewable, temporary, and enforced by repository tests. A package
with a patched release must be upgraded; it must not be added here merely to
make an audit pass.

## Active exception: NLTK path traversal

| Field | Decision |
|---|---|
| Advisory | `PYSEC-2026-3740` / `GHSA-8mgp-746c-j5xp` |
| Package | `nltk 3.10.3` |
| Scope | Transitive runtime dependency of the optional AI extra through `llama-index-core`; absent from the base parser installation |
| Owner | `@MarcoPorcellato` |
| Review date | 2026-09-05 |
| Expiry date | 2026-10-05 |
| Upstream tracking | [NLTK security advisory](https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp) |

### Exploitability analysis

The advisory affects path handling in model import and export operations. The
Parser does not import NLTK and does not call `TransitionParser`,
`AveragedPerceptron`, `PerceptronTagger`, or `save_maxent_params`. Its optional
AI adapter imports only schema types from `llama_index.core.schema`; it does
not accept an NLTK model path or expose an NLTK training, loading, or saving
operation. The vulnerable operations are therefore not reachable through the
Parser's public API or CLI at this revision.

This conclusion is limited to this repository. It does not declare NLTK safe
for direct use by another application sharing the environment.

### Compensating controls

- A deterministic test rejects direct NLTK imports or references to the named
  vulnerable APIs anywhere under `src/`.
- CI and release audits ignore only `PYSEC-2026-3740`; every other advisory
  remains fail-closed.
- The base installation does not include the optional AI dependency graph.
- Any proposal to expose NLTK model import, export, training, loading, or
  saving must first remove this exception or complete a new security review.

### Removal criteria

Remove both workflow flags and this active entry as soon as the first of these
conditions occurs:

1. a patched NLTK registry release is available and qualified in the locked
   optional AI dependency graph;
2. the optional dependency chain no longer resolves to an affected NLTK
   version;
3. repository code reaches an affected API; or
4. 2026-10-05 is reached without a fresh reviewed decision.

Expiry is fail-closed: an expired entry is not permission to keep ignoring the
advisory.
