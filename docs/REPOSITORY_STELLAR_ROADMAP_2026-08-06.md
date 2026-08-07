---
type: RepositoryAudit
title: Logseq Matryca Parser - Code audit and stellar roadmap
description: Verified audit, reproducible findings, and MKQ-4 roadmap aligned to Matryca Knowledge.
status: stable
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-07
verified: 2026-08-07
stale_after: 2026-11-04
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
source_commit: 8e90b44
supersedes: docs/REPOSITORY_IMPROVEMENT_STUDY_2026-07-28.md
superseded_by: null
---

# Logseq Matryca Parser — Code audit and roadmap to a “stellar” repository

> **Status:** study executed and verified on 2026-08-06
> **Analyzed checkout:** `main` @ `8e90b44`
> **Document nature:** decision record and technical backlog; no implementation, commit, push, PR, merge, or release is authorized from this document.
> **Relationship to previous study:** supersedes and fixes `REPOSITORY_IMPROVEMENT_STUDY_2026-07-28.md`, which was untracked during the previous audit.

## 1. Executive summary

The repository is already above average: local quality gate passes with **462 tests**, **3,233 statements** measured, and **91% coverage**, Ruff and Mypy are clean, **0 import cycles**, modern packaging, useful graph APIs, deterministic parsing, file-level atomic writer, and good optional-adapter separation.

The next step is not a rewrite or indiscriminate feature expansion. It is, in order:

1. fix two confirmed P0 defects on synthetic fixtures;
2. make vault security boundaries explicit and enforceable;
3. make mutable graph state a coherent snapshot for writer, watcher, and readers;
4. freeze parser semantics with versioned corpus and metamorphic tests;
5. make delivery, API, diagnostics, and documentation mechanically reliable;
6. measure scale before introducing additional indices, databases, or frameworks.

The key conclusion is that open backlog **#101–#111 is valid but incomplete**. It covers almost all strategic maturation, but this audit also confirms:

- **P0 — content loss on updates to nodes nested deeper than level 3**;
- **P0 — writing outside the vault through symlinked markdown files**;
- **P1 — `file://` URI resolution without vault confinement**;
- **P1 — stale backlinks after incremental page rename**.

The first defect needs a dedicated bug issue and a surgical fix before parser refactor. The two confinement defects should become explicit acceptance criteria in #106; the stale-backlink issue should become an explicit slice under #103 or a child issue.

## 2. Initial plan

The pre-exploration plan was:

1. collect live baseline, repository instructions, history, and indexed architecture;
2. delegate specialist audits to GPT-5.3 Codex Spark and GPT-5.6 Luna;
3. reconcile results and distinguish current defects, existing debt, and speculative ideas;
4. run a correction round on contradictory or unverified points;
5. place evidence, findings, priorities, roadmap, and limits into a versioned Markdown document;
6. validate the document with repository-prescribed gates.

### 2.1 Study acceptance criteria

- Recommendations must derive from live sources, tests, workflows, or reproducible probes.
- Historical facts must not be presented as current state.
- Each finding should include impact, confidence, minimum verification, and relation to #101–#111.
- Hub changes must be preceded by impact analysis.
- Deterministic parsing, UUID behavior, ordering, canonical pages, no-ghost-node guarantees, and `strict_refs` must remain unchanged.
- This study does not authorize commits, pushes, PRs, issues, or remote changes.

## 3. Delegation, collection, and plan adjustment

Five read-only tasks were run in separate worktrees, starting from current state and including the untracked July 28 document.

| Task | Model | Routing rationale | Useful outcome |
|---|---|---|---|
| Documentation and contributor experience | GPT-5.3 Codex Spark | Mostly mechanical work: links, counts, indexes, onboarding | Evidence collected; final report failed due to service output limit, so conclusions were rebuilt and locally re-verified |
| CI, packaging, and release engineering | GPT-5.3 Codex Spark | Workflows and manifests have deterministic checks | Confirmed mutating lint, unpinned actions, and non-immutable artifact lineage |
| Architecture and maintainability | GPT-5.6 Luna | Requires cross-module reasoning and blast-radius analysis | Confirmed two main hubs, need incremental slices, and stale-backlink risk |
| Correctness, security, and performance | GPT-5.6 Luna | High-risk area with probes and judgment required | Identified four anomalies later reproduced in primary checkout |
| Product, API, and ecosystem | GPT-5.6 Luna | Requires sequencing and positioning synthesis | Confirmed contract-first strategy and early rejection of premature plugin/database expansion |

### 3.1 Correction round

The first remote executions were interrupted during compaction. They were not accepted as complete outcomes. The second round:

- reduced scope;
- banned broad re-scans;
- required closure from already collected data;
- reduced reasoning where necessary;
- requested compact outputs and clear separation between facts and assumptions.

Four tasks produced final reports. The documentation task failed again due to output limit; partial data were cross-checked directly against `README.md`, `docs/README.md`, `CONTRIBUTING.md`, workflows, and the previous study.

### 3.2 Critical review of delegated findings

One early synthesis concluded that #101–#111 covered all required work. This was rejected after independent probes: deep soft-break loss is a reproducible current bug, and symlink boundary and `file://` behavior are current security behavior, not theoretical hardening concerns.

This is why the final roadmap starts with a **Wave 0 containment and correction** before previously opened strategic initiatives.

## 4. Evidence and live baseline

### 4.1 Git state

At audit start:

```text
* main...origin/main
?? .serena/
?? docs/REPOSITORY_IMPROVEMENT_STUDY_2026-07-28.md
```

Both paths already existed and were preserved. Local audit index updates automatically added content to `AGENTS.md` and `CLAUDE.md`; those generated additions were removed, restoring both files to no-diff state.

### 4.2 Quality gate

Command:

```bash
rtk make all
```

Result:

- Ruff: `All checks passed!`
- Mypy: `Success: no issues found in 34 source files`
- vendor-neutral documentation check: `OK`
- Pytest: **462 passed**
- coverage: **3,233 statements, 288 missing, 91% total**

`make all` is green, but it is not yet a purely verificative gate: `make lint` runs `ruff check . --fix`. This run produced no diff, but CI could auto-correct checkout in another run and mask a non-compliant submission. This confirms #101.

### 4.3 Audit code

The local index was updated to the current commit and reported:

```text
2,133 nodes | 4,040 relations | 57 clusters | 169 flows
cycleCount: 0
```

The analysis server initially used stale context cache; therefore stale results were not used as sufficient evidence. Critical findings were confirmed with live source, semantic checks, and runtime probes.

### 4.4 Protected hub blast radius

| Symbol | Risk | Observed impact | Operational consequence |
|---|---:|---|---|
| `StackMachineParser._refresh_node` | HIGH | 102 symbols, 4 flows | Changes only with corpus snapshots and parser-level tests |
| `StackMachineParser._replace_stack_tail_node` | HIGH | 102 symbols, 4 flows | P0 fix must be surgical and equivalence-tested |
| `LogseqGraph.load_directory` | CRITICAL | 47 direct callers, 6 flows | No opportunistic changes; keep API and determinism |
| `LogseqGraph.invalidate_and_reload_page` | LOW local | 3 direct callers, 2 flows | Small slice, but global index semantics must be verified against cold reload |
| `_expand_macros_and_embeds_impl` | LOW | 6 symbols, 2 flows | Seams already narrow; not a top performance hotspot |

## 5. Current architecture

```mermaid
flowchart TD
    V["Vault: pages/ and journals/"] --> D["Discovery and path policy"]
    D --> P["StackMachineParser"]
    P --> AST["Immutable LogseqPage and LogseqNode"]
    AST --> G["LogseqGraph"]
    G --> IDX["Canonical pages, UUID, aliases, backlinks"]
    IDX --> Q["Query, namespace, reference checks"]
    G --> W["Incremental reload and watcher"]
    G --> A["CLI, agent read/write"]
    G --> E["Export, RAG, and visualization"]
    W --> G
    A --> W
```

Dependency direction is generally good and cycle checks are clean. Primary risks are not cycles or the wrong framework; they are **temporal consistency** and propagation of immutable structures:

- the parser builds immutable nodes through a stack;
- the graph exposes multiple derived indexes from one page collection;
- writer and watcher can update files and indexes at different times;
- aliases and titles convert one map into canonical identities plus secondary projections.

The future design must make these four contracts explicit.

## 6. Confirmed findings

### P0.1 — Content loss in deeply nested nodes

**Status:** implementation published in
[draft PR #118](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/118),
stacked on #117; pending merge.

`StackMachineParser._replace_stack_tail_node` updates the node, parent, and grandparent, but does not propagate the new branch back to the root for depths above the third level. Soft-break text is recorded on local stack state, while the returned AST keeps the previous root.

Synthetic probe:

```text
DEEP_CONTENTS ['a', 'b', 'c', 'd', 'e']
DEEP_SOFT_BREAK_PRESENT False
```

Protected input:

```markdown
- a
  - b
    - c
      - d
        - e
          continuation-e
```

**Impact:** silent loss of content and metadata whenever any call to `_replace_stack_tail_node` updates a deep node. The issue is not limited to soft-breaks; the same helper handles properties, fence, query, and list finalization.

**Why tests miss this:** existing soft-break tests cover shallow depths and line coverage executes helper logic without checking the invariant that every stack update remains observable from root at arbitrary depth.

**Minimal slice:** replace hardcoded three-level propagation with iterative reconstruction from leaf to root, without changing line classification or parser semantics.

**Required tests:** depths 1, 2, 3, 4, 8, and 32; soft-break, property, code fence, property-list cases; `line_end`; parent/left pointers; UUID; serialization and re-parse; shallow vs deep nesting equivalence.

**Delivery evidence:** issue #113 now has the required iterative leaf-to-root
rebuild and depth/family regression matrix in PR #118. Keep the fixture as an
input to #104 and retain this fix as a prerequisite for #108 until merged.

### P0.2 — Writer may write outside vault via symlink

**Status:** implementation prepared in the fifth stacked tranche for #106.

Discovery accepts symlinked markdown under `pages/` or `journals/`. `parse_page_file` stores `path.resolve()`, i.e., the real target. `append_child_to_node` reads and rewrites that `source_path` without verifying it is inside `graph.graph_path`.

Probe (temp directories only):

```text
SYMLINK_SOURCE_OUTSIDE True
SYMLINK_OUTSIDE_MUTATED True
```

**Impact:** an untrusted vault can cause a local integration with repo permissions to modify an external Markdown file.

**Delivery evidence:** the fifth stacked tranche defines and tests fail-closed
real-path containment, pre-read and pre-replace validation, target identity,
mode/owner/group preservation, dry-run unified patches, configurable limits,
typed diagnostics, external symlink rejection, and confined `file://` reads.

**Required tests:** file symlink, directory symlink, symlink changes between parse and write, traversal path, rename race, dry-run without write, valid internal target.

**Recommended tracking:** update #106 with probe and acceptance criteria; do not duplicate issue unless maintainer decides.

### P1.1 — `file://` bypasses asset boundary

**Status:** current read/confinement defect, high confidence.

`LogseqPage.resolve_asset_path` returns an absolute path for `file://` URIs before applying `graph_root` containment checks. This contradicts current docs stating asset resolver is vault-confined.

Probe:

```text
FILE_URI_RESULT /private/etc/passwd
```

**Impact:** an untrusted document can convert an asset token into an arbitrary local path, and downstream adapters may ingest/read it.

**Minimal slice:** apply a single canonicalization and containment function across all branches, including `file://`, percent-decoding, Windows path forms, and asset fallbacks. Define whether in-vault `file://` is supported or always rejected.

**Recommended tracking:** either a dedicated security issue or explicit expansion of #106 from “write boundary” to “filesystem boundary.”

### P1.2 — Stale backlinks after incremental rename

**Status:** current bug, high confidence, adjacent to #103 but not explicitly stated in current criteria.

Full load reconstructs all backlinks. `invalidate_and_reload_page` removes only nodes for the modified page and adds outgoing backlinks from fresh page data; it does not recalculate keys for incoming links from unchanged pages when a target page title or alias changes.

Probe:

```text
RENAME_BACKLINKS 1 1 0
```

Interpretation: before rename there is a backlink; after `Target → Renamed`, the old key still returns a result and the new one returns none.

**Correct contract:** after each incremental reload, the observable snapshot must be semantically equivalent to a cold reload from the same filesystem state.

**Minimal slice:** add a delta signal for identity/alias changes; if triggered, rebuild all globally dependent indexes or add reverse-dependency indices. Prioritize correctness first, then measurement.

**Recommended tracking:** child issue of #103 or explicit expansion of it; also link #102 and #110.

### P1.3 — Title/alias collisions can hide a page

**Status:** implementation published in
[draft PR #120](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/120),
stacked on #119, for #102.

Pages are stored in a title-keyed dict, and aliases can remap canonical keys. Behavior is deterministic and the registry avoids many ghost nodes, but visibility loss is still primarily a logging concern.

**Delivery evidence:** the fourth stacked tranche preserves the current winner,
records stable structured diagnostics with both vault-relative paths and a
reason, adds a typed opt-in strict mode, and covers derived, frontmatter, and
alias collisions without ghost nodes.

### P1.4 — Writer, watcher, and readers do not share an atomic snapshot

**Status:** confirmed architectural risk; covered by #103.

Writer provides `mkstemp` + `os.replace`, which protects against partial file reads, but it does not serialize two concurrent read-modify-write cycles. Incremental reload updates multiple derived structures in multiple passes.

**Action:** introduce per-vault coordinator with mutation locks and publish immutable snapshots. Avoid a global process-wide lock.

### P1.5 — Mutating lint in CI

**Status:** implementation published on 2026-08-07 in
[draft PR #116](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/116);
tracked by #101.

PR #116 separates verification-only `lint` from opt-in `lint-fix`,
keeps `make all` non-mutating, adds a final CI checkout-integrity assertion,
and protects the target/workflow contract with focused tests. A repository-wide
`ruff format --check` gate was evaluated and deliberately not activated because
23 pre-existing files on `main` require a separate mechanical-formatting tranche.
The finding remains open until the implementation PR is merged and remote CI is
green.

### P1.6 — Release artifacts not built once

**Status:** confirmed; covered by #105.

Pre-flight, PyPI build, and GitHub release do not necessarily consume the same immutable wheel/sdist. Workflows use movable tags and the `nltk` VCS override is tag-based instead of commit-based.

**Action:** build once, checksum, publish attested artifacts, release exact bytes, and align tags, versions, and changelog entries.

### P2 — Strategic debt valid but not as urgent as current findings

- #104: compatibility corpus and metamorphic properties;
- #107: `py.typed`, API policy, and version source;
- #109: documentation lifecycle, link/snippet checks, and generated numbers;
- #110: structured diagnostics; stable payload, broken-reference producer, path
  policy, and JSON CLI are implemented in
  [draft PR #119](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/119),
  the third stacked tranche; the collision producer is prepared in the fourth
  tranche, while parser-recovery, filesystem, and reload producers remain;
- #111: 1k/10k page benchmarks and RSS/p95 budgets;
- #108: incremental parser phase extraction only after #104 and P0.1 fix.

## 7. Why 91% coverage does not mean 91% reliability

The suite is strong, but line coverage does not represent four key dimensions:

| Dimension | Missing example | Required technique |
|---|---|---|
| Structural depth | leaf-to-root update at arbitrary depth | tree-generation tests and metamorphic depth invariance |
| Temporal consistency | incremental reload equivalent to cold load | state-machine tests and snapshot oracle |
| Filesystem confinement | symlink, TOCTOU, `file://` | temporary fixture abuse cases and centralized path policy |
| Concurrency | two writers and watcher concurrently | deterministic barrier tests, no timing sleeps |

Target metric should not be “95% coverage” in abstract. It should be: **100% of critical invariants protected by semantic oracles**.

## 8. Repository and documentation — Matryca Knowledge profile

### 8.1 Normative baseline and provenance

This plan section adopts current parameters from
[`MarcoPorcellato/matryca-knowledge`](https://github.com/MarcoPorcellato/matryca-knowledge)
at revision `7a3ebd8` on 2026-08-06. Authoritative references are:

- [`ENGINEERING_PRINCIPLES.md`](https://github.com/MarcoPorcellato/matryca-knowledge/blob/7a3ebd8/docs/ENGINEERING_PRINCIPLES.md): determinism before automation, evidence, baseline, testing, rollback;
- [`OKF_SOURCE_GOVERNANCE.md`](https://github.com/MarcoPorcellato/matryca-knowledge/blob/7a3ebd8/docs/OKF_SOURCE_GOVERNANCE.md): stable markdown identity, canonical links, entry points, and ownership;
- [`FOUNDATION_GOVERNANCE_OKF_EXECUTION_PLAN.md`](https://github.com/MarcoPorcellato/matryca-knowledge/blob/7a3ebd8/docs/FOUNDATION_GOVERNANCE_OKF_EXECUTION_PLAN.md): separation of official OKF from Matryca quality, MKQ levels, and Gate G6 dedicated to the parser;
- [`SYNC_POLICY.md`](https://github.com/MarcoPorcellato/matryca-knowledge/blob/7a3ebd8/docs/SYNC_POLICY.md): trusted sources, reproducible projection, allowlist enforcement, and avoiding dirty sources.

The external Matryca Knowledge OKF baseline is Google OKF v0.2 at commit `3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`, blob
`a516d50128f5aa1f5746d1464661a39f7143e875`. This repository does **not** declare official OKF compliance: until the official layer is implemented and verified, the correct profile is `matryca_okf_inspired_quality`.

Source repository remains the authority for its own documents. Matryca Knowledge can maintain a revised projection only when it is reproducible and traceable to immutable repository path and commit hashes; generated Logseq views are not source of truth.

### 8.2 Current measured state after documentation adoption

The initial audit findings above were addressed in the documentation adoption
phase on 2026-08-06:

- `docs/index.md`, `docs/README.md`, `docs/log.md`, `docs/decisions/index.md`,
  and `docs/reference/index.md` now provide stable bundle surfaces;
- maintained entry points use lifecycle, classification, ownership, authority,
  compatibility freshness, and explicit supersession metadata;
- [`DOCUMENTATION_SYSTEM.md`](DOCUMENTATION_SYSTEM.md) is the canonical
  contributor and governance contract;
- active and historical documents are separated without bulk-normalizing the
  historical archive;
- repository documentation and maintainer-facing text use English;
- the private `matryca-knowledge/sources.toml` still has no parser
  `okf_entry_points`, so the external validator cannot yet admit or enforce this
  bundle. That registry change and projection refresh remain separate PRs.

### 8.3 Current strengths

- `docs/README.md` separates active, historical, and design docs.
- `CLEAN_CODE_ARCHITECTURE.md` documents hubs, rings, and anti-patterns.
- `logseq_ast_primer.md` captures difficult domain rules.
- Historical roadmaps expose evolution by wave.
- CONTRIBUTING, issue templates, and Good First Issues offer a real onboarding path.

### 8.4 Remaining issues

- The private source profile must declare parser entry points before the shared
  validator can audit the bundle.
- Source CI does not yet enforce maintained links, anchors, lifecycle,
  canonical roles, documented CLI commands, and Python snippets.
- Some release-era documents intentionally retain historical metrics; active
  guidance must avoid copying those values as current claims.
- Asset resolution documentation states a boundary that `file://` handling
  currently violates; this remains a product defect, not a documentation-only
  correction.

### 8.5 Metadata contract

Only maintained documents listed in the allowlist must have required metadata. Historical archives should not be rewritten in bulk. Transition contract already follows the latest Matryca Knowledge structure:

```yaml
type: ArchitectureGuide
title: Stable title
description: Short discovery-focused description
status: draft | stable | deprecated
classification: canonical | active | historical | generated
owner: logseq-matryca-parser
last_verified: YYYY-MM-DD
verified: YYYY-MM-DD
stale_after: YYYY-MM-DD
supersedes: null
superseded_by: null
```

`status` is reserved for lifecycle compatible with OKF v0.2. `classification` captures the Matryca role. `last_verified` remains compatible with existing validator, while `verified` and `stale_after` prepare explicit freshness.
Volatile metrics—tests, coverage, version, module count—must be generated by deterministic tooling or avoided in prose.

### 8.6 Target maintained bundle

| Path | Classification | Responsibility |
|---|---|---|
| `docs/index.md` | canonical | Machine-readable entrypoint and bundle map |
| `docs/README.md` | canonical | Human portal and navigation surface |
| `docs/log.md` | active | Verifiable documentation evolution history |
| `docs/decisions/index.md` | canonical | ADR register, status, and supersession |
| `docs/reference/index.md` | canonical | Provenance, external sources, and public contracts |
| `docs/quality/README.md` | active | Current backlog, gates, and quality roadmap |

Paths should remain stable; renames or splits require redirects or supersession links. Standard markdown links form the knowledge-graph edges. Local references and anchors should be validated offline. No public document should include secrets, absolute local paths, raw runtime dumps, or unsanitized logs.

### 8.7 MKQ maturity and Gate G6

| Level | Required evidence for parser |
|---|---|
| MKQ-0 | Source-anchored repository with immutable provenance |
| MKQ-1 | Stable entrypoint and bundle navigation |
| MKQ-2 | Metadata and freshness on maintained documents only |
| MKQ-3 | Verified links, anchors, lifecycle, owner, and coherent classifications |
| MKQ-4 | Deterministic CI verification from source repository |
| MKQ-5 | Federation, history, and semantic relations; next phase, not immediate gate |

Gate G6 is reached when Logseq Matryca Parser achieves **MKQ-4 without regressing Logseq behavior**. Documentation must also explicitly link to
[Matryca Knowledge](https://github.com/MarcoPorcellato/matryca-knowledge)
and
[Matryca Plumber](https://github.com/MarcoPorcellato/matryca-plumber),
without shifting source-of-truth authority outside the repository.

### 8.8 Documentation migration plan

1. Inventory and classify documents without bulk editing of historical content.
2. Stabilize `docs/index.md`, human portal, and decision/reference indices.
3. Apply metadata and ownership to an initial allowlist of maintained documents.
4. Validate links, anchors, lifecycle, canonical role, and freshness offline.
5. Add non-mutating, source-reproducible CI gate.
6. Declare entry points in Matryca Knowledge registry via a separate PR.
7. Project only clean immutable commits; verify Logseq-rendered views do not alter source semantics.

Steps 1-3 are complete at source level. Step 4 is partially covered by manual
review. Steps 5-7 remain the MKQ-4 completion path tracked by issue #109.

## 9. Product and API strategy

Recommended positioning:

> Logseq parser and graph should be local-first, deterministic, and model-neutral, with export and optional adapters; agent writes should be explicit, confined, and verifiable.

### 9.1 Public contracts to publish

Separate three compatibility dimensions:

1. **Python API:** imports, signatures, exceptions, typing, and deprecation policy;
2. **Logseq semantics:** AST, UUID, hierarchy, properties, references, and round-trip;
3. **CLI:** stdout/stderr, exit codes, JSON schema, and command stability.

Classify surfaces as `stable`, `experimental`, `internal`. AI adapters, visualization, and watcher remain optional dependencies; writer stays opt-in.

### 9.2 What not to build now

- No big-bang parser rewrite.
- No plugin registry before a typed adapter protocol is used by at least two external integrations.
- No database or search engine until #111 proves bottleneck justification.
- No desktop GUI until there is adoption signal for library and CLI usage.
- No “10k+ at 60 FPS” claims without reproducible benchmarks.
- No proprietary LLM orchestration in core: parser should stay model-neutral.
- No new permissive mode without structured diagnostics.

## 10. Proposed roadmap

### Wave 0 — Containment and correctness (before any parser refactor)

| Slice | Priority | Deliverable | Gate |
|---|---:|---|---|
| Arbitrary leaf-to-root propagation | P0 | Surgical fix + depth matrix tests | Existing fixture semantics preserved; deep soft-break retained |
| Writer confinement on symlink | P0 | Fail-closed policy + revalidation | No fixture can mutate external paths |
| Asset URI confinement | P1 | Single path policy | No resolver returns external paths |
| Backlink rename correctness | P1 | Delta identity rebuild or correct full rebuild | Incremental snapshot equals cold-load snapshot |

### Wave 1 — Trust baseline

- #101: non-mutating lint and format;
- #107: typing metadata and API stability table;
- #109: MKQ bundle, separate status/classification, freshness, generated metrics, link/anchor/snippet gates, immutable provenance;
- update #106 with the two filesystem abuse cases;
- update #103 with rename/backlink equivalence.

### Wave 2 — Safe vault semantics

- #110: structured diagnostics;
- #102: title/alias collisions with strict mode;
- #106: dry-run and patch preview;
- stable diagnostic codes for recovery, collisions, boundaries, and reload.

### Wave 3 — Safe automation

- #103: atomic snapshot for vault and serialized mutations;
- #104: versioned corpus, semantic projection, and metamorphic tests;
- watcher/writer concurrency tests with barrier and failure injection;
- incremental/cold-load equivalence as universal gate.

**Delivery update (2026-08-07):** [draft PR #117](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/117)
implements #107 with a single derived version source, wheel-level PEP 561
verification, a clean downstream Mypy probe, an explicit API stability table,
and root-export/signature regression tests. It also enables CI for PRs whose
base is another feature branch so the remaining roadmap can be delivered as an
independently reviewable stack.

### Wave 4 — Release confidence

- #105: build once / publish exact bytes;
- pin actions by SHA;
- pin VCS dependency commits;
- install typed wheel in clean environment, verify `RECORD` and checksum;
- align changelog/tag/version and artifact.

### Wave 5 — Qualified scale

- #111: offline generators at 1k and 10k pages;
- load, single-page reload, search, backlink, RAG export, RSS, and p95;
- budgets recorded for Python 3.12 and 3.13;
- only after measurement, optional secondary indexes.

### Wave 6 — Architectural evolution

- #108: extract classifier, lexical state, reducer, and enrichment one slice at a time;
- no user-visible change without compatibility decision;
- each slice must pass corpus, metamorphic suite, benchmarks, and impact review.

## 11. Agent-ready backlog

### [Issue #113](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/113) — `bug(parser): propagate immutable node refreshes through arbitrary depth`

**Scope:** only `_replace_stack_tail_node`, parser tests, and changelog if needed.
**Out of scope:** parser rewrite, new events, package split.
**Definition of Done:** green depth matrix; preserved UUID/order/line-range invariants; semantic round-trip; `make all`; zero cycles; documented impact review.

### Extension #106 — `security(writer): reject external symlink targets and unify filesystem confinement`

**Scope:** discovery/write boundary, `file://`, centralized containment, dry-run mode.
**Definition of Done:** no external path is read or written by vault-bound flows; POSIX and normalized Windows cases; typed errors and diagnostic codes.

### Extension #103 — `graph: make incremental identity changes cold-load equivalent`

**Scope:** title, alias, backlink, lower-title map, and derived registries.
**Definition of Done:** for create/edit/rename/delete, observable incremental snapshot is identical to full reload.

### Existing issue order

```text
New parser P0 bug
  ├─> #104 compatibility corpus
  └─> #108 parser phase extraction

#106 filesystem boundary
  └─> #110 structured diagnostics

#101 + #107 + #109
  └─> #105 immutable release

#102 + #103 + #110
  └─> #104 operational/semantic oracles
      └─> #111 benchmarks
          └─> #108 refactor slices
```

## 12. Success metrics

### 30 days

- 0 known open P0 issues without owner and repro path;
- non-mutating CI and dirty-tree check;
- filesystem boundary tested for symlink and `file://`;
- maintained documentation at MKQ-2 with separated status/classification and no diverging counts;
- #101–#111 tagged by wave and dependency.

### 60 days

- incremental reload semantically equivalent to cold load;
- stable JSON diagnostics for collisions, references, and filesystem;
- versioned Logseq corpus with provenance;
- typed wheel and published API stability table;
- release built once.
- documentation bundle at MKQ-3 with verified links, anchors, lifecycle, and canonical role.

### 90 days

- 1k/10k benchmarks published with RSS and p95;
- at least two external integrations validated against API contract;
- zero invariant regressions on corpus and metamorphic suites;
- first parser extraction slice completed without semantic drift.
- Gate G6: MKQ-4 in CI without Logseq behavior regressions.

## 13. Reproduction and verification commands

Baseline:

```bash
rtk git status --short --branch
rtk make all
rtk make vendor-name-check
rtk uv run coverage report
rtk git diff --check
```

Audit code:

```text
index status at current commit
query/context across parser, graph, writer, watcher
impact upstream on protected symbols
check(cycles) => cycleCount: 0
```

The four runtime probes were executed in temporary directories only, not live vaults. Output:

```text
DEEP_CONTENTS ['a', 'b', 'c', 'd', 'e']
DEEP_SOFT_BREAK_PRESENT False
RENAME_BACKLINKS 1 1 0
SYMLINK_SOURCE_OUTSIDE True
SYMLINK_OUTSIDE_MUTATED True
FILE_URI_RESULT /private/etc/passwd
```

## 14. Limits and non-authoritative claims

- No benchmark was run against a real or 10k-page vault.
- No public release was qualified and no clean wheel installation was verified.
- The follow-up phase opened PR #112, created issue #113, updated impacted issues, and closed only completed/duplicate entries in the reconciliation log. Milestones, branch protection, and remote workflows were not changed.
- The study does not prove complete compatibility with all Logseq versions.
- The symlink probe demonstrates macOS/POSIX behavior; the policy must include Windows matrix coverage.
- No recommendation authorizes hub refactors without fresh impact analysis at implementation time.

## 15. Final decision

The repository does not need “more things”; it needs to make data loss impossible without alerting, make filesystem escape impossible, and make every public promise measurable.

Recommended trajectory:

```text
fix P0 issues
→ confine vault filesystem operations
→ make snapshots consistent
→ freeze semantics
→ make delivery auditable
→ measure scale
→ refactor incrementally
```

If executed in this order, Logseq Matryca Parser can become a credible reference implementation: not by feature volume, but by deterministic contracts, local security, reproducible regressions, and quality evidence an integrator can independently verify.
