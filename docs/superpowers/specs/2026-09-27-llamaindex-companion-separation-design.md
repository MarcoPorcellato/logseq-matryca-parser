---
type: DesignSpecification
title: Separate LlamaIndex adapter from parser distribution
description: Move the framework-native LlamaIndex bridge into a separately maintained distribution so the parser dependency graph no longer includes NLTK.
status: proposed
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-09-27
verified: 2026-09-27
stale_after: 2027-03-27
base_commit: 1c28aa6ceb01ada0ed8f4838ffb58903dc56f6f4
---

# Separate LlamaIndex adapter from parser distribution

## Purpose

Remove the LlamaIndex dependency chain, including vulnerable NLTK, from the
Logseq Matryca Parser distribution while retaining the existing LlamaIndex
export for users who deliberately install a separate integration package.
Keep parser, graph, serialization, LangChain export, and their behavior
independent of LlamaIndex.

This is dependency-boundary work, not an NLTK replacement or an NLTK security
fix. Consumers who install the companion integration remain exposed to the
upstream NLTK advisory until NLTK publishes and the companion qualifies a fixed
release.

## Verified starting point

- The approved live base is `main@1c28aa6ceb01ada0ed8f4838ffb58903dc56f6f4`.
- `llama-index-core` is declared in the Parser's `ai` and `all` extras and
  brings NLTK into the root `uv.lock`; the root uv constraint also names NLTK.
- `src/logseq_matryca_parser/__init__.py` imports `SynapseAdapter` eagerly.
  `synapse.py` imports both LangChain and LlamaIndex schemas at module import
  time, catches missing imports, and implements both adapters in one module.
- `SynapseAdapter` is an experimental package-root export. Its
  `to_llamaindex_nodes(nodes, *, page_title=None, page_source_id=None)` method
  returns framework-native nodes with metadata and source, parent, child,
  previous, and next relationships.
- The Parser has a scoped exception for `PYSEC-2026-3740` in CI and release
  audits. The upstream advisory currently affects NLTK versions `<=3.10.3` and
  lists no patched release.
- The primary checkout is intentionally not the work surface. The isolated
  design worktree is based on the live main commit above; preserve the primary
  checkout and its untracked research document.

## Decision

Create a companion Python distribution in a **new public GitHub repository**.
The candidate distribution and repository slug is
`logseq-matryca-parser-llamaindex`; verify GitHub and PyPI name availability
before creating or publishing anything. The Parser repository must not contain
the companion's manifest or lockfile, so its Dependabot graph can be free of
the LlamaIndex-to-NLTK chain.

The companion depends on a supported Parser version and `llama-index-core`.
It owns the LlamaIndex visitor and framework-native node construction. It
must preserve the current exported metadata and topology semantics. The new
repository will own its own dependency audit and any temporary advisory
exception; moving the integration does not resolve NLTK for users of that
integration.

## Parser repository scope

- Remove `llama-index-core` from the Parser's `ai` and `all` extras. Keep the
  `ai` extra name for LangChain export during this migration; `all` retains
  visualization and LangChain dependencies only.
- Remove the NLTK uv constraint after confirming no remaining Parser
  dependency requires it. Regenerate the root lock and verify NLTK and
  `llama-index-core` are absent from the complete root dependency graph.
- Keep `SynapseAdapter.to_llamaindex_nodes` with its current signature as a
  lazy compatibility shim. It imports the companion only when called. If the
  companion is absent, raise an actionable `ImportError` with its installation
  command. Do not return dictionaries or other objects in place of real
  LlamaIndex nodes.
- Keep package-root import, parsing, graph, serialization, LangChain export,
  and non-LlamaIndex CLI behavior functional without importing LlamaIndex or
  NLTK.
- Remove the NLTK-specific `pip-audit` ignore from CI and release workflows and
  retire the Parser's advisory exception and its test only after the root
  lock, exported requirements, and built package metadata prove the dependency
  is gone.
- Update the README, cookbook, example, API stability contract, conformance
  matrix, security exception record, maintained indexes, and release notes
  with the companion install path and migration instructions.

## Compatibility and rollout

The existing method remains available, but calling it now requires the
companion distribution. Installing the Parser's `[ai]` or `[all]` extra alone
will no longer install LlamaIndex. Document this behavior before release and
provide the companion installation command next to every affected recipe.

Ship this packaging change only in a release with explicit migration notes,
not as a silent patch. The companion version must declare and test a bounded
compatible Parser version range. The exact distribution name, repository
slug, and version range must be verified before publishing.

## Security and scope boundaries

- Success means the Parser distribution and its root lock no longer install or
  resolve the NLTK chain. It does not mean NLTK or the companion is globally
  fixed.
- Keep the NLTK advisory visible and handled in the companion repository until
  an upstream fixed release is available and qualified. Do not dismiss the
  Parser alert manually to simulate remediation.
- Do not replace NLTK with another NLP library; Parser source has no direct
  NLTK functionality to replace.
- Do not change AST, graph, parser, serialization, LangChain, or Logseq
  semantics. No adapter-wide refactor beyond the imports and bridge boundary
  needed for this migration.
- Creating the public companion repository, publishing either distribution,
  pushing branches, and opening PRs are separate external actions. This design
  authorizes none of them.

## Acceptance criteria

1. Fresh subprocess tests prove importing the Parser package and using the
   base parser do not import `llama_index` or `nltk`.
2. Parser base, `[ai]`, and `[all]` dependency graphs and wheel metadata contain
   neither `llama-index-core` nor `nltk`; the root lock and exported audit input
   agree.
3. The compatibility shim preserves its current signature and gives an
   actionable missing-companion error without loading the companion at Parser
   import time.
4. Companion tests use real LlamaIndex types and prove node type, deterministic
   IDs, metadata, ordering, and all current source/tree/sibling relationships.
5. Parser CI and release dependency audits pass without the NLTK waiver; every
   other advisory remains fail-closed.
6. Documentation clearly distinguishes the Parser's clean dependency graph
   from the companion's still-open NLTK advisory and describes migration from
   `[ai]`/`[all]` users.
7. Parser full quality, documentation, package-contract, and supply-chain
   gates pass on the exact candidate commit. Companion's own package and
   dependency gates pass before its publication is considered.

## Open external gates

- Verify candidate GitHub and PyPI names and the supported-version policy
  before repository creation or package release.
- Obtain explicit authorization before creating the public companion
  repository or publishing either package.
- Recheck the NLTK advisory and upstream release state immediately before
  deciding whether the companion needs a temporary exception.

## Next review stage

Maintainer review and approval of this design precede the implementation plan.
After approval, GPT-6 Sol `xhigh` will author the detailed implementation plan;
the maintainer will review that plan before implementation begins.
