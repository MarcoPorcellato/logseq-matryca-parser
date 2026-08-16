---
type: ExecutionPlan
title: lsdoc reference study and parser assurance plan
description: License-safe comparative study and dependency-ordered plan for stronger semantic, complexity, and source-location guarantees.
status: draft
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-16
verified: 2026-08-16
stale_after: 2026-11-14
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
parent_plan: docs/REPOSITORY_STELLAR_ROADMAP_2026-08-06.md
source_commit: e2a3f9a8d190fd115028d0ad344c31fded0357d9
reference_commit: c79cb059da5b4360ebde2e5fd953fa1f43ddabc3
---

# lsdoc reference study and parser assurance plan

This document is the canonical subordinate execution contract for the parser
assurance improvements selected from a comparative study of
[`martinkoutecky/lsdoc`](https://github.com/martinkoutecky/lsdoc). The
[repository stellar roadmap](REPOSITORY_STELLAR_ROADMAP_2026-08-06.md) remains
the repository-wide top-level SSOT; this document elaborates only its
#104 -> #111 -> #108 delivery path.
Conversation history and the external repository are research inputs, not
competing specifications for this project.

## 1. Outcome

Logseq Matryca Parser should gain stronger, reproducible assurance that:

1. parser changes preserve the project-owned semantic contract;
2. pathological inputs terminate within explicit work and time budgets;
3. compatibility evidence is provenance-safe and independently reproducible;
4. optional source locations can support diagnostics and bounded editing without
   changing the existing AST by accident;
5. future parser phase extraction proceeds behind those gates rather than ahead
   of them.

Success is not “become a Python port of lsdoc.” Success is to adopt useful
verification principles independently while preserving this project's Apache-2.0
license, broader graph/writer/AI product scope, stable Python API, and Logseq
Markdown source-of-truth model.

## 2. Authoritative anchors

| Item | Verified state | Evidence |
|---|---|---|
| Source repository | `MarcoPorcellato/logseq-matryca-parser` | `origin/main` fetched 2026-08-16 |
| Source base | `e2a3f9a8d190fd115028d0ad344c31fded0357d9` | clean `agent/parser-assurance-m1` checkout matching `origin/main` on 2026-08-16 and [GitHub commit](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/e2a3f9a8d190fd115028d0ad344c31fded0357d9) |
| Source license | Apache License 2.0 | [`LICENSE`](../LICENSE) |
| Reference repository | `martinkoutecky/lsdoc` release `v0.5.5` | [reference commit `c79cb059`](https://github.com/martinkoutecky/lsdoc/commit/c79cb059da5b4360ebde2e5fd953fa1f43ddabc3) |
| Reference license | `AGPL-3.0-only` | [`Cargo.toml`](https://github.com/martinkoutecky/lsdoc/blob/c79cb059da5b4360ebde2e5fd953fa1f43ddabc3/Cargo.toml) and [`LICENSE`](https://github.com/martinkoutecky/lsdoc/blob/c79cb059da5b4360ebde2e5fd953fa1f43ddabc3/LICENSE) |
| Parent roadmap | current repository-wide quality SSOT | [stellar roadmap](REPOSITORY_STELLAR_ROADMAP_2026-08-06.md) |
| M0 publication | merged as [PR #159](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/159) | source head `a6056413`, squash merge `30946446`, terminal validation recorded in the PR |
| Existing delivery anchors | #87, #103, #104, #108, #111 are open; #106 and #113 are closed | live GitHub issue reads on 2026-08-16 |
| Local implementation checkpoint | `8806205c35b104ed65d00a273acc9eeca572ae38` | clean local commit on `agent/parser-assurance-m1`; exact-head tests passed, but independent oracle review rejected publication |
| Current milestone | M1-B corrective assurance hardening prepared; goal paused | [restart handoff](internal/M1A_CORRECTIVE_HARDENING_RESTART_HANDOFF_2026-08-16.md); no push or PR |

Drift-prone anchors must be re-verified before issue edits, implementation,
publication, or qualification.

### 2.1 M1 independent-review reconciliation

An independent review on 2026-08-16 found the M1 direction sound but the
initial review package incomplete. The review was treated as advisory input and
rechecked against the source tree, [#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104),
its audit-reconciliation comment, and the parent roadmap before acceptance.

The live #104 comment expands the issue to include the depth matrix from closed
#113, incremental-versus-cold-load snapshots owned by open #103, and filesystem
abuse cases linked to closed #106. M1 therefore delivers **#104-A**, the
project-owned projection and compatibility-corpus foundation. It does not claim
to close #104. The remaining generated-malformed, graph snapshot, and broader
filesystem-assurance work stays dependency-ordered under M3, #103, and the
existing security contracts.

The review established these M1-A decisions:

1. Use one private, test-owned projector with two versioned profiles; do not add
   a root-package export or a new public API.
2. `exact_parse_v1` captures deterministic `StackMachineParser.parse()` output.
   It includes page title, namespace, configured tab size, declared timestamps,
   page properties/order/references, and every node's content, clean text,
   properties/order, references, task data, UUID/source UUID/synthetic marker,
   hierarchy, parent/left relations, path, outline path, indentation, line
   ranges, declared timestamps, and ordered children. It excludes filesystem
   context. The manifest stores the source SHA-256, while the test directly
   proves `page.raw_content == source` instead of duplicating source text in
   JSON.
3. `semantic_roundtrip_v1` compares parse -> serialize -> parse semantics. It
   includes title, namespace, normalized properties and their declared order,
   outline order, meaningful content/clean text, references, tasks, declared
   timestamps, source UUIDs, and structural parent/left locators. It excludes
   raw source text, absolute paths, graph root, filesystem-derived timestamps,
   byte formatting, and universal line-number equality. Direct synthetic UUID
   equality is enforced only when the fixture identity policy requires it.
4. Identity policy is an object, not an ambiguous label: `synthetic_uuid` is
   `stable` or `recomputed`; `source_uuid` is `preserve` or `absent`; and
   `relations` is `direct_ids` or `outline_paths`. All fixtures separately prove
   UUID uniqueness, same-input determinism, and valid ordered parent/left links.
5. File-entrypoint behavior uses bounded assertions rather than a third snapshot
   profile. Paths are compared through normalized or relative relationships,
   never frozen host-specific absolute values.
6. The manifest records top-level corpus and snapshot schema versions. Every
   entry also records `fixture_schema_version`, `snapshot_schema_version`,
   fixture ID, source path and SHA-256, provenance, license, parse
   entrypoint/configuration, enabled profiles, expected outcome, protected
   behaviors, identity policy, expected diagnostic codes, and notes.
7. The review surface for M1-A includes the parent roadmap, clean architecture,
   public exports and API-contract test, path helpers and tests, package/quality
   gates, and repository license/notice in addition to parser and serializer
   sources. Existing focused tests remain authoritative; corpus tests reuse
   their behaviors and replace the private deep-refresh semantic tuple rather
   than creating a third semantic definition.

### 2.2 M1-B corrective review reconciliation

An independent patch review of local commit `8806205c35b104ed65d00a273acc9eeca572ae38`
on 2026-08-16 found the architecture acceptable but the assurance oracle not
yet safe to publish. Primary-agent runtime probes reproduced both P1 findings:
the semantic projector removed a real content wikilink for `[[Foo]]` combined
with `tags:: Foo`, and it projected `[[Project Authored]], [[Fixture]]` as one
malformed token. Manifest probes also proved that non-empty unverified
diagnostic codes and Boolean values in integer fields were accepted.

M1-B is a corrective sub-milestone of M1, not a new product feature. It must:

1. represent `tags`, `page-tags`, `alias`, and `aliases` as ordered canonical
   token sequences, splitting commas only outside `[[...]]` references;
2. derive property-origin wikilink occurrences independently and subtract only
   their multiplicity from aggregate node wikilinks, preserving content links
   with the same value;
3. preserve raw-byte fixture SHA-256 claims while forcing LF checkout bytes for
   `tests/fixtures/compat/**` through `.gitattributes`;
4. reject every non-empty `expected_diagnostics` list while M1 accepts only
   valid fixtures and has no diagnostic comparison runner;
5. reject Boolean schema versions and Boolean `tab_size` values with exact
   integer-type checks;
6. include `scripts/update_compat_snapshots.py` in the maintained mypy command
   and protect that inclusion with a quality-gate contract test; and
7. preserve commit `8806205` as historical evidence, deliver corrections in a
   new local commit, qualify that exact implementation SHA, then use a separate
   documentation-evidence commit to record it before any push.

The P1/P2 labels describe assurance-contract risk, not parser runtime behavior:
M1-B remains test, fixture, tooling, Git policy, and documentation work. It must
not change `src/`, package exports, runtime dependencies, or close #104.

## 3. Status vocabulary

- **Verified:** directly supported by source, a terminal command, or live GitHub
  state at the stated revision and date.
- **Reference claim:** stated by the reference project but not reproduced in
  this study.
- **Planned:** dependency-ordered work with explicit exit evidence.
- **In delivery:** a saved branch or pull request exists, but its complete exit
  evidence is not yet terminal.
- **Blocked:** a named legal, technical, or human dependency prevents that path.
- **Deferred:** intentionally excluded until demand and prerequisites justify it.

## 4. What was studied

The study reviewed the reference repository's public API, parser organization,
source mapping, semantic projection, reference extraction, differential harness,
complexity instrumentation, performance tests, graph-checking tool, decision
records, divergence records, release history, and backlog. It also compared
those surfaces with the current Python models, stack-machine parser, graph,
diagnostics, security contracts, round-trip harness, tests, and live strategic
issues in this repository.

The reference project states that it is intended as the parsing source of truth
for Tine. That relationship is relevant because it demonstrates a parser being
treated as an independently testable integration contract rather than as an
incidental utility inside an application.

### 4.1 Verified reference facts

- The crate is Rust, version `0.5.5`, and `AGPL-3.0-only`.
- Its source exposes separate AST, reference, inline, rendering, and
  source-oriented outline surfaces.
- The repository contains a differential harness that invokes `mldoc`,
  canonicalizes selected output, and fails on differences.
- It contains dedicated adversarial performance tests and deterministic
  parser-work instrumentation separate from semantic comparison.
- It carries source spans and source-range APIs, including explicit behavior for
  UTF-8 boundaries and parser-ownership failures.
- It keeps detailed decision, divergence, parity-audit, and complexity records.
- It provides a local graph comparison tool with process limits, file limits,
  timeouts, local reports, and an explicit privacy posture.

### 4.2 Reference claims not reproduced here

The reference README reports zero differences over a 1,188-input gate,
panic-free fuzzing over more than 160,000 inputs, real-graph parity, and bounded
complexity. This study confirmed that supporting harnesses and tests exist, but
did not install dependencies, execute untrusted reference code, access private
graphs, or independently reproduce those measurements. They remain reference
claims, not evidence about Logseq Matryca Parser.

### 4.3 Current strengths that must not be lost

Logseq Matryca Parser already exceeds the reference parser's product scope in
several areas: vault discovery, canonical pages and aliases, backlinks, safe
writer operations, structured diagnostics, CLI workflows, visualization,
Obsidian export, and AI/RAG adapters. It also already has immutable Pydantic
models, stable package exports, arbitrary-depth refresh regression coverage,
vault confinement, deterministic title-collision handling, and release
provenance.

The selected work therefore strengthens parser assurance. It does not replace
the graph, writer, diagnostics, export, or agent layers.

## 5. Comparative findings

| Assurance area | Current project | Useful reference lesson | Decision |
|---|---|---|---|
| Semantic regression | strong unit suite and 19-case round-trip script | compare a normalized behavior contract, not incidental internals | expand #104 first |
| Oracle | historical mldoc research, no executable maintained differential gate | a separate oracle catches shared blind spots | build only after license/process review |
| Fixture provenance | proposed under #104 | every fixture needs origin, permission, invariant, and expected result | adopt immediately |
| Malformed input | focused tests exist | termination and classified outcomes deserve their own gate | add original generators and subprocess timeouts |
| Complexity | pathological issue #87 and future benchmarks #111 | semantic correctness cannot detect repeated scans | add deterministic work-growth evidence before broad optimization |
| Timing | no versioned parser budget yet | timing is necessary but noisy | keep targeted timing plus deterministic work counters |
| Source locations | line ranges exist on nodes | exact ranges can power diagnostics and editing | RFC first; do not change stable AST yet |
| API separation | parser, graph, diagnostics, writer, and exporters are already separated | expose only consumer-relevant projections | retain Python-native boundaries |
| Failure posture | typed errors and diagnostics exist | parser ownership gaps should fail closed in strict research gates | add research-only strict gate before public behavior change |
| Evolution evidence | stellar roadmap and issue ledger exist | divergence and decision ledgers prevent rediscovery | extend existing issue/ADR system, not a parallel history |
| Real-vault validation | no maintained privacy-safe parity command | user-owned graphs reveal reachable edge cases | plan opt-in local tool after M2 |
| Org/render parity | outside current product contract | reference proves these are large independent products | defer until measured user demand |

## 6. Scope

- Extend #104 with an original, versioned semantic projection and fixture
  manifest.
- Define an optional differential research harness for overlapping Logseq
  semantics, subject to the license gate in M2.
- Add original property-based and adversarial generators for termination,
  hierarchy, identity, references, and round-trip invariants.
- Define deterministic parser-work growth evidence and integrate the #87 seed
  into #111 without replacing timing and memory benchmarks.
- Evaluate a Python-native source-location contract through an RFC and
  prototype before any API promotion.
- Feed accepted gates into #108 parser phase extraction.
- Preserve an honest decision and divergence ledger with negative findings.

## 7. Non-goals

- No Rust rewrite and no Python port of lsdoc.
- No runtime, build, package, or CI dependency on the `lsdoc` crate.
- No copying or adaptation of lsdoc source, control flow, AST schema, tests,
  corpus, expected outputs, documentation wording, or generated reports.
- No claim of full mldoc, renderer, Org, or Logseq-version parity.
- No public source-span promise before an accepted RFC and compatibility tests.
- No optimization that changes semantics merely to improve a benchmark.
- No private vault content in commits, CI artifacts, issue bodies, or reports.

## 8. License and clean-room boundary

This section is a conservative engineering policy, not legal advice.

The reference is AGPL-3.0-only while this project is Apache-2.0. The Apache
Software Foundation describes Apache-2.0 as GPLv3-compatible in the direction
where Apache-licensed material is included in a GPLv3-governed work, and warns
that reverse incorporation does not preserve an Apache-only result under its
interpretation. AGPL applicability and derivative-work questions depend on the
facts and jurisdiction; this plan therefore treats incorporation as prohibited
unless qualified review or upstream permission establishes an acceptable path.
GNU's AGPL additionally requires corresponding source availability for users
interacting remotely with a modified covered program. Copyright does not
protect ideas, systems, or methods as such, but it does protect their particular
expression. See the
[GNU AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html),
[Apache compatibility explanation](https://www.apache.org/licenses/GPL-compatibility),
and [U.S. Copyright Office overview](https://www.copyright.gov/help/faq/faq-protect.html).

### 8.1 Mandatory rules

| Material or action | Policy |
|---|---|
| General testing principle | may be independently designed from project requirements and public standards |
| Source code or distinctive control flow | never copy or translate from lsdoc into this repository |
| AST fields, nesting, serialization, or public API shape | design from Logseq Matryca Parser consumers; do not mirror lsdoc |
| Test inputs, corpora, expected outputs, fuzz seeds | create original fixtures or use sources with independently verified compatible provenance |
| Documentation text, tables, diagrams, and decision prose | write independently; do not paraphrase distinctive expression |
| Unmodified external oracle process | allowed only after M2 records license review, process isolation, dependency provenance, and publication policy |
| Future code reuse request | stop; obtain maintainer approval plus qualified legal review or explicit upstream relicensing/permission |

Every implementation PR under this plan must include a provenance statement:

> This change was implemented independently from Logseq Matryca Parser
> requirements and project-owned fixtures. It does not copy or adapt lsdoc code,
> tests, corpora, schemas, or documentation.

## 9. Disclosure decision

**Decision: disclose the reference publicly, narrowly, and precisely.**

The reference should appear in this study and in the provenance index, with its
exact revision and AGPL license. It should not become a marketing claim in the
root README, and implementation PRs should link this policy only when relevant.

Hiding the research source would not remove license obligations if material had
been copied, and it would weaken provenance for future maintainers. Conversely,
calling the project a direct inspiration without explaining the boundary could
create a false impression of derivation. The preferred wording is:

> `lsdoc` was reviewed as public comparative prior art for parser assurance.
> Logseq Matryca Parser does not include or adapt its AGPL-licensed code, tests,
> corpora, schemas, or documentation.

## 10. Evidence envelope

The future evidence levels are:

- **E0 — source inspection:** proves that a mechanism or test exists, not that
  its claims pass.
- **E1 — focused local gate:** proves one behavior at one exact commit.
- **E2 — maintained corpus gate:** proves the declared semantic projection over
  the versioned project-owned corpus.
- **E3 — differential research evidence:** compares overlapping semantics against
  a pinned external oracle; differences and oracle failures remain visible.
- **E4 — release qualification:** exact-head CI, package, corpus, complexity, and
  compatibility evidence for a release candidate.

No lower level may be presented as a higher one. A null result, unsupported
syntax, oracle crash, timeout, or unexplained difference is recorded, not
converted into a pass or silently added to an allowlist.

## 11. Ordered milestones

### M0 — Publish the study and operating boundary

**Outcome**

- Versioned plan, persistent goal, provenance relation, parent-roadmap link,
  documentation chronology, and changelog entry.

**Dependencies**

- Exact source and reference revisions verified.

**Exit evidence**

- `rtk make docs-check`, `rtk make vendor-name-check`, `rtk make all`, and
  `rtk git diff --check` complete successfully on the delivery branch.
- The reviewed commit SHA is pushed, recorded in the pull request, and matches
  the head SHA whose required GitHub checks reach a terminal green state.

**Impact**

- Creates no parser behavior or license change.

**Residual risk**

- No future implementation is authorized merely by publishing this plan.

### M1 — #104-A project-owned semantic projection and corpus foundation

**Outcome**

- Deliver the first explicit tranche of
  [#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104)
  without closing the expanded parent issue.
- Add one private projector producing `exact_parse_v1` and
  `semantic_roundtrip_v1` under the field and identity contracts in section 2.1.
- Add an original, offline, versioned corpus whose manifest records corpus,
  fixture, and snapshot schema versions, source SHA-256/provenance/license,
  parse configuration, protected behaviors, identity policy, expected outcome,
  and expected diagnostic codes.
- Preserve the closed #113 depth matrix and minimized regression as protected
  corpus behavior while retaining focused unit tests as the narrow defect
  owners.
- Add bounded file-entrypoint assertions without freezing absolute host paths or
  duplicating the symlink and `file://` security suites owned by #106.

**Dependencies**

- M0 merged through PR #159; current API, architecture, path, package, license,
  quality-gate, and semantic contracts re-verified.
- #103 remains the owner of complete incremental/cold-load snapshot equivalence.

**Exit evidence**

- Original Apache-2.0 fixtures only; source hashes and manifest provenance
  validated; `.gitattributes` proves LF checkout bytes for the corpus; discovery
  order cannot change canonical snapshots.
- Exact-parse, semantic-roundtrip, identity, hierarchy, depth, and bounded
  file-entrypoint tests remain in the fast CI budget.
- Regression tests prove comma-aware canonical reference-property sequences,
  preservation of content wikilinks that coincide with property tags, and
  count-based removal of property-origin wikilink occurrences.
- The valid-only manifest rejects non-empty diagnostics, Boolean schema
  versions, and Boolean tab sizes; the quality-gate contract proves the snapshot
  generator remains in the mypy command.
- The root export manifest is unchanged, no runtime/package dependency is added,
  `make all` and `make vendor-name-check` pass, and `src/` has zero import cycles.

**Impact**

- Makes semantic drift reviewable without freezing incidental Pydantic, JSON,
  filesystem, or host-path details and without promoting a test oracle to the
  stable public API.

**Residual risk**

- Project-owned invariants can share the same blind spots as the implementation.
- M1-A alone does not satisfy #104's generated malformed-input,
  incremental/cold-load, or complete filesystem-abuse acceptance criteria.

### M2 — External oracle feasibility and license gate

**Outcome**

- A decision record determines whether a pinned, unmodified `mldoc` executable
  may be used as a separate research oracle without entering runtime packages or
  release artifacts.
- Scope is limited to shared observable semantics; differences caused by this
  project's intentionally different AST and graph responsibilities are typed.
- Oracle errors, version drift, and unknown mappings fail closed.

**Dependencies**

- M1 projection stable; dependency-license inventory; maintainer approval of the
  selected process boundary. Qualified legal review is required if packaging,
  linking, service deployment, or source adaptation is proposed.

**Exit evidence**

- Accepted ADR, exact oracle version/hash, documented installation boundary,
  no package/runtime dependency, original comparison adapter and fixtures, and
  a reproducible local proof. If rejected, the negative decision is the valid
  milestone result and M3 continues without an external oracle.

**Impact**

- Can expose shared parser blind spots without claiming full parity.

**Residual risk**

- Oracle behavior is not necessarily the desired product behavior; human
  adjudication remains mandatory.

### M3 — Adversarial and property-based semantic laboratory

**Outcome**

- Original generators cover indentation depth, malformed fences, escapes,
  overlapping delimiters, properties, references, Unicode, CR/LF variants,
  large lines, and incremental/cold-load equivalence.
- Every generated run has bounded size, deterministic replay information, and
  subprocess timeout protection.
- Complete the remaining expanded #104 acceptance criteria without duplicating
  the focused #103 snapshot owner or the established #106 security contracts.

**Dependencies**

- M1; optional M2 when accepted; #103 for complete incremental snapshot claims.

**Exit evidence**

- Fixed-seed CI subset; scheduled broader run; minimized original regression
  fixtures; no crash, hang, invariant loss, or unclassified failure.

**Impact**

- Extends confidence beyond examples and line coverage.

**Residual risk**

- Passing generated families does not prove all real Logseq content.

### M4 — Deterministic work-growth and performance budgets

**Outcome**

- Define a Python-native, test-only parser work model based on this parser's own
  phases and operations; do not reproduce lsdoc's counter placement or schema.
- Run input families at increasing sizes and reject superlinear growth outside
  explicitly documented exceptions.
- Preserve #87 as the focused pathological seed and #111 as the wall-time,
  p95, RSS, and vault-scale owner.

**Dependencies**

- M1 semantic oracle; impact analysis before parser-hub instrumentation.

**Exit evidence**

- Deterministic work ratios, targeted timeout tests, platform-labelled timing
  baselines, memory evidence, unchanged semantic projection, and documented
  noise policy.

**Impact**

- Separates algorithmic regression from machine-speed variance.

**Residual risk**

- An incomplete work model can miss uninstrumented library or regex costs;
  timing and profiling remain complementary.

### M5 — Privacy-safe local graph assurance tool

**Outcome**

- Optional local command evaluates project-owned invariants and, only if M2 is
  accepted, differential overlap against the external oracle.
- Default behavior uploads nothing, excludes graph content from reports, bounds
  files/bytes/time, stores only safe aggregates, and requires explicit opt-in to
  retain minimized snippets.

**Dependencies**

- M2 decision, M3 minimization, filesystem safety review, and threat model.

**Exit evidence**

- Temporary synthetic vault tests; self-test; privacy review; fail-closed report
  schema; no network operation during graph analysis.

**Impact**

- Finds reachable user-content edge cases without centralizing private vaults.

**Residual risk**

- Even minimized snippets can be sensitive; retention remains opt-in and local.

### M6 — Source-location RFC and prototype

**Outcome**

- Decide whether consumers need byte offsets, code-point offsets, line/column
  ranges, or a separate source-map object.
- Define newline, Unicode, transformed text, provenance, serialization, and
  stale-range behavior.
- Prototype behind an experimental API without changing stable node fields.

**Dependencies**

- M1; concrete consumer cases from diagnostics, agent reads, or bounded edits.

**Exit evidence**

- Accepted or rejected RFC; non-ASCII and CR/LF tests; safe slicing behavior;
  round-trip and writer compatibility; performance measurement.

**Impact**

- Could improve precise diagnostics and future editor integrations.

**Residual risk**

- Memory and compatibility costs may outweigh demand; rejection is acceptable.

### M7 — Parser phase extraction under frozen evidence

**Outcome**

- Resume [#108](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/108)
  one Python-native phase at a time only after semantic and performance gates.

**Dependencies**

- M1, M3, M4; fresh impact analysis for every protected hub.

**Exit evidence**

- Tranche-specific unit tests, complete semantic equivalence, work/timing
  comparison, `make all`, terminology gate, and zero import cycles.

**Impact**

- Reduces change risk without a big-bang parser rewrite.

**Residual risk**

- Some seams may not justify extraction; preserving a deliberate hub is valid.

## 12. Explicit deferrals and rejection triggers

| Proposal | Disposition | Reconsider only when |
|---|---|---|
| Rewrite parser in Rust | rejected | a separate product decision proves Python cannot meet measured requirements |
| Depend on or embed lsdoc | rejected under current Apache-only policy | upstream grants suitable permission/relicense and architecture review approves it |
| Copy/adapt lsdoc tests or corpus | rejected | never under this plan |
| Mirror lsdoc AST/API | rejected | never as a compatibility shortcut |
| Full render-level mldoc parity | deferred | a renderer becomes a supported product with named consumers |
| Org parser | deferred | real user demand, fixtures, API decision, and maintenance owner exist |
| Publish parity/performance headline | deferred | exact reproducible project evidence reaches E4 |
| Replace graph or writer around parser-only patterns | rejected | independent project requirements justify a separate plan |

## 13. Delegation and cost policy

1. Deterministic source inspection and repository scripts come first.
2. Low-cost workers may inventory docs, distill terminal logs, create mechanical
   fixture metadata, or independently review settled prose.
3. Workers receive the minimum relevant excerpts and no secrets or private
   graph content.
4. One worker owns one non-overlapping file group.
5. The primary agent retains license interpretation, architecture, security,
   oracle adjudication, API promotion, release, and merge decisions.
6. One failed low-cost attempt and one focused correction are allowed before
   escalation; missing output is not evidence.
7. Every delegated conclusion is rechecked against source or deterministic
   validation before acceptance.

For M1-B, a low-cost worker may own one bounded mechanical file group after the
contract in section 2.2 is fixed: projector regression-test scaffolding;
manifest negative-test scaffolding; or documentation chronology. The primary
agent retains reference-token semantics, path/EOL security, exact-head
qualification, Git-history decisions, and publication judgment.

## 14. Validation and publication gates

For this documentation milestone:

```bash
rtk make docs-check
rtk make vendor-name-check
rtk make all
rtk git diff --check
```

Implementation milestones additionally require:

- exact-head impact analysis before protected parser or graph hubs;
- audit-code cycle check with zero cycles in `src/`;
- focused semantic, work-growth, timing, and privacy evidence appropriate to the
  milestone;
- no private vault data, copied AGPL material, or unreviewed dependency change;
- separate approval for merge, release, external service deployment, or license
  change.

M1-B additionally requires these exact local commands on the corrective
implementation commit:

```bash
rtk uv run python scripts/update_compat_snapshots.py
rtk uv run pytest -q tests/test_compat_corpus.py tests/test_parser_deep_refresh.py tests/test_quality_gate_contract.py
rtk uv run ruff check scripts/update_compat_snapshots.py tests/parser_assurance tests/test_compat_corpus.py tests/test_parser_deep_refresh.py tests/test_quality_gate_contract.py
rtk make all
rtk make vendor-name-check
rtk git diff --check origin/main...HEAD
```

The checkout must be clean and the audit-code cycle check must report zero
cycles. The exact implementation SHA then receives a frozen primary and
low-cost independent review. A later documentation-evidence commit must pass at
least `make all`, `make vendor-name-check`, documentation validation, diff
check, and hosted required checks on its own exact head.

## 15. Interruption and recovery

At every handoff record the source base, branch, exact HEAD, worktree path,
dirty state, completed validations, unproven gates, active workers, external
oracle version, and next command. Preserve work in a local commit when
authorized. A temporary worktree path alone is not a durable checkpoint.

Milestone reports use:

- result obtained;
- terminal validation evidence;
- behavior or claim changed;
- residual risks;
- next dependency.

The current resumable checkpoint is
[`internal/M1A_CORRECTIVE_HARDENING_RESTART_HANDOFF_2026-08-16.md`](internal/M1A_CORRECTIVE_HARDENING_RESTART_HANDOFF_2026-08-16.md).

## 16. Persistent goal

The short execution pointer is versioned separately at
[`goals/LSDOC_PARSER_ASSURANCE_GOAL.md`](goals/LSDOC_PARSER_ASSURANCE_GOAL.md).
It must not replace the requirements in this plan.

## 17. Completion checklist

- [x] M0 is merged and publicly available through PR #159.
- [x] #104-A is implemented and locally qualified on the working tree with an
  initial original, provenance-safe projection and corpus foundation; the
  resulting commit is retained as rejected pre-correction evidence.
- [ ] M1-B preserves authentic content wikilinks and canonicalizes all four
  reference-property families with comma-aware, count-based semantics.
- [ ] M1-B enforces LF corpus bytes, empty valid-fixture diagnostics, exact
  integer manifest fields, and snapshot-generator mypy coverage.
- [ ] The corrective implementation commit is clean, exact-head qualified, and
  independently reviewed without unresolved P0/P1/P2 findings.
- [ ] A separate evidence commit records the implementation SHA and is covered
  by terminal hosted validation before #104-A is merged.
- [ ] The remaining expanded #104 acceptance criteria are proved through the
  dependency-owned #103 and M3 evidence before #104 is closed.
- [ ] The external-oracle decision is recorded, including a valid negative
  decision if license or process boundaries are unacceptable.
- [ ] Adversarial and property-based tests have deterministic replay and bounded
  execution.
- [ ] #87 and #111 have complementary deterministic-work and measured-runtime
  evidence without semantic drift.
- [ ] The privacy-safe local graph tool is delivered or explicitly rejected with
  recorded reasons.
- [ ] The source-location RFC is accepted or rejected with consumer and cost
  evidence.
- [ ] Every #108 extraction slice is covered by the semantic and performance
  gates, or the epic records why no extraction is justified.
- [ ] No AGPL-covered expression entered Apache-only source, tests, fixtures,
  schemas, or documentation.
- [ ] Documentation, issue state, and public claims match the delivered behavior.
- [ ] Every validation and publication gate is terminal for the exact revisions
  claimed.

Completion is unproven until every applicable item has authoritative evidence.

## 18. Execution ledger

| Date | Anchor | Result | Evidence and residual boundary |
|---|---|---|---|
| 2026-08-16 | M0 / PR #159 | merged | Source head `a6056413`, squash merge `30946446`; PR records 535 passing tests, 91.95% coverage, documentation/package/vendor gates, and zero cycles. No parser behavior changed. |
| 2026-08-16 | M1 activation | verified | Clean `agent/parser-assurance-m1` at `e2a3f9a`, matching `origin/main`; no tracked M1 changes at activation. |
| 2026-08-16 | Independent M1 review | reconciled | Accepted the larger review surface, two-profile/single-projector model, explicit identity policy, and manifest expansion after source and live-issue verification. M1 is #104-A; #104 remains open. |
| 2026-08-16 | Low-cost inventories | advisory | Two Spark read-only inventories located reusable tests and model fields. Their proposals are not authority; only source-verified evidence is admitted to implementation. |
| 2026-08-16 | M1-A implementation | local, uncommitted | Added one private two-profile projector, a strict versioned manifest, six original Apache-2.0 fixtures and exact snapshots, bounded file-entrypoint assertions, and reuse from the deep-refresh regression suite. No `src/`, root export, or runtime dependency changed; final qualification and publication remain separate gates. |
| 2026-08-16 | M1-A implementation review | reconciled | A bounded Spark review found no P0/P1. Its valid non-atomic snapshot-write P2 was corrected; manifest-negative and snapshot-CLI contracts were added. Its `source_uuid` P2 was rejected after primary verification because the projection deliberately exposes source identity and the dedicated test applies each `preserve`/`absent` policy without masking drift. |
| 2026-08-16 | M1-A working-tree qualification | provisional | `rtk uv run python scripts/update_compat_snapshots.py` passed in non-mutating freshness mode; `rtk make all` passed with 553 tests and 92.07% coverage; Ruff, mypy, documentation, vendor-name, and diff checks passed; audit code reported zero `src/` import cycles. `rtk uv run python scripts/update_compat_snapshots.py --write` is the only explicit regeneration mode, and stale snapshots make the default command exit nonzero. This is not E1/E2 because the qualified bytes were not yet committed. |
| 2026-08-16 | M1-A local commit `8806205` | exact-head tests passed; publication rejected | Clean local commit recorded 556 passing tests, 92.07% coverage, snapshot freshness, `make all`, vendor-name, diff, and zero-cycle checks. A later independent full-patch review found two oracle P1s: malformed multi-reference normalization and deletion of authentic content wikilinks. The commit must not be pushed as M1-A evidence. |
| 2026-08-16 | M1-B corrective review | verified and prepared | Primary runtime probes reproduced both P1s and proved acceptance of non-empty unverified diagnostics and Boolean integer fields. Source review confirmed raw-byte hashes without LF checkout policy and omission of the snapshot generator from the maintained mypy command. Two bounded Spark inventories were advisory; the primary retained semantic and security decisions. The goal remains paused and no implementation, push, or PR is claimed. |
