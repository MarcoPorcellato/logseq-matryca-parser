# Changelog

All notable changes to **logseq-matryca-parser** (The Logos Protocol) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Documented graph-path compatibility** — `LogseqGraph.load_directory`
  accepts both `pathlib.Path` and string graph roots, matching the stable
  copy-paste examples without changing path resolution or vault discovery.

### Changed

- **Static-analysis adoption record** — document the current quality baseline,
  non-overlapping candidate tools, ranked pilots, explicit unknowns, and
  maintainer gates without installing or enabling new analysis software.
- **Code-aligned human and agent documentation** — reconcile the CLI command
  surface, default `scan` behavior, contributor task navigation, architecture
  claims, and diagrams with the current implementation.

## [1.8.1] - 2026-08-25

### Security

- **Stable NLTK supply-chain source (#186)** — the optional AI and development
  dependency graph now constrains NLTK to the patched PyPI release line at
  `>=3.10.3`, replacing the mutable `v3.10.0-rc1` VCS tag declaration. The
  lightweight base installation remains unchanged.

### Added

- **Reproducible runtime evidence foundation (#111)** — add a deterministic,
  offline synthetic-vault generator and a source-free measurement runner for
  parser, cold-load, reload, search, and optional SYNAPSE scenarios. The runner
  records semantic validity and bounded runtime observations outside the
  default CI gate. It establishes a measurement protocol, not vault-scale
  budgets or a universal performance claim; #111 remains open.

### Changed

- **Private lexical-state extraction (#108 M9)** — move YAML, code, query,
  drawer, frontmatter, and block-property eligibility transitions into a
  private standard-library-only state object. `StackMachineParser.parse()`
  retains line classification, reduction, AST construction, identities,
  semantic enrichment, and public behavior. The broader #108 epic remains
  open.

### Fixed

- **Coherent incremental graph mutations (#103)** — reloads, deletions, and
  filesystem moves now publish page routing, node and backlink registries, and
  collision diagnostics as one coherent graph snapshot. Conflicting title or
  alias participants can recover deterministically, bounded writes serialize
  their source read and reload transaction, and watcher callbacks observe the
  published state in order. Stable public APIs remain unchanged.
- **Pathological nested outlines (#87)** — parse and file-entrypoint traversal
  now remain iterative for a 1024-level valid outline, while parser-owned tree
  construction avoids quadratic immutable-ancestor copies. Derived metadata is
  refreshed once after tree construction instead of repeatedly across mutable
  soft-break ancestors, and parser registries are rebuilt from the exact final
  nodes returned by parse and file entry points. Strict reference validation is
  confined to the current page. Tree order, parent and left relationships,
  source paths, semantic snapshots, and the stable public API are preserved.
  Deterministic tests bound refresh growth; local timing observations remain
  diagnostic only and do not add a vault-scale performance claim.
- **Bounded local-assurance timeout cleanup (#188)** — a timed-out isolated
  assurance worker is terminated and joined before its result queue is closed,
  preventing queue-thread cleanup from extending the bounded failure path.

### Tests

- Expand privacy-safe local-assurance regression coverage across traversal and
  byte limits, guarded reads, parser aggregation, report validation, denied
  network entry points, worker lifecycle, and failure cleanup without exposing
  vault content or weakening the repository coverage floor.

## [1.8.0] - 2026-08-20

### Tests

- Define and regress the existing one-based source-line contract across Unicode
  text and CRLF input. The accepted M6 decision retains line-only
  parse-snapshot locations and adds no offset API or parser behavior change.
- Add a deterministic, test-only parser work-growth laboratory with fixed
  size-scaled synthetic cases, semantic and structural gates, source-free
  receipts, and non-gating platform observations. No runtime API or performance
  claim is added.

### Added

- **Governance and agent-assurance system** — added public governance,
  maintainership, support, citation, AI-contribution, issue-triage, roadmap,
  agent-action, compatibility, AAIF-alignment, and protocol-decision surfaces,
  with explicit source authority and no unsupported remote or membership claim.
- **Release supply-chain evidence** — the release workflow now generates a
  CycloneDX 1.5 production SBOM, scoped dependency/license inventory, checksum
  manifest, GitHub build-provenance attestations, and an SBOM attestation bound
  to the exact wheel and sdist; all evidence is preserved in the immutable
  bundle and attached to the GitHub Release.
- **Pull-request dependency review and scheduled Scorecard** — added SHA-pinned,
  least-privilege workflows for newly introduced vulnerabilities and OpenSSF
  Scorecard SARIF monitoring.
- **Privacy-safe local graph assurance (M5)** — added `matryca-parse assure`, an
  optional bounded local check that runs in a fresh worker, rejects symlinks,
  limits files/bytes/time, denies ordinary socket entry points, and returns a
  fixed aggregate-only JSON report. It does not upload, persist, or emit vault
  content, paths, titles, UUIDs, exception text, or host names. This is not an
  external-parser, performance, or release-qualification claim.
- **Deterministic adversarial parser laboratory (#104 M3)** — added original,
  bounded generators for parser depth, malformed fences, escapes and delimiters,
  properties and references, Unicode/newline variants, large lines, and strict
  unresolved references. Each case runs in a fresh subprocess with a parent
  timeout, safe replay receipt, classification-preserving minimization, tree
  invariants, and semantic round-trip checks for valid inputs. The fixed profile
  runs with the ordinary suite; an offline scheduled broad profile expands only
  deterministic seeds and case counts. No parser runtime, public API, package
  dependency, #103 snapshot-equivalence, or #111 performance claim changes.
- **Parser compatibility corpus foundation (#104-A)** — added six original,
  offline Apache-2.0 fixtures with source hashes and strict provenance, schema,
  parser-configuration, behavior, diagnostics, and identity-policy metadata;
  one private projector now drives exact-parse snapshots and semantic
  parse/serialize/parse checks without changing the stable package API. The
  expanded parent issue #104 remains open for graph reload, generated malformed
  input, and broader filesystem-assurance work.
- **Parser assurance reference study** — added a license-safe comparative
  analysis of `martinkoutecky/lsdoc@c79cb059` and a dependency-ordered plan for
  a project-owned semantic corpus, optional external-oracle decision, original
  adversarial generators, deterministic complexity evidence, privacy-safe local
  graph checks, and a source-location RFC. No AGPL source, tests, corpora,
  schemas, or documentation were copied or adapted.

### Changed

- **Internal line classification (#165 M7)** — route the existing parser loop
  through a private, immutable syntax event while retaining the stack reducer,
  AST construction, semantic enrichment, identities, public API, and
  dependencies. The change is covered by focused parser, corpus, adversarial,
  and deterministic work-growth tests; it makes no benchmark or release claim.

### Fixed

- **Diagnostic dependency boundary** — replaced the graph module's type-only
  reverse import with a minimal structural protocol, preserving the public
  diagnostic behavior while restoring a zero-cycle source import graph.
- **Public checksum layout** — release checksum entries now use the flat asset
  names exposed by GitHub Releases while each internal job still verifies the
  immutable bundle layout, so the documented clean-download command works.
- **Compatibility-corpus assurance oracle** — canonical reference-property
  sequences now preserve commas inside page references and normalize complex
  `#[[tag]]` values; property-origin wikilinks are removed by occurrence while
  equal content links and their order remain visible, including when matching
  text appears inside parser-shielded code, comments, math, fences, or queries.
  Valid fixtures reject undeclared diagnostics and Boolean schema/configuration
  fields; corpus bytes are forced to LF, and the snapshot generator is covered
  by the maintained mypy gate. This changes tests and tooling only, not package
  runtime behavior.
- **Packaging metadata compatibility** — pin the Hatchling build backend to the
  last release that emits Core Metadata 2.4 by default, keeping the published
  wheel and source distribution accepted by the release Twine gate.

### Security

- **Metrics archive hardening** — restricted the self-mutating workflow to
  trusted `main`, separated read-only traffic credentials from the job-scoped
  write token, bounded API retries, time, and response size, validated complete
  payloads before mutation, and replaced JSON files atomically.
- **Explicit assurance gates** — documented the release evidence and metrics
  threat models, retained the measured official OKF v0.2 backlog instead of
  masking it, and recorded a NO-GO for AAIF submission until external,
  governance, adoption, release, and legal evidence exists.
## [1.7.1] - 2026-08-08

Patch release correcting the v1.7.0 SYNAPSE example promise, hardening release
notes validation, and refreshing vulnerable optional-development dependencies.
**No intentional breaking changes** to package APIs or CLI behavior.

### Added

- **Runnable SYNAPSE RAG example** —
  [`examples/run_synapse_rag.py`](examples/run_synapse_rag.py) exercises the
  LangChain, LlamaIndex, and context-enriched conversion paths against an
  offline temporary Logseq graph, including verified expansion of a resolved
  page embed ([#90](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/90)).

### Changed

- **Release contract** — release-note validation now rejects missing or
  repository-escaping local Markdown links, preventing a tag from promising an
  artifact that is not present in its source tree.
- **Release documentation** — the v1.7.0 record and public release notes carry
  a dated erratum for the omitted SYNAPSE example while preserving the
  immutable v1.7.0 tag, artifacts, attestations, and checksums.

### Security

- **Optional AI/development lock** — constrained `aiohttp>=3.14.3` and
  `setuptools>=83.0.0`, resolving the four Dependabot advisories open against
  the v1.7.0 lock. Neither dependency is part of the base package runtime.

## [1.7.0] - 2026-08-08

Minor release — structured diagnostics, deterministic title-collision handling,
arbitrary-depth parser refreshes, typed public APIs, vault-bound writer safety,
and a governed English documentation system. **No intentional breaking changes**
to stable package exports or default CLI behavior.

### Added

- **Verified immutable release pipeline** — tag, source, runtime, and changelog
  contracts now fail closed before packaging; Python 3.12/3.13 pre-flight runs
  the full quality and dependency-audit gates; wheel and sdist are built once,
  checked with Twine, checksummed, published to PyPI with OIDC attestations, and
  attached byte-for-byte to the GitHub Release
  ([#105](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/105)).

- **Structured diagnostic foundation** — stable immutable `Diagnostic`,
  `DiagnosticCode`, and `DiagnosticSeverity` exports; deterministic
  `collect_graph_diagnostics()` for broken block references; vault-relative
  path enforcement; and pure JSON CLI output through `scan --diagnostics-json`
  ([#110](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/110)).
- **Graph title-collision contract** — permissive loading now exposes stable
  diagnostics for derived-title, frontmatter-title, and alias collisions while
  preserving the existing deterministic winner and no-ghost invariants;
  `strict_title_collisions=True` raises `PageTitleCollisionError`, and KINETIC
  renders all findings with `scan --diagnostics`
  ([#102](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/102)).
- **Documentation system guide** — [`docs/DOCUMENTATION_SYSTEM.md`](docs/DOCUMENTATION_SYSTEM.md) explains source authority, maintained versus historical surfaces, metadata, freshness, validation, the Matryca Knowledge projection workflow, and the repository's documentation evolution.
- **Embed expansion edge-case tests** — `TestEmbedExpansionEdgeCases` in [`tests/test_synapse.py`](tests/test_synapse.py) covers cycles, missing targets, and happy-path for both `{{embed [[Page]]}}` and `{{embed ((uuid))}}` (closes [#71](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/71)).
- **Contributor onboarding (wave 4)** — ten new Good First Issues (GFI-39…GFI-48) filed on GitHub ([#88](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/88)–[#97](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/97)); index updated in [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md).

### Changed

- **Immutable workflow dependencies** — all release and CI actions are pinned to
  reviewed commit SHAs with readable release comments; the former independent
  GitHub and PyPI tag workflows are consolidated into one ordered release graph.

- **Federated documentation profile** — aligned the maintained bundle with Matryca Knowledge `origin/main` at `7a3ebd8`, separating OKF lifecycle from Matryca classification and recording authority, freshness, provenance, and the still-pending private registry activation.
- **Ghost Tooling** — removed remaining vendor indexer blocks from `AGENTS.md` / `CLAUDE.md`; maintainer guidance now uses **audit code** terminology only.
- **Repository language** — translated the historical audit reports, design references, Logseq Read skill, maintainer configuration comments, parser warning, demo labels, and optional SYNAPSE dependency errors into English; contributor guidance now makes English the repository default ([#69](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/69)).
- **Documentation quality tranche** — added `scripts/check_documentation.py`, source `docs/maintained.toml`, and focused tests; wired the deterministic, non-mutating `docs-check` into `make all` and CI. This implements the source-side MKQ-3 gate; MKQ-4 remains pending until private `okf_entry_points` and projection activation pass against the merged source commit.

### Fixed

- **Vault-bound writer and asset reads** — headless child writes now reject
  external/untracked/symlink-swapped targets, verify target identity before
  replacement, preserve permission and ownership metadata, expose typed safe
  diagnostics and configurable limits, and support unified-diff dry runs;
  `file://` and asset symlink reads are confined to the graph
  ([#106](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/106)).
- **Deep parser refreshes** — immutable node updates now rebuild the complete
  active branch to the root at arbitrary nesting depth, preserving soft breaks,
  properties, fenced code, queries, list properties, ordering, identity, and
  parent/left relationships ([#113](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/113)).
- **LENS topology** — unresolved wikilinks no longer create phantom page nodes when visualization uses a loaded `LogseqGraph`; valid page aliases and tags remain visible ([#59](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/59)).

### Security

- **Artifact lineage** — PyPI publication must succeed before the GitHub Release
  is created, and every consumer re-verifies the SHA-256 manifest for the exact
  distributions produced by the single build job.

### Documentation erratum (2026-08-08)

- The initial GitHub Release notes incorrectly listed
  `examples/run_synapse_rag.py`. The file is not part of v1.7.0 and
  [#90](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/90)
  remains open. This documentation-only correction does not change the tag,
  distributions, attestations, or published SHA-256 digests.

## [1.6.0] - 2026-07-02

Minor release — Clean Architecture v1 structural slices (SRP/OCP), new public graph APIs, layer-boundary CI, and documentation SSOT. **No intentional breaking changes** to existing `matryca-parse` CLI behavior or stable package exports.

### Added

- **Clean Architecture SSOT** — [`docs/CLEAN_CODE_ARCHITECTURE.md`](docs/CLEAN_CODE_ARCHITECTURE.md) maps Uncle Bob rings, SOLID, and module maps; quality index in [`docs/quality/`](docs/quality/) (backlog, GitHub roadmap, July 2026 triage).
- **`kinetic_export.py`** — KINETIC format handlers extracted from `kinetic.py` (DEBT-005 / [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80)).
- **`kinetic_commands.py`** — `scan`, `visualize`, `demo`, `append`, `agent-read`, and `agent-write` subcommands (SRP slice / [#82](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/82)).
- **`synapse_embed.py`** — `BlockEmbedExpander` / `PageEmbedExpander` strategy pattern for embed expansion (DEBT-006 / [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70)).
- **`LogseqGraph.iter_attached_nodes()`** — public ISP iterator skipping orphan ghost registry entries ([#81](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/81)).
- **Layer boundary CI** — `tests/test_layer_boundary.py` forbids framework imports in entities/use cases, adapter→driver leaks, and Typer/Rich in `kinetic_export.py`.
- **`make vendor-name-check`** — Ghost Tooling gate for vendor-free public documentation.
- **Maintainer local code audit runbook** — [`docs/internal/LOCAL_CODE_STUDY.md`](docs/internal/LOCAL_CODE_STUDY.md).
- **GitHub issue template** — `.github/ISSUE_TEMPLATE/clean_architecture.yml` for Uncle Bob slices; bootstrap script `.github/scripts/create_clean_arch_issues.sh`.

### Changed

- **`kinetic.py`** — slim Typer app factory (~230 lines): `export` orchestration + shared CLI helpers; subcommands in `kinetic_commands.py`.
- **`LogseqGraph.is_tracked_markdown_path()`** — public DIP surface for watcher path checks ([#68](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/68)).
- **KINETIC** — removed dead `_parse_graph` helper ([#67](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/67)).
- **Ghost Tooling** — vendor AST indexer names removed from public docs; unified on **local code audit** / **graph-based code study** terminology.
- **Contributor docs** — [`README.md`](README.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/COOKBOOK.md`](docs/COOKBOOK.md), [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md), and [`CONTRIBUTING.md`](CONTRIBUTING.md) updated for v1.6.0 and **456** pytest cases.

### Meta (contributor tracking)

- **Clean Architecture epic** — [#78](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/78) (phases [#79](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/79)–[#83](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/83)).
- **Contributor waves 3–5** — issues [#59](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/59)–[#73](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/73) filed from local code study; agent rule [`.cursor/rules/07-clean-architecture-audit.mdc`](.cursor/rules/07-clean-architecture-audit.mdc).

## [1.5.0] - 2026-06-29

### Added

- **CLI** — `matryca-parse scan --broken-refs` reports unresolved `((uuid))` block references in a Rich table and exits with status 1 when any are found ([#29](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/29), [#77](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/77)).

### Changed

- **Contributor docs** — [`README.md`](README.md), [`docs/COOKBOOK.md`](docs/COOKBOOK.md), [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md), and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) document the new scan flag and **451** pytest cases.

## [1.4.2] - 2026-06-29

### Fixed

- **agent-write** — `append_child_to_node` normalizes source files missing a trailing newline before line splice, preventing new bullets from being appended onto the last line ([#72](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/72), [#74](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/74)).
- **SYNAPSE** — cyclic `{{embed [[Page]]}}` chains no longer duplicate parent literal text; page embed expansion tracks an immutable host-page chain seeded from `to_context_enriched_chunks` ([#65](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/65), [#75](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/75)).
- **agent-write** — `SessionAliasRegistry.load_from_disk` tolerates empty, malformed, or legacy-wrapped X-Ray JSON; KINETIC exits with a clear message instead of a traceback ([#60](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/60), [#76](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/76)).

### Added

- **Test coverage (wave 2)** — Community contribution ([#58](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/58), maintainer #43): **65** new pytest cases for `detect_tab_size_from_markdown`, graph link/backlink helpers, SYNAPSE embedding strip + metadata schema, FORGE Markdown/JSON visitors, LENS node classification, `extract_changelog` CLI, `LogseqConfigReader` timestamps, and KINETIC `agent-write` validation errors. Closes [#20](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/20), [#43](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/43)–[#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52).
- **Regression tests** — Seven new cases for newline splice, cyclic page embed, and malformed X-Ray state (issues [#73](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/73), [#65](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/65), [#60](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/60)); suite total **450** pytest.

### Changed

- **Contributor docs** — [`README.md`](README.md), [`docs/README.md`](docs/README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) harmonized for **v1.4.2** (test count, supported versions, agent-write / SYNAPSE behavior notes).

## [1.4.1] - 2026-06-24

### Added

- **Test coverage (wave 1)** — Community contribution ([#42](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/42)): **107** new pytest cases (**378** total) across parser helpers (`normalize_logseq_timestamp`, `clean_node_content`), `logseq_paths` fallbacks, exception hierarchy, `extract_changelog` release script, KINETIC per-command `--help`, `agent-read --query`, and direct `ObsidianForgeVisitor` tests. New modules: `tests/test_exceptions.py`, `tests/test_extract_changelog.py`. Closes [#21](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/21)–[#24](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/24), [#27](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/27), [#30](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/30)–[#32](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/32).
- **Good first issues (wave 2)** — Ten new contributor tasks ([#43](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/43)–[#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52)) indexed as GFI-17–GFI-26 in [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md); wave-1 GFI items marked complete.

### Changed

- **Contributor docs** — [`README.md`](README.md), [`docs/README.md`](docs/README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) harmonized for **v1.4.1** (test count, issue index range, supported versions).

## [1.4.0] - 2026-06-23

### Added

- **Bug hunt report** — [`docs/BUG_HUNT_REPORT.md`](docs/BUG_HUNT_REPORT.md): local static analysis audit waves 1–8 complete (31 bug IDs, module inventory §10): parser crash, ghost registry, export dupes, API case/alias inconsistencies, SYNAPSE hang.
- **Contributor onboarding** — [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md) indexes 16 starter tasks ([#19](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/19)–[#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34)); [`docs/README.md`](docs/README.md) distinguishes active vs historical documentation; GitHub labels (`good first issue`, `help wanted`, `tests`, `documentation`, `cli`, `forge`) and issue-template contact link; **Your first PR** section in [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Integration cookbook & doc harmonization** — [`docs/COOKBOOK.md`](docs/COOKBOOK.md); [`docs/design-docs/README.md`](docs/design-docs/README.md); draft [`docs/rfc/OLLAMA_RAG.md`](docs/rfc/OLLAMA_RAG.md); cross-links across README, ARCHITECTURE, AST primer, RELEASE_PROCESS, CODEQL, SECURITY, and PR template; `examples/run_demo.py` English + package imports.

### Changed

- **Ghost Tooling policy** — Matryca.ai vendor-agnostic compliance: local static analysis tools excluded from CI, Makefile, and public documentation; see [`docs/internal/STATIC_ANALYSIS_POLICY.md`](docs/internal/STATIC_ANALYSIS_POLICY.md) and [`.cursorrules`](.cursorrules).
- **Repository metrics archive** — `scripts/archive_repository_metrics.py` partitions traffic into `metrics/quarters/YYYY-QN.json` with `metrics/index.json` manifest; legacy `metrics/history.json` is migrated once on first run.

### Fixed

- **Daily metrics workflow** — `.github/workflows/daily-metrics.yml` syncs with `main` before archiving, uses `pull --rebase` with push retries, serializes runs via `concurrency`, and commits the quarterly metrics tree instead of a monolithic JSON file.
- **BUG-017** — `StackMachineParser._refresh_node` no longer crashes on empty bullets with block properties (`IndexError`).
- **BUG-001 / BUG-003** — SYNAPSE page/block embed expansion uses `get_page` (case-insensitive) and fail-safe empty replacement instead of infinite loops on unresolved embeds.
- **BUG-016** — `append_child_to_node` calls `invalidate_and_reload_page` so the in-memory graph matches disk after agent-write.
- **BUG-005** — `invalidate_and_reload_page` purges registry/backlinks when the markdown file was deleted instead of raising `FileNotFoundError`.
- **BUG-010 / BUG-013 / BUG-022** — `load_directory` rebuilds `_node_registry` from indexed pages only (no ghost nodes after title collision or duplicate `title::`); `search_content`, `GraphQuery`, and `get_nodes_by_tag` iterate attached nodes.
- **BUG-026** — Wikilink backlink index includes canonical title and `alias::` keys so `get_backlinks("Development")` matches `[[Dev]]`.
- **BUG-012** — `get_node_by_embed_ref` resolves block UUIDs case-insensitively.
- **BUG-014** — `LogseqGraphWatcher` handles `on_deleted` and `on_moved` filesystem events.
- **BUG-028** — `get_namespace_children` uses case-insensitive namespace prefix matching.
- **DEBT-001 / BUG-006** — `iter_canonical_pages()` deduplicates alias keys; KINETIC export paths use canonical pages (no duplicate Obsidian/langchain/json output).
- **BUG-011 / BUG-021** — Per-page `tab_size` detection at parse time; `serialize_logseq_page` and `append_child_to_node` preserve four-space vault indentation.
- **BUG-008 / BUG-015 / BUG-031** — `search_content`, `get_nodes_by_tag`, and `GraphQuery.has_tag` use case-insensitive matching with optional `#` prefix.
- **BUG-009** — `SessionAliasRegistry.load_from_disk` skips duplicate UUID mappings instead of corrupting reverse lookup.
- **BUG-018** — `to_llamaindex_nodes` assigns distinct `SOURCE` relationships per page when roots span multiple files.
- **BUG-023** — `to_context_enriched_chunks` skips orphan registry nodes.
- **BUG-019 / BUG-020** — LENS deduplicates alias pages and resolves wikilink refs to canonical titles when a `LogseqGraph` is provided.
- **BUG-029** — `resolve_relative_page_link` supports `../` and `./` path segments.
- **BUG-030** — `resolve_asset_path` rejects absolute paths and links that escape the graph root.
- **BUG-004** — Weekly agent log files use ISO 8601 week numbers (`isocalendar`) instead of `strftime(%W)`.
- **BUG-007 / BUG-025** — `get_namespace_children` dedupes alias keys; `LogseqGraph.load_directory(strict_refs=True)` validates cross-page block refs via `raise_if_broken_references()`.
- **LIM-001** — `filename_to_page_title` preserves literal dots in titles with spaces (e.g. `Dr. Smith`).
- **LIM-002** — Empty page titles map to stable `untitled` filename stem and `untitled.md` relative path.
- **DEBT-001** — Public `LogseqGraph.page_for_node()`; SYNAPSE and KINETIC `scan` use canonical page iteration; production `assert` removed from embed expansion.

## [1.3.1] - 2026-06-19

### Changed

- **Documentation** — `examples/run_demo.py` and **`claude-skill-logseq-read/SKILL.md`** recommend **`uv sync --all-extras`** / **`uv pip install`** instead of legacy **`pip install`** hints.

## [1.3.0] - 2026-06-19

### Changed

- **Sprint 1 architectural quick wins** — **`discover_graph_files`** moved from `kinetic.py` to `logseq_paths.py` (decouples CLI from `LogseqGraph`); KINETIC optional-dependency errors now recommend **`uv sync --extra ai|viz`**; **`lens.py`** lazy-imports NetworkX/PyVis; **SYNAPSE** exports vector-store-safe metadata via **`SynapseMetadata`** / **`build_synapse_metadata`** (`task_priority`, temporal epochs, `source_uuid`, joined `path`/`refs`); explicit **`[tool.ruff]`** config in `pyproject.toml`.
- **Sprint 2 runtime robustness** — **`LogseqGraphWatcher`** debounces filesystem events (~500ms) and ignores editor temp/swap files; **`StackMachineParser(strict_refs=True)`** raises **`BlockReferenceError`** for unresolved same-page `((uuid))` refs (default off); **KINETIC** adds **`@app.callback()`** with **`--verbose`** / **`--graph`**, **`rich_markup_mode="rich"`**, and shared graph-path resolution.
- **Sprint 3 architecture** — **`LogseqGraph`** uses **`validate_assignment=True`** (no frozen/`object.__setattr__` hack); **SYNAPSE** **`LlamaIndexVisitor`** adds **`SOURCE`**, **`NEXT`**, and **`PREVIOUS`** relationships; package root **`__init__.py`** exports **`SynapseAdapter`**, **`SessionAliasRegistry`**, **`GraphVisualizer`**, and core LOGOS symbols via explicit **`__all__`**.
- **Optional AI stack** — `llama-index-core` bumped to `0.14.22` via lock refresh.
- **Documentation** — README, ARCHITECTURE, CONTRIBUTING, SECURITY, CODEQL, AST primer, and roadmaps updated for **1.3.0** (public API, watcher debounce, `strict_refs`, LlamaIndex spatial edges, `uv` install).

### Security

- **Transitive dependency hardening** — `uv` constraints pin `aiohttp>=3.14.1` (11 Dependabot alerts); `nltk` overridden to `v3.10.0-rc1` from upstream Git until NLTK 3.10.0 ships on PyPI (GHSA-p4gq-832x-fm9v). Affects optional `[ai]` / `[all]` extras only; core install unchanged.

## [1.2.2] - 2026-06-18

### Fixed

- **CodeQL CI conflict** — removed `.github/workflows/codeql.yml`; SAST runs via GitHub **CodeQL default setup** only (advanced workflow + default setup cannot coexist). See [`docs/CODEQL.md`](docs/CODEQL.md).

### Changed

- **README** — CodeQL references updated to default setup; link to `docs/CODEQL.md`.
- **Documentation** — `docs/CODEQL.md` added; CONTRIBUTING and SECURITY updated for **1.2.2**.

## [1.2.1] - 2026-06-18

### Added

- **Community health files** — `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `.github/CODEOWNERS`, and `.github/ISSUE_TEMPLATE/config.yml` for GitHub Community Standards compliance.
- **PyPI project URLs** — `Repository`, `Source`, `Documentation`, and `Changelog` links in `pyproject.toml`.
- **Coverage gate** — `pytest-cov` in the dev group; `make test` enforces `--cov-fail-under=80` with `[tool.coverage.*]` in `pyproject.toml`.
- **CodeQL workflow** — `.github/workflows/codeql.yml` for Python SAST on push/PR to `main`.
- **PyPI pre-flight** — `pypi_publish.yml` runs `make all` via `uv` before building and publishing a tag.
- **CI Python matrix** — GitHub Actions tests Python **3.12** and **3.13** in `ci.yml` and PyPI pre-flight.

### Changed

- **CI toolchain** — `.github/workflows/ci.yml` uses `astral-sh/setup-uv` and runs `uv sync --all-extras` followed by `make lint`, `make check`, and `make test` (parity with local `make all`).
- **CONTRIBUTING.md** — development setup documents `uv sync --all-extras` instead of `pip install -e .`.
- **Pre-commit** — Ruff and Mypy hook versions aligned with the `dev` dependency group in `pyproject.toml`.
- **Mypy scope** — unified to `src/`, `tests/`, and `examples/` in the Makefile, CI, CONTRIBUTING, and pre-commit.
- **CI security** — `pip-audit` on exported production requirements and `concurrency` cancel-in-progress on the same ref.
- **Version sync test** — `tests/test_package_version.py` asserts `__version__` matches `importlib.metadata.version(...)`.
- **Documentation layout** — root `ROADMAP_*.md` files consolidated under `docs/roadmaps/`.
- **README badges** — Python support badge updated to **3.12 | 3.13**; CI badge links directly to the workflow.
- **PyPI classifiers** — `Programming Language :: Python :: 3.13` added in `pyproject.toml`.

## [1.2.0] - 2026-05-29

### Added

- **Asset extraction** — `LogseqNode.assets` collects markdown images, `{{pdf}}` macros, and local `[label](path)` attachments; `resolve_asset_path` decodes percent-encoded paths (`%20`).
- **YAML frontmatter** — `---` blocks at file start populate `LogseqPage.properties` like native Logseq page properties.
- **`page-tags::`** — block and page properties named `page-tags` inject implicit graph tokens like `tags::`.

### Fixed

- **Round-trip serialization** — soft-break continuations no longer double-indent; list-shaped block properties (`tags::` + bullets) serialize as Logseq bullet lists instead of Python repr; `:LOGBOOK:` drawers and derived temporal fields (`scheduled::`, `repeater::`, …) are not emitted as bogus `key::` lines; YAML frontmatter pages round-trip with `---` fences and stable block UUIDs; `title` from YAML or `title::` frontmatter overrides the graph page title for deterministic IDs.
- **Property comma-split in wikilinks** — `tags::` / `alias::` comma separation ignores commas inside `[[...]]` tokens.
- **Properties after code fences** — `key::` lines immediately following a closing fence are parsed into block properties (Logseq contiguity exception).
- **Org warning periods** — `DEADLINE` / `SCHEDULED` payloads with `-3d`-style warning periods parse without datetime failures.
- **Quoted property values** — outer `"` / `'` are stripped from block property values in the AST.
- **Query macro shielding** — `{{query}}` / `{{advancedquery}}` inline macros do not emit false wikilink graph tokens (embed macros still do).
- **Case-insensitive page routing** — `LogseqGraph.get_page` and `resolve_relative_page_link` resolve titles via a lowercase index (Datomic / Logseq parity).
- **HTML comment shielding** — wikilinks and tags inside `<!-- ... -->` are masked before entity extraction (no ghost graph links).
- **Graph token parity** — list-shaped block properties (`tags::` with bullets) feed wikilinks/tags into the AST; page-level properties (YAML and `key::` frontmatter) merge into `page.refs`.
- **Temporal ranges and repeaters** — `SCHEDULED` / `DEADLINE` markers with `HH:MM - HH:MM` ranges parse using the start time; repeater tokens (`.+1w`, `++1d`) are stripped before datetime parsing.
- **Legacy namespace filenames** — `filename_to_page_title` decodes `___`, `%2F`, and Dendron-style `.` separators.
- **BOM-prefixed graph files** — `parse_page_file` reads with `utf-8-sig` so Windows-synced BOM bytes do not break the first bullet.
- **Markdown escape shielding** — `\#` and `\[\[` no longer yield tags or wikilinks in graph metadata.
- **Empty bullets** — bare `-` / `*` lines parse as empty blocks instead of failing `BULLET_PATTERN`.
- **Wikilink header anchors** — `[[Page#Section]]` resolves to the page name only for graph routing.
- **Hybrid alias links** — `[Alias]([[Page]])` is no longer treated as a file asset.

## [1.1.1] - 2026-05-28

### Added

- **Graph page aliases** — `LogseqGraph.load_directory` honors `title::`, `alias::` / `aliases::` for `pages` lookup and backlinks; incremental reload re-applies enrichment after watcher edits.
- **LaTeX math shielding** — `_shield_inline_code` masks `$$...$$` and `$...$` spans so wikilinks/tags inside equations are not extracted.
- **Datalog query dead zones** — `#+BEGIN_QUERY` … `#+END_QUERY` blocks are ignored for entity extraction (parse-loop state plus shielding).
- **Numbered list blocks** — `logos_parser.py` recognizes ordered-list markers (`1. `, `12. `, etc.) as outliner bullets alongside `-` and `*`.
- **Markdown task checkboxes** — `[ ]`, `[-]`, and `[x]`/`[X]` on block text map to `TODO`, `DOING`, and `DONE` before Org-mode prefix fallback.

### Fixed

- **Logseq OG parity (parser)** — `{{embed [[Page]]}}` and similar macros expose nested wikilinks; Unicode tags and markdown boundaries (`**#tag**`, `==#tag==`); comma-separated `tags::` / `alias::` / `aliases::` inject implicit graph tokens; `~~~` fences share code-block immunity with ` ``` ` fences.
- **Property contiguity** — block `key:: value` lines apply only while contiguous below the bullet; after a soft-break, later `key::` lines stay in `content` / `clean_text` (Logseq-native behavior).
- **Property bullet lists** — empty `alias::` / `tags::` followed by indented `-` bullets serialize as `list[str]` without orphan AST children.
- **Case-insensitive property keys** — all property keys normalized to lowercase at parse time; `TITLE::` frontmatter overrides graph page titles like `title::`.
- **Extended task markers** — `DELEGATED`, `POSTPONED`, `IN-PROGRESS` (longest-prefix matching) alongside existing Org-mode statuses.
- **Aliased block references** — `[Visible](((uuid)))` clean text retains visible alias only (no surrounding `[` `]`).

## [1.0.0] - 2026-05-28

### Added

- **LOGOS engine** — deterministic Stack-Machine parser (`StackMachineParser`) producing strict `LogseqPage` / `LogseqNode` ASTs from Spatial Markdown.
- **SYNAPSE adapters** — LangChain and LlamaIndex exporters with parent-child lineage metadata.
- **FORGE exporters** — JSON, Markdown, Obsidian, and enriched chunk payloads.
- **LENS visualizer** — interactive topology HTML via NetworkX / PyVis.
- **KINETIC CLI** — `matryca-parse` Typer entry point for export, visualization, and agent read/write workflows.
- **Headless CRUD** — append-only agent writer and X-Ray press utilities for sovereign graph mutation.
- **Logseq-native serialization** — round-trip page and block property layout via `logseq_markdown.py`.
- **Graph query layer** — `LogseqGraph` with backlinks, effective property inheritance, and optional filesystem watcher.
