---
type: ReferenceGuide
title: Runtime evidence
description: Test-only local runtime evidence protocol and source-free receipt contract.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-20
verified: 2026-08-20
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
