# Local Assurance Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` to execute this plan task by task.

**Goal:** Raise meaningful coverage of the privacy-safe local graph assurance
worker from 55% to at least 90%, with 95% as a stretch target, without weakening
its fail-closed or source-free contract.

**Architecture:** Add deterministic characterization tests around filesystem
enumeration, bounded reads, parser aggregation, report validation, process
isolation, and cleanup. Keep production unchanged unless a new failing test
demonstrates an actual contract defect.

**Tech Stack:** Python 3.12, pytest, pytest monkeypatch and tmp paths, standard
library multiprocessing/socket/path primitives, Ruff, mypy, coverage.py.

**Spec:**
`docs/superpowers/specs/2026-08-24-meaningful-test-coverage-design.md`

## Global constraints

- Exact base:
  `main@01faa3b5b66a5eda117968093a10080c67c1accf`.
- Modify `tests/test_local_graph_assurance.py` first. Add another assurance test
  file only when it materially improves ownership or readability.
- Never expose a path, title, UUID, Markdown fragment, exception text, host
  name, or credential in returned reports or committed fixtures.
- Never use network access, `time.sleep()`, unbounded process waits, or a real
  private vault.
- Prefer real temporary files. Mock only filesystem race boundaries and process
  lifecycle objects that cannot be exercised deterministically otherwise.
- Do not change production code to make it easier to test.
- For every new characterization test, record the production mutation it would
  detect. If production behavior must change, first demonstrate the focused
  RED failure and then implement the smallest correction.
- Every shell command starts with `rtk`.
- Do not push, open a PR, merge, close an issue, or release without a separate
  maintainer gate.

## Task 0: Establish receipts and coverage map

**Files:** none.

- [x] Verify branch, HEAD, base, and clean checkout.
- [x] Run the complete baseline gate.
- [x] Generate an exact JSON coverage report for the focused assurance tests
  and retain only aggregate/missing-line information in the ignored SDD ledger.
- [x] Record test count, assurance statement count, misses, and percentage.

Expected baseline: 718 tests globally; assurance module 301 statements, 134
misses, 55% coverage; repository total 88.51%.

## Task 1: Filesystem traversal and declared limits

**Files:**

- Modify: `tests/test_local_graph_assurance.py`
- Production: `src/logseq_matryca_parser/local_graph_assurance.py` only after a
  demonstrated defect.

- [x] Test directory enumeration failure returns only
  `vault.directory_read_error`.
- [x] Test entry metadata failure returns only `vault.entry_stat_error`.
- [x] Test ignored directories and non-Markdown entries do not affect observed
  counts.
- [x] Test a non-directory `pages` or `journals` root is rejected.
- [x] Test `max_file_bytes` and the traversal-stage `max_total_bytes` limits.
- [x] Run focused tests and inspect the exact missing-line delta.

Mutation sensitivity: these tests must fail if the corresponding fail-closed
return, skip rule, or limit comparison is removed or inverted.

## Task 2: Guarded reads and parser aggregation

**Files:**

- Modify: `tests/test_local_graph_assurance.py`
- Production: `src/logseq_matryca_parser/local_graph_assurance.py` only after a
  demonstrated defect.

- [x] Test guarded-read rejection for symlink/non-regular/outside-root/open
  failure conditions using the narrowest deterministic boundary.
- [x] Test descriptor identity and post-read size or identity revalidation.
- [x] Test invalid UTF-8 aggregation without source disclosure.
- [x] Test unclassified parser failure without exception disclosure.
- [x] Test structure invariant, duplicate synthetic identity, and duplicate
  source identity findings using controlled parsed pages.
- [x] Test multiple unresolved references preserve only an aggregate count.
- [x] Run focused tests and inspect the exact missing-line delta.

Mutation sensitivity: removing any read revalidation or finding emission must
make a named test fail.

## Task 3: Safe report and isolated worker lifecycle

**Files:**

- Modify: `tests/test_local_graph_assurance.py`
- Production: `src/logseq_matryca_parser/local_graph_assurance.py` only after a
  demonstrated defect.

- [x] Cover top-level schema/type/status failures and invalid numeric values in
  `_safe_report` without duplicating implementation tables.
- [x] Verify `passed`/findings consistency and JSON serialization failure.
- [x] Verify all guarded socket entry points are denied and restored even when
  the context exits through an exception.
- [x] Use deterministic fake process/context/queue boundaries to cover timeout,
  no-report, invalid-report, and worker unexpected-failure outcomes.
- [x] Assert queue/process cleanup without using elapsed-time expectations.
- [x] Run focused tests and inspect the exact missing-line delta.

Mutation sensitivity: bypassing validation, cleanup, termination, or restoration
must make the corresponding test fail.

## Task 4: Integrate, review, and qualify tranche A

**Files:**

- Modify only if needed for maintained references:
  `docs/superpowers/plans/2026-08-24-local-assurance-coverage.md`.

- [x] Review the complete diff for privacy, portability, implementation
  coupling, false assertions, and redundant cases.
- [x] Run the assurance tests with exact module coverage.
- [x] Run the complete repository coverage report.
- [x] Require at least 90% coverage for `local_graph_assurance.py`; continue
  toward 95% only while the design quality contract is satisfied.
- [x] Run `make all`, `make vendor-name-check`, and `git diff --check`.
- [x] Record exact HEAD, test count, module and repository coverage, remaining
  misses, and any production correction in the SDD ledger.
- [x] Commit the reviewed tranche, but stop before push or PR creation unless
  the maintainer provides that publication gate.

## Completion receipt

Tranche A was qualified on code/test head
`d99e738af4ed520218545ebbca1f81a82f05a9e0` before this documentation-only
closeout:

- focused assurance suite: 60 passed;
- assurance module: 304 statements, 24 misses, 92% statement coverage;
- assurance branch diagnostic: 90%;
- complete repository: 757 passed, 4,092 statements, 360 misses, 91.20%
  statement coverage;
- baseline-to-head repository delta: +39 tests, +2.69 percentage points, and
  110 fewer missed statements;
- independent whole-tranche review: PASS after portability and bounded timeout
  cleanup corrections;
- production correction: the timeout path now terminates and joins the worker,
  then cancels queue thread joining and closes the queue before returning;
- complete gate: `make all`, `make vendor-name-check`, and `git diff --check`
  passed.

The 95% module stretch was not pursued further. The remaining 24 lines are
primarily filesystem branches already exercised end-to-end in the spawned
worker; covering them again in-process would add duplicate tests or increasingly
artificial race mocks. The global coverage floor remains 80 because the wider
campaign has not yet reached its repository-wide 95% success criterion.

## Execution delegation

- Spark was preferred for bounded characterization work but was unavailable
  during this tranche.
- Luna implemented and reviewed the bounded test tasks and review-fix rounds.
- The controller retained integration, review reconciliation, stop decisions,
  exact-head verification, and the repository-wide gate.
