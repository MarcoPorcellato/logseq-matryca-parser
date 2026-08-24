# Assurance delivery handoff to GPT-5.6 Terra — 2026-08-21

This handoff records a checkpoint; it is not a validation or release receipt.

## Safe resume point

- Repository: `/Users/marco1/Documents/CODICE con VS CODE/logseq-matryca-parser`
- Additional worktree: none; the maintainer prefers in-place execution when a
  clean checkout can preserve every branch remotely.
- Branch: `feat/graph-mutation-coherence-103`
- Saved planning commit: `e02f9be` (`docs(graph): define coherent mutation delivery`)
- Base: `main@8e2bc893dea34b756edb6632e04917b04a68c1e6`
- Remote feature branch: published as `feat/graph-mutation-coherence-103` when
  this handoff was finalized.
- Feature pull request: draft PR #180, base `main`; it contains only the design,
  plan, and handoff documents at this checkpoint.
- Working tree before this handoff was added: clean.

Re-verify every anchor live. The commit that contains this handoff necessarily
postdates `e02f9be`; use `git rev-parse HEAD` as the exact execution head.

## Completed and terminally verified

- PR #178 was reverified as `CLEAN` and `MERGEABLE` with eight successful
  checks at source head `8689976ea02d718d855cabc0d42156d398cd8e79`, then
  squash-merged to `main` as
  `8e2bc893dea34b756edb6632e04917b04a68c1e6` under explicit maintainer
  authorization.
- PR #179 was retargeted from `fix/parser-pathological-refresh-87` to `main`.
  Its release branch was reconciled non-destructively with `main` and pushed at
  exact head `8d1c35ff3243fb79a26b18761a6b4c6e4e7f1c85`.
- The corrected PR #179 diff contains only 11 release files. The reconciled
  local head passed `make all`: 692 tests, 89.82% coverage, Ruff, mypy,
  documentation, vendor-name, and test gates all succeeded.
- The #103 architecture was approved by the maintainer. The binding design is
  `docs/superpowers/specs/2026-08-21-graph-mutation-coherence-design.md`; the
  executable TDD plan is
  `docs/superpowers/plans/2026-08-21-graph-mutation-coherence.md`.
- Fresh audit-code analysis at the release checkpoint classified
  `invalidate_and_reload_page` as HIGH impact with six direct and eight total
  dependents across four flows. Source import cycles were zero.
- Deterministic controller probes reproduced lost concurrent append, mixed
  page/node publication, and failed-refresh registry loss. Those probes were
  temporary diagnostics and were deleted; the implementation plan requires
  permanent RED tests before production edits.

## Saved but not yet qualified

- Planning commit `e02f9be` contains 855 lines of approved #103 design and TDD
  instructions. It passed `git diff --check`, vendor-name validation, and the
  documentation validator through the existing `.venv`.
- `make docs-check` on the feature branch was unavailable because `uv` attempted
  to download `hatchling==1.30.1` while sandbox networking was unavailable.
  The same validator executed directly with `.venv/bin/python` and exited 0.
  Terra must run the normal Make gate after dependency admission is available.
- No #103 production code or permanent concurrency test has been written.

## External state at handoff preparation

- PR #179: draft, base `main`, head
  `8d1c35ff3243fb79a26b18761a6b4c6e4e7f1c85`, `CLEAN`, and `MERGEABLE`. A
  final live readback on 2026-08-21 showed all eight hosted checks successful.
  Reverify before any merge because this is a checkpoint, not future proof.
- PR #180: draft, base `main`, and `MERGEABLE` at publication. Its initial
  hosted checks were still converging when this handoff was finalized; obtain a
  fresh terminal readback before treating the PR as qualified.
- v1.8.1: not merged, tagged, released, or published. Merge and release remain
  separate maintainer gates.
- Issue #103: open. Design approved; implementation and eventual closure still
  require exact-head evidence and separate publication gates.
- No active worker or shell process remains at this checkpoint.

## Sol rulings that Terra must preserve

### Issue #103

- One `RLock` per graph, never a process-global lock.
- Candidate mappings are copied and completed before publication; previously
  published dictionaries and backlink lists are never mutated.
- Supported readers capture one graph version. `graph.pages` remains a
  point-in-time compatibility mapping; direct external mutation is unsupported.
- The writer lock covers target lookup through atomic replacement and reload.
- Incremental reload must retain targeted backlink repair; no global backlink
  rebuild is authorized.
- User callbacks are ordered after successful publication on a private daemon
  dispatcher and cannot block graph mutation.
- Tests use barriers/events and bounded waits, not sleeps.

### Issue #104 after #103

Existing evidence already covers offline provenance-safe fixtures, hashes and
LF normalization, exact snapshots, semantic round trips, generated malformed
profiles, and a separately scheduled broad adversarial workflow. Do not
duplicate those facilities.

The remaining bounded work is:

1. add an explicit discovery-order invariance test for canonical snapshots;
2. consume #103's create/edit/delete/rename projection matrix as lifecycle
   compatibility evidence;
3. map every #104 checkbox to an exact test/workflow receipt;
4. run `make all` and update the issue without overstating filesystem-security
   tests as corpus fixtures.

This work belongs on a separate branch after the #103 implementation base is
stable.

### Issue #111 after semantic stabilization

Preserve the existing deterministic 96-page diagnostic profile. Extend the
generator with explicit immutable profiles for 1,000 and 10,000 pages rather
than changing the fast profile's identity. Large profiles stay outside default
CI.

The required scenario matrix is cold load, one-page incremental edit, content
search, tag search at controlled node counts, and context chunks both without
and with embeds. Every scenario retains semantic gates and emits source-free
receipts with profile/schema identity, source hash, aggregate counts, Python
minor, OS, architecture, dependency-lock hash, warmups, sample count, median,
p95, and native RSS unit.

Do not invent numeric budgets. First collect retained exact-environment
baselines from at least three independent eligible runs. Budget promotion is a
later statistical Sol gate because no current data can justify thresholds.
Until that gate, receipts are observations and the policy must reject
cross-environment comparisons or public performance claims.

## Cost-aware execution routing

- Terra is the controller for #103 implementation, cross-file integration,
  TDD loops, and focused/full local validation.
- Luna may handle bounded read-only inventory, deterministic log distillation,
  and English documentation drafting from settled facts.
- Use deterministic tools before any worker.
- Escalate to Sol only for a new architecture/security ruling, final
  concurrency adjudication, merge/release qualification, or #111 statistical
  budget promotion.
- No LM Studio or other local model may be used.

## Exact Terra resume sequence

1. Run `rtk git status --short --branch`, `rtk git rev-parse HEAD`, and
   `rtk git rev-parse origin/main`; preserve any drift before acting.
2. Read `AGENTS.md`, the #103 design, this handoff, and the complete #103 plan.
3. Verify PR #179 live. Record running or failed checks accurately; do not merge
   or release without a fresh maintainer gate.
4. Run Task 0 of the #103 implementation plan, including focused baseline,
   refreshed impact, and zero-cycle checks.
5. Start Task 1 with permanent RED tests. Do not write production code until
   both rollback and mixed-reader tests fail for the expected behavioral reason.
6. Execute the plan continuously through local qualification, using a fresh
   bounded worker and independent review per task where cost-effective.
7. Stop before push, PR ready state, merge, issue closure, or release unless the
   corresponding authority is explicit and current.

## Persistent goal for the Terra continuation

Copy this objective into the resumed task if the active goal is unavailable:

> Implement issue #103 from
> `docs/superpowers/specs/2026-08-21-graph-mutation-coherence-design.md` and
> `docs/superpowers/plans/2026-08-21-graph-mutation-coherence.md`, starting from
> the exact verified branch checkpoint in
> `docs/internal/ASSURANCE_TERRA_HANDOFF_2026-08-21.md`. Use TDD and cost-aware
> delegation, preserve all security and synchronous-API boundaries, and qualify
> the exact head. Then prepare the remaining #104 lifecycle/discovery evidence
> and #111 scalable harness in separate dependency-ordered branches. Do not
> merge, close issues, promote performance budgets, or release without the
> separately required maintainer gates.

## Boundaries that must survive the model switch

- Repository documents and source are authoritative; conversation summaries
  and worker reports are not proof.
- Running, skipped, stale, mismatched, or partial evidence is not a pass.
- Do not rewrite release history or force-push #179.
- Do not use cross-process claims for the #103 one-process contract.
- Do not add a database, search engine, parser rewrite, public coordinator API,
  or broad async architecture.
- Do not publish vault content, paths, titles, UUIDs, exception text, host names,
  credentials, caches, or local audit state.
