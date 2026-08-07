---
type: DiagnosticContract
title: Structured diagnostics contract
description: Stable codes, payload schema, path-safety rules, rendering, and escalation policy for parser and graph diagnostics.
status: stable
classification: canonical
audience: contributors
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-07
verified: 2026-08-07
stale_after: 2027-02-03
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Structured diagnostics contract

The diagnostics API gives integrations stable, serializable findings without
turning log text into an accidental interface. Logging remains an output sink;
tests and consumers should assert diagnostic fields and codes.

## Payload

`Diagnostic` is an immutable dataclass with these fields:

| Field | Contract |
|---|---|
| `code` | Stable namespaced identifier |
| `severity` | `info`, `warning`, or `error` |
| `source_path` | Vault-relative POSIX path or `None`; never an absolute path |
| `line` | One-based source line or `None` |
| `message` | Concise human-readable explanation; wording is not a compatibility contract |
| `context` | Immutable string-to-string metadata with deterministic key order |

`Diagnostic.to_dict()` returns a deterministic JSON-compatible mapping.
Constructors reject absolute paths and parent traversal. Producers also remove
paths that cannot be proven relative to the selected vault.

## Stable codes

| Code | Severity | Meaning |
|---|---|---|
| `graph.broken_block_reference` | `error` | A block contains a `((uuid))` reference absent from the loaded graph |

Codes and field meanings are stable package-root API. New codes may be added in
minor releases. Removing a code or changing its meaning requires the same
major-version and migration process as other stable API breaks. Message wording
and context-field additions remain non-breaking.

## Python usage

```python
from logseq_matryca_parser import LogseqGraph, collect_graph_diagnostics

graph = LogseqGraph.load_directory("/path/to/graph")
for diagnostic in collect_graph_diagnostics(graph):
    print(diagnostic.to_dict())
```

Collection is observational: it does not mutate graph state or replace
`get_broken_references()` and `raise_if_broken_references()`.

## CLI rendering and escalation

- `matryca-parse scan GRAPH --broken-refs` renders the human Rich table.
- `matryca-parse scan GRAPH --diagnostics-json` writes only a JSON array to
  standard output, making it safe to pipe into automation.
- Both diagnostic flags opt into error escalation: exit status is `1` when an
  error diagnostic is present and `0` otherwise.
- A plain `scan` remains informational and does not escalate findings.

Future title-collision, parser-recovery, filesystem, and reload diagnostics must
reuse this payload and path policy. Each producer requires code/context tests
and both output forms where it is exposed through the CLI.
