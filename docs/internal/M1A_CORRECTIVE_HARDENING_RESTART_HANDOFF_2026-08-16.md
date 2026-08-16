# M1-B post-correction pre-push handoff — 2026-08-16

## Safe resume point

- Repository: `/Users/marco1/Documents/CODICE con VS CODE/logseq-matryca-parser`
- Isolated worktree: none; the dedicated delivery branch is checked out in the
  primary repository directory.
- Branch: `agent/parser-assurance-m1`
- Corrective implementation: `9e8708eef9cfa63fd9f392f5b5a9e7df564072e7` (non-amending, files-only corrective pass)
- Base and local `origin/main`: `e2a3f9a8d190fd115028d0ad344c31fded0357d9`
- Remote branch: none; the delivery branch has not been pushed.
- Pull request: none.
- Evidence commit: this handoff, the canonical plan, persistent goal, and
  documentation log record the local result separately from the implementation.
  Re-verify its exact SHA after committing before any review or publication.
- Persistent goal state: active through frozen Sol review; push, PR, merge, and
  release still require separate user authorization.

## Completed and terminally verified

- Commit `8806205` exists locally and was clean when qualified.
- `rtk uv run python scripts/update_compat_snapshots.py` passed on `8806205`.
- Focused parser-assurance tests passed: 32 tests before the independent
  correction review.
- `rtk make all` and a compact full-suite run passed on `8806205`: 556 tests,
  92.07% coverage.
- `rtk make vendor-name-check`, commit diff check, and audit-code cycle check
  passed; `src/` had zero cycles.
- A later independent full-patch review returned `NEEDS_CORRECTION`; therefore
  the successful checks do not qualify `8806205` for publication.
- Primary runtime probes reproduced both projector P1s:
  `[[Foo]]` plus `tags:: Foo` loses the content wikilink, and
  `[[Project Authored]], [[Fixture]]` becomes one malformed token.
- Primary manifest probes proved that non-empty `expected_diagnostics`, Boolean
  schema versions, and Boolean `tab_size` are accepted.
- Source inspection confirmed raw-byte fixture hashing without an LF checkout
  policy and omission of `scripts/update_compat_snapshots.py` from the Makefile
  mypy command.
- Corrective implementation `996c5a5` passed its exact-head local checks, and
  separate evidence commit `6fcf4b2` froze the first Sol review surface.
- That Sol review returned `NEEDS_CORRECTION`: property-link extraction ignored
  parser shielding, so a property literal such as ``note:: `[[Foo]]` `` (and
  equivalent HTML-comment, math, fence, query-macro, or query-region forms)
  could remove an authentic visible `[[Foo]]`; `#[[Foo]]` also projected as
  `[[Foo]]` instead of `Foo`.
- Corrective implementation `9e8708e` repaired all reproduced defects without
  modifying `src/`: the test oracle canonicalizes comma-separated references,
  subtracts property-origin wikilinks from the tail by multiplicity (including math,
  backtick/tilde fences, query macro, and query-region contexts), forces LF corpus
  bytes, rejects non-empty valid-fixture diagnostics and Boolean integer values,
  and type-checks the snapshot generator. Exact-head validation passed on a clean
  worktree: seven focused regressions, snapshot freshness, `make all` with 579 tests
  and coverage gate, Ruff, mypy, documentation validation, vendor-name check, diff
  check, and zero-cycle audit. No source, package, dependency, API, or runtime
  behavior changed.

## Frozen scope and remaining gates

- Review the frozen diff from `origin/main` through the exact evidence-commit
  HEAD with GPT-5.6 Sol. Recheck every finding against source and deterministic
  evidence; do not treat a review request as an approval.
- Refresh remote `origin/main`, rules, and GitHub state only after the user
  authorizes publication. Do not publish `8806205`, `996c5a5`, or `6fcf4b2`
  independently as qualified checkpoints; only the final reviewed branch may
  be pushed, and only with explicit authorization.
- Obtain terminal hosted checks and the user’s separate approval before opening
  a PR, merging, or releasing.

## Completed corrective work packages

| Order | Owner | Files | Required result |
|---|---|---|---|
| 1 | Primary semantics | `tests/parser_assurance/projection.py`, `tests/test_compat_corpus.py` | Complete: comma-aware canonical sequences and reverse count-subtraction preserve authentic content links and order. |
| 2 | Primary security | `.gitattributes`, `tests/parser_assurance/corpus.py`, `tests/test_compat_corpus.py` | Complete: raw-byte LF policy, empty valid diagnostics, and exact integer guards. |
| 3 | Primary quality gate | `Makefile`, `tests/test_quality_gate_contract.py` | Complete: snapshot generator appears in mypy and has a dry-run contract test. |
| 4 | Spark scaffolding, primary integration | `tests/test_compat_corpus.py`, `tests/parser_assurance/projection.py` | Complete: Spark added bounded regressions for the first Sol findings; the primary extended the shielding matrix, implemented the correction, and retained all adjudication authority. |
| 5 | Primary integration | `CHANGELOG.md`, `docs/log.md`, canonical plan, persistent goal | Complete in implementation/evidence commits; claims preserve historical failures and superseded receipts without presenting them as current qualification. |
| 6 | Primary Git/evidence | local commits and exact-head receipts | Implementation exact-head qualification complete; this evidence commit then needs its own exact-head qualification and frozen Sol review. |

No package or runtime source file belongs to these work packages.

## Active or stopped work

- Workers: prior Spark inventories remain advisory.
- M1-B sequence fact: Spark added the bounded regression-test scaffolding and the
  primary integrated it. No Luna fallback was needed.
- Processes: none expected; verify before resuming.
- Resource admission: not checked; no local-model or LM Studio work is allowed.

## External state

- Required checks: not applicable until a branch is pushed and a PR exists.
- Remote freshness: local `origin/main` was `e2a3f9a`; live GitHub must be
  refreshed immediately before publication.
- Receipt: none.
- Human gate: resume of the paused goal; commit, push, PR, merge, and release
  remain separate gates.

## Exact pre-push sequence

1. Run `rtk git status --short --branch`, `rtk git rev-parse HEAD origin/main`,
   and qualify the separate evidence commit on its exact head.
2. Freeze `git diff --binary origin/main...HEAD` and ask GPT-5.6 Sol to review
   the whole patch against the M1-B contract, including documentation claims.
3. Adjudicate every review finding with source and deterministic probes. If any
   correction is necessary, create a new local correction and repeat exact-head
   qualification; do not amend historical commits.
4. Stop before push. Refresh live `origin/main`, rules, and GitHub state only
   when the user separately authorizes publication.

## Boundaries that must survive the restart

- Do not publish historical checkpoints `8806205`, `996c5a5`, or `6fcf4b2`
  independently as qualified evidence.
- Do not modify `src/`, root package exports, package metadata, dependencies, or
  runtime behavior for M1-B.
- Do not copy or adapt AGPL code, tests, corpus, schemas, or documentation.
- Keep all fixtures original, offline, Apache-2.0, and free of private vault
  content or host paths.
- Do not weaken path, symlink, atomic-write, identity, determinism, diagnostics,
  coverage, or documentation gates.
- Do not close #104; M1-A remains only its compatibility-corpus foundation.
- Do not call `8806205`, uncommitted preparation, or a non-hosted result E2/E4.

This handoff is a preparation checkpoint, not a validation receipt.
