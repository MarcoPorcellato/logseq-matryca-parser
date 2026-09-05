---
type: ArchitectureDecision
title: ADR-0004 Parser and Plumber boundary
description: Decision that Parser remains a deterministic OG parsing library while Plumber owns the cross-product Logseq gateway.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-09-05
verified: 2026-09-05
stale_after: 2027-03-04
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# ADR-0004: Parser and Plumber boundary

## Status

Accepted.

## Context

Logseq Matryca Parser already provides deterministic parsing of Logseq OG
Markdown into a typed AST, an in-memory graph, and parser-native
serializations. Cross-product integration needs one gateway that can select a
source, own host adapters and session lifecycle, and publish stable contracts
to product consumers without making those consumers depend on Parser internals.

## Decision

The supported OG data flow is:

```text
Logseq OG -> Parser -> Plumber -> Trama/Brain
```

Parser owns deterministic OG parsing, typed AST construction, its in-memory
graph, and parser-native serialization. It accepts caller-provided local
Markdown inputs, but does not choose a cross-product source, operate a Logseq
host adapter, own sessions, or define public `plumber.*` contracts.

Plumber owns source selection, Logseq host adapters, session lifecycle, and
versioned public contracts for downstream consumers. The data flow above is not
a Python dependency direction. The Parser runtime must not import Plumber, Trama, or Brain. Plumber may use Parser internally for an OG source.

Trama and Brain consume Plumber contracts. They must not import or know Parser,
and must not access Logseq OG files or a Logseq DB through a parallel gateway.

LENS remains compatible in this slice. Its current API, CLI command, optional
dependency, and behavior are unchanged. A later, separately reviewed migration
will move user-facing graph-intelligence visualization to Trama and may begin a
compatible LENS deprecation. This decision adds no warning, removal, command,
or API change.

Parser remains protocol-neutral under
[ADR-0001](ADR-0001-PROTOCOL_ADAPTER_BOUNDARY.md). This decision adds no MCP
server, network endpoint, GUI, release, or compatibility claim.

## Consequences

- Parser remains independently useful to developer consumers that need only
  deterministic Markdown parsing, an in-memory graph, CLI workflows, or
  parser-native exports.
- Plumber is the only cross-product boundary between Logseq sources and Trama
  or Brain.
- Existing Parser public APIs and LENS compatibility promises remain unchanged.
- Any future UI migration, host adapter, protocol, mutation, or release needs
  its own accepted design and verification evidence.

## Verification and rollback

`tests/test_plumber_boundary_docs.py` keeps this decision and the maintained
architecture guides explicit. `tests/test_layer_boundary.py` rejects Parser
runtime imports of Plumber, Trama, and Brain. Rollback requires a superseding
ADR and a separately reviewed compatibility plan; it does not authorize an
implicit import or product-surface change.
