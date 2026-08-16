# M1-A corrective hardening restart handoff — 2026-08-16

## Safe resume point

- Repository: `/Users/marco1/Documents/CODICE con VS CODE/logseq-matryca-parser`
- Isolated worktree: none; the dedicated delivery branch is checked out in the
  primary repository directory.
- Branch: `agent/parser-assurance-m1`
- HEAD: `8806205c35b104ed65d00a273acc9eeca572ae38`
- Base and local `origin/main`: `e2a3f9a8d190fd115028d0ad344c31fded0357d9`
- Remote branch: none; the delivery branch has not been pushed.
- Pull request: none.
- Working tree after preparation: modified canonical plan, persistent goal, and
  documentation log; this handoff is untracked. Re-verify the exact status
  before editing.
- Persistent goal state: paused; only the user may resume it.

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

## Saved but not yet qualified

- `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md` — M1-B contract,
  gates, checklist, and ledger update.
- `docs/goals/LSDOC_PARSER_ASSURANCE_GOAL.md` — exact rejected anchor and resume
  pointer.
- `docs/log.md` — documentation chronology for this correction checkpoint.
- `docs/internal/M1A_CORRECTIVE_HARDENING_RESTART_HANDOFF_2026-08-16.md` — this
  preparation checkpoint.

Do not treat these uncommitted documentation changes as passed validation.

## Corrective work packages

| Order | Owner | Files | Required result |
|---|---|---|---|
| 1 | Primary semantics; Spark may scaffold tests | `tests/parser_assurance/projection.py`, `tests/test_compat_corpus.py` | Comma-aware canonical sequences for `tags`, `page-tags`, `alias`, and `aliases`; property-origin wikilinks removed by count; authentic matching content links preserved. |
| 2 | Primary security; Spark may scaffold negative tests | `.gitattributes`, `tests/parser_assurance/corpus.py`, `tests/test_compat_corpus.py` | Raw-byte SHA remains truthful under forced LF; valid-only diagnostics must be empty; schema versions and tab size reject Boolean values. |
| 3 | Spark mechanical edit; primary integration review | `Makefile`, `tests/test_quality_gate_contract.py` | Snapshot generator is explicitly included in mypy and protected by a contract test. |
| 4 | Primary integration | `CHANGELOG.md`, `docs/log.md`, canonical plan, persistent goal | Claims match the corrected implementation and preserve `8806205` as rejected historical evidence. |
| 5 | Primary Git/evidence | local commits and exact-head receipts | New corrective implementation commit, exact-head qualification and frozen review, then a separate evidence-only documentation commit. |

No package or runtime source file belongs to these work packages.

## Active or stopped work

- Workers: two Spark read-only inventories completed; no worker has write
  ownership and their outputs are advisory only.
- Processes: none expected; verify before resuming.
- Resource admission: not checked; no local-model or LM Studio work is allowed.

## External state

- Required checks: not applicable until a branch is pushed and a PR exists.
- Remote freshness: local `origin/main` was `e2a3f9a`; live GitHub must be
  refreshed immediately before publication.
- Receipt: none.
- Human gate: resume of the paused goal; commit, push, PR, merge, and release
  remain separate gates.

## Exact resume sequence

1. Run `rtk git status --short --branch`, `rtk git rev-parse HEAD origin/main`,
   and verify the three prepared documentation files against this handoff.
2. Re-read `AGENTS.md`, the canonical plan, the persistent goal, and this
   handoff. Confirm that the goal has been resumed by the user.
3. Implement work package 1 and first add regressions for:
   `[[Foo]]` plus `tags:: Foo`; duplicate content/property occurrences;
   `[[Project Authored]], [[Fixture]]`; and a comma inside `[[New York, NY]]`.
4. Implement work package 2 with `tests/fixtures/compat/** text eol=lf`, strict
   empty diagnostics, exact integer types, and negative tests.
5. Implement work package 3 and prove its Makefile dry-run contract.
6. Run the focused tests and targeted Ruff/mypy commands from the canonical
   plan. Regenerate exact snapshots only if the exact profile changed; semantic
   fixes alone must not rewrite them.
7. Run `rtk make all`, `rtk make vendor-name-check`, the exact diff check, and
   the zero-cycle audit. Review every change against #104-A scope.
8. Create a new corrective implementation commit; do not amend or delete
   `8806205`. Re-run every required gate on the clean exact commit.
9. Delegate one frozen read-only review to Spark, then adjudicate every finding
   against source and deterministic probes.
10. Update the canonical ledger with the implementation SHA and evidence in a
    separate documentation-only commit. Qualify that exact head locally.
11. Stop before push. Refresh live `origin/main`, rules, and GitHub state only
    when the user separately authorizes publication.

## Boundaries that must survive the restart

- Do not push or open a PR for `8806205`.
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
