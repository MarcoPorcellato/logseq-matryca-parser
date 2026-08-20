---
type: ArchitectureDecision
title: ADR-0001 Protocol adapter boundary
description: Decision to keep protocol integrations optional and deferred until explicit compatibility and safety gates are met.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-19
verified: 2026-08-19
stale_after: 2027-02-19
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# ADR-0001: Protocol adapter boundary

## Status

Accepted for the current repository architecture.

## Context

The parser already provides deterministic AST, graph, export, and bounded agent
access capabilities. Requests for MCP, A2A, or other agent protocol endpoints
could improve integration, but they would also introduce a schema, permission,
dependency, maintenance, and security surface that the base parser does not
currently need.

## Decision

The core package remains protocol-neutral. It will not add an MCP, A2A, or
other networked agent endpoint solely to advertise interoperability.

A future adapter may be proposed only when all of the following are available:

1. a concrete user workflow and named consumer;
2. a stable request/response schema and compatibility versioning plan;
3. a threat model covering authority, vault containment, prompt injection,
   secrets, and network exposure;
4. bounded permissions with explicit read/write separation and human approval
   for mutations;
5. compatibility vectors based on the project's parser corpus and semantic
   projection;
6. optional dependency packaging that preserves a lightweight base install;
7. conformance and integration tests that run without a private user vault.

## Consequences

- Existing LangChain and LlamaIndex integrations remain optional adapters.
- The current agent action contract remains the authority for local read/write
  behavior.
- Documentation may describe future protocol evaluation, but must not imply a
  server, certification, or compatibility that has not been implemented.
- A future proposal needs architecture, security, and release review before it
  can change this boundary.

## Alternatives considered

| Alternative | Decision |
|---|---|
| Add a protocol server to the base package now | Rejected: expands dependencies and authority without a qualified consumer or safety proof |
| Add an experimental optional adapter immediately | Deferred: an optional package still needs schema, threat model, and conformance evidence |
| Keep protocol-neutral adapters and document the admission gate | Accepted: supports integration planning without changing runtime authority |

## Review and rollback

Review this decision when a concrete adapter proposal meets every admission
criterion. The rollback path is a superseding ADR and a separately reviewed,
optional integration; no existing parser contract needs to change in place.
