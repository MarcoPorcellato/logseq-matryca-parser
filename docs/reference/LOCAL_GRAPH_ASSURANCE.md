---
type: ReferenceGuide
title: Local graph assurance
description: Safe operation and JSON report contract for the bounded local graph assurance command.
status: stable
classification: canonical
audience: integrators
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-18
verified: 2026-08-18
stale_after: 2027-02-18
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Local graph assurance

`matryca-parse assure` checks a Logseq vault locally with project-owned parser
invariants. It is designed for private, bounded validation rather than export,
telemetry, external comparison, or performance measurement.

```bash
uv run matryca-parse assure /absolute/path/to/vault
uv run matryca-parse assure /absolute/path/to/vault --max-files 5000 --timeout-seconds 20
uv run matryca-parse assure --self-test
```

The command prints JSON to standard output. Exit code `0` means the selected
checks passed; any finding, configured limit, worker failure, or timeout exits
nonzero. `--self-test` must be used without a vault path and exercises the same
child-worker path against a temporary synthetic vault.

## Privacy and containment contract

The command has no network destination and does not create a report file. Its
worker rejects encountered symlinks and accepts only regular Markdown files
under `pages/` and `journals/`. It applies independent limits for files, total
bytes, individual file bytes, and elapsed worker time.

The report intentionally excludes all source-derived strings: Markdown,
snippets, relative or absolute paths, page titles, block UUIDs, exception text,
and host names. It reports only schema version, status, configured limits,
aggregate observations, finding-code counts, and coarse Python/platform labels.

Do not treat this process-local socket guard as an operating-system sandbox.
Run it only on a vault you are authorized to inspect, and use normal operating
system controls when you require stronger process isolation.

## Report schema v1

```json
{
  "schema_version": 1,
  "status": "passed",
  "limits": {"max_files": 10000, "max_total_bytes": 134217728, "max_file_bytes": 8388608, "timeout_seconds": 30.0},
  "observed": {"markdown_files": 2, "total_bytes": 96, "parsed_pages": 2, "parsed_nodes": 2, "root_nodes": 2, "block_references": 1},
  "findings": [],
  "runtime": {"python": "3.12", "platform": "darwin"}
}
```

`status` is one of `passed`, `findings`, `limit_exceeded`, `error`, or
`timeout`. Every `findings` item has only a stable code and a positive count.
Consumers must reject reports with unknown fields at any schema level rather
than assume they remain content-free.

## Scope

The initial command checks parser tree relationships, duplicate source
identities, page-title collisions, and unresolved block references. It does
not claim complete graph reload equivalence, performance budgets, external
parser parity, or release qualification. See
[ADR-002](../decisions/ADR-002-local-graph-assurance-boundary.md) for the
threat model and expansion gate.
