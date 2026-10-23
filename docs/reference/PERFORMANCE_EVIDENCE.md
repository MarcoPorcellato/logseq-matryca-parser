---
type: ReferenceGuide
title: Runtime evidence
description: Test-only diagnostic runtime evidence and pure decision-comparison metadata contracts.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-23
verified: 2026-10-23
stale_after: 2027-02-20
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Runtime evidence

Run the harness from an exact committed checkout:

```bash
uv run python -m tests.performance.runtime_evidence
```

The command creates only a deterministic synthetic vault in temporary
directories, prints one source-free JSON receipt to stdout, and does not
persist a receipt. It does not accept a vault path, read a private vault, or
send network traffic.

## What the receipt measures

The fixed synthetic source contains 96 pages, 24 blocks on each ordinary page,
cross-page links, aliases, tags, and one 1024-level outline. The receipt binds
that source to a schema version, SHA-256 fingerprint, and aggregate counts; it
does not include generated Markdown, source paths, page titles, block UUIDs,
host names, or exception text.

Each available scenario performs three warm-ups and 21 measured executions with
`time.perf_counter_ns`. The receipt reports the median and nearest-rank p95 in
nanoseconds. A duration is valid only when the scenario's semantic gate passes:

- `deep_parse_1024` validates tree invariants on the bounded deep outline.
- `cold_graph_load` validates the canonical-page count after a new graph load.
- `incremental_alias_move_reload` compares ordered backlinks from an
  incremental title-and-alias move reload with a cold load of the same source.
- `search_content` validates the fixed search-result count and identities.
- `synapse_context_chunks` validates chunk count and lineage metadata when the
  optional adapter is available.

If the optional SYNAPSE runtime dependency is unavailable, its scenario is
reported as `unavailable` with reason `optional_adapter_unavailable`; it is not
silently skipped or counted as a pass.

The process high-water RSS is included only when the host supplies it. Its unit
remains native: `bytes` on Darwin and `KiB` on supported Unix systems. It is an
observation rather than a normalized memory measure.

## Interpretation and noise policy

A receipt is a local diagnostic, not a cross-machine comparison, CI timing
gate, release qualification, or general performance guarantee. Interpret it
only with its recorded Python version, platform system, and machine labels.

- Run only from an exact committed head.
- When a maintainer needs to retain an observation, store the unmodified JSON
  outside the repository and only with explicit authority.
- Close competing local workloads when practical and repeat only with the same
  command and environment.
- Never average or compare observations across machines.
- Investigate a semantic-gate failure before considering any duration value.
- A timing budget, public performance statement, or release use needs a
  separately approved baseline and promotion decision.

The harness is private test support under `tests/performance/`; it adds no
package API and no normal CI duration or RSS threshold.

## Decision comparison contract

The separate `matryca-decision-observation` schema, version 1, supports future
reviewed comparisons for issue [#111](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/111).
It does not change the legacy diagnostic command, schema or small-vault
builder described above.

The implementation is pure test support in
[`tests/performance/comparison_contract.py`](../../tests/performance/comparison_contract.py).
It reads no files, measures no operation, launches no workers and adds no
package or CLI API. Its four entrypoints accept in-memory data:

- `parse_comparison_json` decodes bounded JSON and rejects duplicate keys.
- `validate_comparison_receipt` validates an already decoded object; it cannot
  recover duplicate keys discarded by another decoder.
- `assess_observation` checks one immutable receipt against explicit trusted
  admission and comparison-policy inputs.
- `assess_comparison` checks the entire predeclared selection, including failed
  or unavailable attempts. It never chooses a successful subset.

Objects have closed fields and strict types. Booleans are not integer counts;
timings retain all 21 integer samples, their median and nearest-rank p95.
Unknown fields, paths and arbitrary error text are rejected without echoing
their values. JSON input is limited to 65,536 characters and UTF-8 bytes;
a selected comparison contains at most 256 observations. These limits are
validation bounds, not permission to execute workloads.

### Valid metadata is not verified execution

A structurally valid receipt does not prove that a workload ran, the hashes
describe its actual source, semantics passed, or workers were cleaned up.
Private, evidence-reviewed attestations bind the canonical receipt and exact
comparison policy to source, installed dependencies, environment, dataset,
workload, execution, independence and cleanup evidence. The validator checks
those supplied bindings; it does not discover or independently authenticate
the evidence.

Policy, invariant and ordered-selection hashes have distinct canonical
framing. A comparison requires its exact declared cells and assignments,
one matching admission per observation and at least three independently
substantiated outer launches per cell. Three warmups and 21 samples inside
one observation do not satisfy that independence requirement. Repeated outer
execution IDs and duplicate observation or cell IDs cannot qualify.

Receipt outcomes remain honest: available observations require successful
semantics and complete timing; invalid observations retain truthful counters
but no accepted durations; unavailable capabilities retain `not_run` semantics,
zero samples and no fabricated successful execution. An unsupported runtime
produces a separate rejection, not an observation with invented supported
labels.

The eligibility verdict is `eligible`, `invalid`, `unavailable` or
`incomparable`. It concerns supplied metadata for one declared purpose,
not parser correctness, a performance guarantee or execution authority.
When multiple reasons apply, invalid takes precedence over unavailable,
then incomparable; reasons remain sorted and deduplicated.

### Purpose-specific evidence

- Calibration requires the scenario's primary phase; memory may be unavailable.
- Cache-design comparisons require complete-load timing for both cold-instance
  and unchanged-repeat cells, plus separately measured parse spans and reviewed
  attribution for the repeat. A parse span is not an exclusive recoverable
  cost or a measured cache speedup.
- Executor-design comparisons require end-to-end timing that includes all
  applicable startup, transfer, coordination and shutdown costs, and verified
  process-tree memory for every mode, including the baseline. Separate transfer
  or startup samples are not required when those costs are included honestly.

Missing memory is unavailable, never zero. Native units remain in the record;
overflow-checked KiB-to-byte arithmetic cannot turn coordinator-only RSS into
worker-inclusive coverage. No process-tree collector is implemented or
qualified by this contract.

Comparative purposes also require exact threshold identity and reviewed
predeclaration before selected runs. The validator applies no numerical
budget and produces no cache or executor GO/NO-GO decision.

### What remains deferred

Immutable descriptors define 96-, 1,000- and 10,000-page vault profiles with
3,304, 25,000 and 241,000 expected blocks respectively. Only their metadata is
implemented here. The larger generators, actual dataset fingerprints and
runtime workload admission remain future work; the legacy no-argument small
builder is unchanged.

The focused #87 pathological input and #113 deep-refresh case need their own
reviewed source, descriptor and semantic manifest before execution. A guessed
1,148-line string is not the #87 workload.

Deterministic tests in
[`tests/test_performance_comparison_contract.py`](../../tests/test_performance_comparison_contract.py)
use synthetic metadata and attestations to check contract behavior only.
They do not constitute real admitted observations, benchmark results or
additional Logseq conformance evidence. No benchmark runner, native adapter,
new collector, cache, executor-default change or CI timing gate is added.
Issue #111 remains open; actual measurements, budgets and separate cache/process
decisions require later reviewed plans and execution authority.
