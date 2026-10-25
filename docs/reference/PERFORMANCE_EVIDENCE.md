---
type: ReferenceGuide
title: Runtime evidence
description: Diagnostic evidence, deterministic fixtures, small-graph semantics, injected sampling, and unmeasured native bindings.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-24
verified: 2026-10-24
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

### Deterministic source fixtures

The private [decision-vault builder](../../tests/performance/decision_vault.py)
implements the fixed `decision-vault-generator` namespace, version 1. It accepts
only the three profile IDs below and returns an immutable in-memory synthetic
vault. It does not accept a path, arbitrary page count, seed or external content.
The small profile delegates to the unchanged no-argument legacy builder.

| Profile | Files | Source block lines | Source bytes |
|---|---:|---:|---:|
| `vault-small-96-v1` | 96 | 3,304 | 1,107,557 |
| `vault-scale-1000-v1` | 1,000 | 25,000 | 1,532,437 |
| `vault-scale-10000-v1` | 10,000 | 241,000 | 5,762,437 |

Each profile contains ordinary pages with 24 blocks and the same 1,024-node
deep-outline source. Logical POSIX paths and bytes retain the legacy UTF-8/LF
construction. Dataset SHA-256 frames each sorted path, NUL, content and NUL;
these fingerprints identify source bytes, not a measured graph:

| Profile | Dataset SHA-256 |
|---|---|
| `vault-small-96-v1` | `adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583` |
| `vault-scale-1000-v1` | `bba08886accc6d7a92253ba033fb8149f3af93e52428f61470c6c4f7a4e06e01` |
| `vault-scale-10000-v1` | `47e33f710c722aaaefee822a304bb4a65bc68149c111705e106de92f305b7c12` |

[Default fixture tests](../../tests/test_performance_decision_vault.py) check
the small profile, closed input selection, import laziness and identity
sensitivity. Larger profiles are not constructed, parsed or materialized by
default CI. Their [explicit scale checks](../../tests/performance/decision_vault_scale_checks.py)
verify all generated bytes against independent templates and frozen literal
fingerprints, repetition, the unchanged deep source and rejected mutations.
Select the scale file explicitly in an already prepared test environment:

```bash
uv run --locked --no-sync --offline python -m pytest -q tests/performance/decision_vault_scale_checks.py
```

The scale filename intentionally falls outside default pytest test-discovery
patterns; imports and collection construct no fixture. Static checks still
cover these Python files. The checks perform no Parser call, graph load,
materialization or timing/memory sampling. A profile's meaning or bytes
changing requires a reviewed new identifier/version, not a golden refresh.

### Small full-load workload qualification

The private [workload descriptions](../../tests/performance/decision_workload.py)
bind only `vault-small-96-v1` and the scenarios `full_load_cold_instance` and
`full_load_unchanged_repeat`. They include the frozen dataset, explicit caller
bindings for generator and semantic sources, native per-file tab detection,
both graph strict options set to false, source ordering and the complete
`load_directory` interval. They do not accept an arbitrary graph or worker-count
option, inspect the host or execute an operation.

Unchanged-repeat differs only by its scenario and priming fields: one untimed
priming load before all three future warmups. Every eventual sample still uses
a fresh graph and executor. Neither scenario claims cold operating-system
caches. The descriptions run no warmup/sample loop and report no duration.

Canonical compact sorted-key UTF-8 JSON produces separate workload, operation,
parser-option and semantic-contract hashes. Explicit source-digest syntax is
not verified provenance: complete harness, installed source/dependencies and
runtime admission still need separate reviewed bindings.

The independent [small-graph semantic oracle](../../tests/performance/decision_semantics.py)
derives expectations from the closed source grammar, without using Parser
output, generator helpers or production normalization/UUID helpers. It checks
96 physical pages, 95 aliases, 3,304 nodes and the complete 1,024-node chain,
including ordered registries/backlinks and the absence of extra members.

Observation uses bounded iterative traversal and flat immutable rows. The
selected compatibility meaning is `semantic_roundtrip_v1`, with stable
synthetic IDs, absent source IDs and direct-ID relations. Exact source ranges,
owned logical source paths and raw-page hashes supplement that projection.
Every declared page/node field is mapped or explicitly validated; filesystem
page timestamps are normalized only when the closed source has no timestamp
properties. Stable IDs here mean identical source, not a new guarantee after
rewriting or changing source positions.

The observer rejects malformed nested properties, wrong scalar/container
types, cycles, shared nodes and excess members before reusing structural
helpers. It does not recursively dump native models, change the recursion
limit or call the recursive canonical projection on the deep page. Controlled
shallow parity checks retain the existing projection contract.

[Workload metadata tests](../../tests/test_performance_decision_workload.py)
check independently assembled payload/hash vectors, strict closed inputs,
revalidation and fresh-import purity.
[Semantic tests](../../tests/test_performance_decision_semantics.py) materialize
the small fixture once and call the native graph loader twice per
fixture-using pytest invocation. Both fresh graphs independently match the
oracle; a separate comparison checks ordered same-source UUIDs. Reversible
in-memory mutations check alias targets, source/index membership, registry
identity/order, references/backlinks, malformed containers and the deepest
node's content/ranges. Mutation tests perform no additional graph loads.

These are ordinary bounded correctness tests, not independently launched
decision observations or additional official Logseq corpus qualification.
Larger fixtures remain unparsed and unmaterialized by these tests. No Parser,
public API, dependency, worker default or legacy diagnostic behavior changes.

### Injected small-load sampling kernel

The private [sampling kernel](../../tests/performance/decision_sampling.py)
accepts the existing small full-load description, explicit source-free metadata
and caller-supplied load, verification and clock callbacks. It selects no native
loader or clock and does not inspect files, CPUs, memory or the environment.
The caller is responsible for any later native binding and execution authority.

Preflight revalidates the immutable inputs, binds all dataset fields to the
frozen small fixture and derives workload/options/semantic identities from the
same description. Only current-thread metadata is supported; a supplied worker
count does not prove the actual pool size or native execution.

Cold-instance sequencing has three untimed warmups and 21 measured loads.
Unchanged-repeat adds exactly one untimed priming load before all warmups.
Every returned result is verified outside its load interval before acceptance.
Chronological integer durations retain all samples; median and nearest-rank p95
remain items 11 and 20 of a sorted copy. The six secondary phases are explicitly
uninstrumented and memory is unavailable. No parse-cost attribution is implied.

A failure stops that invocation without retry. Truthful completion counters and
stage-specific semantic/clock/infrastructure status remain, but all invalid
timing vectors and summaries are discarded. Abort exceptions propagate without
a fabricated receipt. Dropping the kernel's own result references does not prove
garbage collection, native executor cleanup or callback-owned object release.

[Sampling tests](../../tests/test_performance_decision_sampling.py) exercise the
real kernel with opaque fake results and scripted integer clocks only. They
check event order, late/co-occurring failures, strict metadata, reference
retention, lazy imports and bounded privacy sentinels. The receipt's
`perf_counter_ns` schema label in these tests is not evidence that a real clock
or Parser workload ran. A schema-valid receipt is still not runtime admission;
this module creates no attestation, comparison selection or positive verified
flag. It adds no native sampling campaign to default CI.

### Unmeasured native small-load binding

The private [native binding](../../tests/performance/decision_native_binding.py)
connects the closed 96-page workload to the existing graph loader. Explicit
context entry prepares one owned synthetic vault, checks its exact file types,
inventory and bytes, and builds the existing independent expectation once.
Import and construction perform no native loading or fixture preparation.
No arbitrary vault path, worker override, clock or sampling loop is accepted.

Each fresh-load callback calls the unchanged native loader with both strict
options false. Its enclosing future interval includes bounded ownership/state
checks and weak-reference bookkeeping as well as the complete native call;
it is not exclusive native-only time. Disk integrity and independent graph
verification happen after callback return, before accepting the result or
allowing another load. A dead or foreign result cannot pass identity checking.
Configured thread metadata comes from the graph module's imported cap, not a
later CPU estimate or observed concurrent-thread count.

The synchronous context rejects foreign-thread access and cleanup during an
active load or verification. It attempts owned cleanup once, requires positive
root absence and preserves an original abort alongside a private cleanup
failure. This does not guarantee hard termination, object destruction or
race-proof filesystem isolation. Caller references and exception tracebacks
can still retain objects and paths; raw working objects are not public evidence.

[Default binding tests](../../tests/test_performance_decision_native_binding.py)
use fake native resolution and semantic observations, with fixed synthetic
files for filesystem checks. They add no native graph calls to default CI;
the existing semantic fixture's two native calls remain unchanged.
The separate [two-load correctness file](../../tests/performance/decision_native_small_checks.py)
is outside default discovery and remains unexecuted. It needs explicit
authorization for one bounded, single-process invocation without parallel,
repeat or rerun plugins. Static checking and inert collection are not native
qualification, including qualification of native model weak-reference support.

The binding invokes no sampling kernel and creates no timing receipt,
attestation or positive verified flag. Actual runtime/source admission,
measurements and performance claims remain separate gates.

### What remains deferred

Fixture identity and small full-load correctness do not establish a
runtime-admitted dataset or workload. Larger-profile semantics, query/reload/
embed workloads, loaded source/dependency identity, actual runtime admission
and admitted native timing campaigns remain separate reviewed work. A generator namespace,
matching fingerprint or passing semantic test is not a positive admission
attestation.

The focused #87 pathological input and #113 deep-refresh case need their own
reviewed source, descriptor and semantic manifest before execution. A guessed
1,148-line string is not the #87 workload.

Deterministic tests in
[`tests/test_performance_comparison_contract.py`](../../tests/test_performance_comparison_contract.py)
use synthetic metadata and attestations to check contract behavior only.
They do not constitute real admitted observations, benchmark results or
additional Logseq conformance evidence. No native benchmark runner,
new collector, cache, executor-default change or CI timing gate is added.
Issue #111 remains open; actual measurements, budgets and separate cache/process
decisions require later reviewed plans and execution authority.
