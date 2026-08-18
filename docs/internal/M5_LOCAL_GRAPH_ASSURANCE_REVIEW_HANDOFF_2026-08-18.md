# M5 local graph assurance pre-publication handoff — 2026-08-18

## Safe resume point

- Repository: `MarcoPorcellato/logseq-matryca-parser`
- Isolated worktree: `/private/tmp/logseq-parser-assurance-m5-20260818`
- Branch: `agent/parser-privacy-assurance-m5`
- Base: `origin/main` at `27d006153e45f2c4ae37ca03136114fb8246ac88`
- Local implementation/evidence commits, oldest first:
  `4f0342d`, `826aad7`, `9202967`, `41486b3`, and `eecea20`.
- Remote branch: none. Pull request: none. Hosted checks: none.
- Persistent goal: active. The remaining M5 pre-publication gates are the
  independent full-patch review, live-base refresh, explicit publication
  authorization, and terminal hosted checks.

The original checkout remains intentionally dirty and divergent. Do not use it
for M5 edits, commits, qualification, or publication.

## Delivered local scope

`matryca-parse assure` is an optional local CLI command. It starts a fresh
worker, scans only regular Markdown beneath `pages/` and `journals/`, rejects
encountered symlinks, bounds files/bytes/time, denies ordinary socket entry
points in the worker, and prints a fixed aggregate-only JSON report.

The checks are deliberately limited to project-owned parser structure,
duplicate source identities, page-title collisions, and unresolved block
references. The command creates no report file and has no network destination.
It must never emit vault Markdown, snippets, paths, titles, UUIDs, exception
text, host names, or user-vault identifiers.

The implementation validates every report level, permits only declared finding
codes, rechecks the total byte bound while reading, and rejects invalid direct
runtime-limit values. Its process-local socket guard is not an operating-system
sandbox; filesystem races remain a documented residual boundary.

## Terminal local evidence at `eecea20`

- Focused CLI and assurance suite: 49 passed.
- Full `rtk make all`: 614 collected tests passed; Ruff, mypy, documentation,
  vendor-name, and coverage gates passed.
- `rtk make vendor-name-check`: passed.
- `rtk git diff --check origin/main...HEAD`: passed.
- Local audit-code cycle check: `cycleCount: 0`.
- The raw, unfiltered full diff from `origin/main` through `eecea20` had
  SHA-256 `6396fa22f1efef469ef6cd7d9b0b3a90e7fd4c68942a72de59b28850d2e59310`.

This evidence proves only the stated local head. Re-run all relevant checks and
freeze a new raw full-diff hash after any further commit, rebase, or review
correction.

## Review questions

1. Does the full patch preserve the aggregate-only report boundary on every
   worker outcome, including errors, timeouts, malformed input, and unsafe
   worker data?
2. Are path, symlink, read-size, process, and networking claims accurately
   bounded, with no implication of an operating-system sandbox or race-free
   filesystem isolation?
3. Does the command preserve the documented parser/graph invariants without
   promoting the internal implementation to the stable package-root API?
4. Do the ADR, reference guide, changelog, plan, goal, and documentation log
   make only claims supported by the exact code and local evidence?
5. Are the tests sufficient for the changed safety boundaries, or is a focused
   regression still required before publication?

## Required next sequence

1. Recheck the exact branch, worktree cleanliness, `HEAD`, and live
   `origin/main`; do not use cached remote state for a publication decision.
2. Freeze the raw `git --no-pager diff --no-ext-diff --binary --full-index
   origin/main...HEAD` bytes and hash them without filtering.
3. Obtain the independent GPT-5.6 Sol review of that exact full patch only
   after explicit permission to transmit repository material. Treat its output
   as advisory until each finding is reproduced or rejected against source and
   deterministic evidence.
4. If anything changes, add a non-amending local correction, repeat exact-head
   qualification, and obtain a review of the new full patch.
5. Stop before push. Refresh live GitHub state and publish only after separate
   user authorization. Required hosted checks then remain a distinct gate.

## Boundaries that must survive

- Do not copy or adapt AGPL-covered code, tests, corpora, schemas, module
  structures, control flow, or documentation.
- Do not add an external parser/oracle, telemetry, upload, report persistence,
  package dependency, package-root export, or CI service.
- Do not claim #103 incremental/cold-load equivalence, #87 or #111 performance
  evidence, external-parser parity, release qualification, or closure of #104
  or #108.
- Do not weaken deterministic UUID/tree relationships, vault containment,
  symlink handling, file limits, safe reporting, coverage, or documentation
  gates.

This handoff is a local review checkpoint, not a release, hosted-validation,
pull-request, merge, or public-availability receipt.
