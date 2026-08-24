---
type: DesignSpecification
title: Meaningful test coverage campaign
description: A quality-first campaign that raises repository coverage through stable behavioral and security tests.
status: approved
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-24
verified: 2026-08-24
stale_after: 2026-11-22
base_commit: 01faa3b5b66a5eda117968093a10080c67c1accf
---

# Meaningful test coverage campaign

## Purpose

Raise test coverage as far as practical without weakening the suite through
implementation-coupled assertions, timing-sensitive tests, unsafe filesystem
operations, or exclusions added only to improve the percentage. Coverage is a
discovery instrument and regression signal; it is not a substitute for
behavioral, security, compatibility, or release evidence.

## Verified baseline

The isolated baseline at
`main@01faa3b5b66a5eda117968093a10080c67c1accf` passed `make all` with:

- 718 tests;
- 4,089 measured statements;
- 470 missed statements;
- 88.51% total statement coverage;
- an existing global `fail_under` value of 80.

The principal gaps are `local_graph_assurance.py` at 55%, `graph.py` at 85%,
`agent_writer.py` at 84%, and user-facing CLI or adapter failure paths. The
main parser is already at 97%, so parser-line maximization is not the first
priority.

Re-run the exact baseline before relying on these values after any base update.

## Success criteria

1. Reach at least 95% total statement coverage on the exact campaign head.
2. Continue toward 97% or higher while every added test protects supported,
   security-relevant, compatibility-relevant, or user-visible behavior.
3. Stop numeric expansion when remaining lines require platform-specific races,
   unsupported internal states, framework internals, or mocks that merely
   restate the implementation.
4. Generate branch coverage as a diagnostic before the final policy update;
   do not silently replace the established statement-coverage gate.
5. Raise `fail_under` only after the exact head passes the complete repository
   gate with stable margin.

At the verified baseline, reaching 95% requires covering at least 266 current
misses; reaching 97% requires covering at least 348. Source changes may alter
the denominator, so exact-head reports remain authoritative.

## Test quality contract

- Prefer public APIs and observable results.
- Test private helpers only when they are the narrow boundary for a security,
  isolation, validation, or deterministic failure contract.
- Use `tmp_path`, bounded events, deterministic fakes, and explicit monkeypatch
  boundaries. Do not use real network access or timing sleeps.
- Assert status, finding code, aggregate count, filesystem state, graph state,
  or exit behavior. Do not assert that a mock was called as the sole outcome.
- Keep private vault paths, titles, UUIDs, source content, exception text, host
  names, and credentials out of receipts.
- Do not add `# pragma: no cover`, omit modules, or weaken existing assertions
  solely to increase the metric.
- A characterization test for existing behavior must identify the production
  mutation it would detect. A production fix requires a failing regression test
  before implementation.
- Keep optional dependencies lazy and simulate their absence only at a stable
  import or adapter boundary.

## Delivery sequence

### Tranche A: local assurance

Raise `local_graph_assurance.py` from 55% to at least 90%, with 95% as the
module stretch target. Cover traversal failures, declared limits, guarded file
reads, parser failures, structural findings, safe-report validation, worker
timeout, missing result, invalid result, and network restoration.

### Tranche B: graph and bounded writes

Target at least 92% for `graph.py` and 95% for `agent_writer.py` and
`agent_press.py`. Prioritize collision routing, incremental registry cleanup,
backlink repair, malformed metadata, atomic non-mutation failures, and writer
security boundaries. Concurrency tests remain event-driven and bounded.

### Tranche C: CLI, exporters, and adapters

Cover user-visible optional-dependency failures, invalid option resolution,
serialization edge cases, Obsidian anchor allocation, metadata recursion,
orphan handling, custom embed expanders, and module invocation. Avoid redundant
permutations that traverse identical code.

### Tranche D: residual audit and policy

Review every remaining miss by category, add only defensible tests, record
intentional residuals, produce statement and branch diagnostics, and raise the
global floor to the highest value with a reasonable stability margin. Update
maintained quality documentation and exact test counts only in this final
tranche.

Each tranche is independently reviewable and may be published as a stacked PR.
No push, PR creation, merge, issue closure, or release is implied by this
design.

## Cost-aware execution

- Deterministic coverage reports and targeted source inspection come first.
- Spark handles bounded single-file characterization tests with exact briefs.
- Luna handles process isolation, optional dependency, and more involved error
  simulations when Spark is insufficient.
- Cross-module graph or writer judgment, security adjudication, integration,
  and exact-head qualification remain with the controller.
- Every worker report is verified against the diff and fresh test output.

## Rejected alternatives

1. **A 100% mandate.** Rejected because it incentivizes brittle tests and
   unsupported-state construction. A higher percentage remains welcome when
   the quality contract is satisfied.
2. **Immediate `fail_under = 95`.** Rejected because it would make every
   intermediate commit fail without proving new behavior.
3. **Excluding low-coverage modules.** Rejected because assurance and CLI
   failure paths are part of the shipped product.
4. **One oversized coverage PR.** Rejected because assurance, graph/writer, and
   adapter risks need distinct review surfaces.

## Verification gates

For every tranche:

```bash
rtk uv run pytest -q <focused tests>
rtk uv run pytest --cov=src/logseq_matryca_parser --cov-report=term-missing tests/
rtk make all
rtk make vendor-name-check
rtk git diff --check
```

The final receipt records exact HEAD, test count, statement totals, misses,
coverage percentage, per-module residuals, and whether branch coverage was
diagnostic or enforced.
