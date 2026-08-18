---
type: LocalGraphAssuranceDecision
title: Privacy-safe local graph assurance boundary
description: Defines a content-free, bounded, local-only CLI contract for project-owned Logseq graph assurance.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
decision_date: 2026-08-18
last_verified: 2026-08-18
verified: 2026-08-18
stale_after: 2027-02-18
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# ADR-002: Privacy-safe local graph assurance boundary

## Status

Accepted on 2026-08-18 for the M5 assurance tranche. The initial implementation
is the optional `matryca-parse assure` command and its project-owned synthetic
self-test.

## Context

M3 and M4 establish project-owned parser evidence, but they do not inspect a
user-owned vault. M5 needs a local path for checking reachable graph conditions
without centralizing vault content, retaining snippets, or turning a private
analysis command into a service.

The command must not weaken the M2 decision in
[ADR-001](ADR-001-external-oracle-boundary.md). It must use only this
repository's parser and invariants; no external parser, oracle, telemetry,
network service, or dependency is permitted.

## Decision

Provide a local-only `matryca-parse assure` command with these fixed boundaries:

- it runs parsing in a fresh child process and applies a parent-enforced timeout;
- it accepts only regular Markdown files beneath `pages/` and `journals/`, and
  fails closed on encountered symlinks, unreadable entries, or configured file
  and byte limits;
- it denies ordinary socket entry points while the worker evaluates the vault;
- it emits schema-versioned JSON with aggregate counts and finding codes only;
- it never emits, persists, uploads, or retains Markdown, snippets, paths,
  page titles, UUIDs, exception text, host names, or user-vault identifiers;
- it provides `--self-test`, which runs the same worker against a temporary,
  project-owned synthetic vault; and
- it returns nonzero for findings, limits, worker failures, or timeouts.

The initial checks are intentionally narrow: parser structure, duplicate source
identities, title collisions, and unresolved block references. They are not a
claim of complete incremental/cold-load equivalence (#103), pathological
latency (#87), vault-scale performance (#111), external-parser parity, or
release qualification.

## Threat model and controls

| Risk | Control | Residual boundary |
|---|---|---|
| Vault Markdown or identifiers leak through a report | Fixed aggregate-only report schema; report validation rejects additional fields | A user can still redirect the safe JSON locally; that is their own filesystem choice |
| Symlink traversal reads unrelated files | Any encountered symlink is rejected before parser input | Read-only discovery still has filesystem race limits; failures are reported without path detail |
| Oversized or numerous files exhaust resources | Explicit `--max-files`, `--max-total-bytes`, `--max-file-bytes`, and timeout limits | Limits are intake bounds, not performance claims |
| Parser or library code reaches the network | Worker replaces normal socket construction, connection, and name resolution with failure | This is a process-local guard, not an operating-system sandbox |
| A child hangs or returns unsafe data | Parent timeout, worker termination, schema validation, and fail-closed generic error codes | A terminated worker cannot provide a detailed diagnostic |

## Consequences

- The command is useful for a private local assurance pass without sending
  vault content anywhere.
- Its JSON schema is a CLI contract. The internal
  `local_graph_assurance` module is not added to package-root stable exports.
- Report persistence, minimized snippet retention, richer diagnostics, and any
  external comparison require separate decisions and tests.
- M5 does not close #103, #104, #87, #111, or #108.

## Reconsideration and rollback

Any expansion that emits source-derived fields, writes reports automatically,
adds network capability, retains snippets, or invokes an external oracle needs
a superseding ADR, privacy review, threat-model update, focused tests, and a
separate publication decision. Removing the command is safe because no report
or vault mutation is part of its contract.

## Verification evidence

- Initial implementation commit `4f0342d` adds the isolated worker, CLI entry
  point, and project-owned synthetic self-test. Follow-up commit `826aad7`
  validates every nested report field against the fixed schema, rejects unknown
  finding codes, and rechecks the total byte bound during reads. Current local
  head `41486b3` also rejects invalid direct runtime-limit values.
- Focused tests cover content-free reports, symlink rejection, file limits,
  socket denial, CLI self-test behavior, and misuse rejection.
- Full repository qualification remains a separate exact-head gate for the
  documentation-evidence commit and hosted pull request.
