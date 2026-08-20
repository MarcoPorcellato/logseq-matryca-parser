---
type: ConformanceSupportMatrix
title: Support and compatibility matrix
description: Supported runtimes, stable contracts, semantic boundaries, optional integrations, and deprecation rules.
status: stable
classification: active
audience: integrators
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

# Support and compatibility matrix

This matrix makes the project's support boundary explicit. It does not claim
conformance to an external Logseq, AAIF, MCP, A2A, or OKF specification unless
separate evidence says so.

## Runtime and distribution support

| Surface | Support level | Evidence and change rule |
|---|---|---|
| Python 3.12 and 3.13 | Supported | Declared by project classifiers and exercised by the CI matrix |
| Python below 3.12 | Unsupported | Outside `requires-python` and the project test matrix |
| Base parser and graph dependencies | Supported | Installed by the base distribution; keep the core package lightweight |
| Optional `ai`, `viz`, and `watch` extras | Supported as optional integrations | Must remain lazy and must not become an implicit base dependency |
| Wheel typing metadata | Supported | `py.typed` and downstream wheel qualification are covered by package-contract checks |

The current released version is identified by the package version source and
release notes. Security support is limited to the latest release as defined in
[`SECURITY.md`](../../SECURITY.md).

## Public interface tiers

| Contract | Level | Consumer expectation |
|---|---|---|
| Package-root symbols listed in [API stability](API_STABILITY.md) | Stable | Breaking changes require a major version, migration guidance, and a changelog entry |
| Documented parser, graph, diagnostics, writer-preview, Markdown, and path contracts | Stable or explicitly scoped | Preserve documented deterministic behavior and safety boundaries |
| `matryca-parse` documented commands | Maintained CLI contract | Document user-visible changes and provide migration guidance for incompatible behavior |
| SYNAPSE, LENS, exporter, agent helper, and lower-level helper surfaces | Experimental unless promoted | Consumers must tolerate minor-version changes and follow release notes |
| Non-exported modules and undocumented internals | Internal | No compatibility guarantee |

## Semantic guarantees and limits

| Area | Current contract | Deliberate limit |
|---|---|---|
| Logseq Markdown parsing | Deterministic AST, hierarchy, UUID handling, properties, references, tasks, timestamps, assets, and documented round trips | Not a claim of complete upstream Logseq implementation or formal upstream conformance |
| Graph identity | Canonical pages, aliases, backlinks, deterministic ordering, and structured diagnostics | Consumers must use documented APIs rather than internal registries |
| Filesystem actions | Vault containment, dry run, atomic replacement, path checks, and limits | No authority outside configured vault boundaries |
| Agent actions | Bounded reads and opt-in writes with caller authorization | No autonomous publication, privilege expansion, or trust in vault instructions |
| Serialization | Documented Logseq, Markdown, JSON, and Obsidian-compatible outputs | Output remains subject to the explicitly documented serializer semantics |

## Optional integration matrix

| Integration | Status | Dependency | Compatibility boundary |
|---|---|---|---|
| LangChain documents | Optional experimental adapter | `langchain-core` | Preserve lineage metadata and lazy import behavior |
| LlamaIndex nodes | Optional experimental adapter | `llama-index-core` | Preserve relationships and lazy import behavior |
| Visualization | Optional experimental adapter | `networkx`, `pyvis` | Do not make visualization a parser requirement |
| File watching | Optional experimental adapter | `watchdog` | Event handling must preserve graph identity and deterministic reload rules |
| MCP or A2A | No runtime implementation | None | See the protocol adapter decision before proposing one |

## Deprecation and change management

Stable interfaces remain available for at least one minor release after a
documented deprecation, unless a security or data-integrity concern requires a
faster change. Every compatible or breaking change must update the relevant
contract, tests, and [`CHANGELOG.md`](../../CHANGELOG.md).

## Verification

Use the exact checkout's deterministic evidence:

```bash
uv sync --all-extras
make all
```

For distribution claims, use the package-contract workflow or its documented
local equivalent. For remote CI, release, and security-feature claims, collect
a fresh GitHub receipt rather than relying on this source document alone.
