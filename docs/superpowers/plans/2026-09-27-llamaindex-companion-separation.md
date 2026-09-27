# LlamaIndex Companion Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the LlamaIndex-to-NLTK chain from the Parser distribution while preserving framework-native LlamaIndex export through a separately maintained companion.

**Architecture:** Parser keeps the experimental `SynapseAdapter` entry point and a call-time delegation shim; it retains framework-neutral metadata and source-ID helpers but owns no LlamaIndex imports, visitor, manifest entry, or lock entry. A separate distribution owns the real LlamaIndex visitor and its own lock, audit, tests, and release evidence. Neither distribution ships until cross-repository acceptance passes.

**Tech Stack:** Python 3.12/3.13, uv 0.11.7, Hatchling, pytest, LlamaIndex core, GitHub Actions, pip-audit.

**Spec:** `docs/superpowers/specs/2026-09-27-llamaindex-companion-separation-design.md`

## Current checkpoint status — 2026-09-27

- Parser Tasks 1–4 are implemented and integrated-reviewed `PASS_WITH_NOTES`.
- Final Parser checks pass: `make all` (825 tests, 91.13% coverage), docs,
  vendor-name policy, wheel contract, sdist metadata, and an unwaived audit.
- Tasks 5–6 and cross-repository Task 7 remain gated on separate companion
  repository authority, name/range decisions, real-node tests, and acceptance.
- The integrated Parser diff is committed locally on this branch. No push, PR,
  repository creation, or publication occurred.

## Global Constraints

- Approved live base: `main@1c28aa6ceb01ada0ed8f4838ffb58903dc56f6f4`; this design worktree is `afd617046392ae14f0a2c9ce14493b3d08036b2e` before plan edits. Rebind HEAD/status before execution. GitHub API was unavailable during design review, so remote freshness beyond the verified base is unconfirmed.
- Candidate distribution/repository slug: `logseq-matryca-parser-llamaindex`; verify GitHub and PyPI name availability before creating or publishing anything. Python import module in this plan: `logseq_matryca_parser_llamaindex`.
- Keep `SynapseAdapter.to_llamaindex_nodes(nodes, *, page_title=None, page_source_id=None)` and the package-root `SynapseAdapter` export. Missing companion must produce an actionable installation command; no dictionary substitute for real LlamaIndex nodes.
- Keep `[ai]` for LangChain export; `[all]` retains visualization and LangChain dependencies only. Remove the NLTK uv constraint only after confirming no remaining Parser dependency requires it.
- Parser base, `[ai]`, `[all]`, root `uv.lock`, exported audit requirements, and built package metadata must contain neither `llama-index-core` nor `nltk`.
- Do not change AST, graph, parser, serialization, LangChain, or Logseq semantics. No adapter-wide refactor beyond imports and bridge boundary; do not replace NLTK with another NLP library.
- `PYSEC-2026-3740` remains a companion concern until an upstream fixed NLTK release is available and qualified. Remove Parser's waiver and exception test only after Parser dependency evidence is clean; never dismiss the Parser alert manually.
- Companion declares and tests a bounded compatible Parser version range. Exact range is an open maintainer gate, not a value to guess. Recheck advisory state before deciding its temporary exception.
- Parser user-facing docs and messages remain English. Existing Parser `requires-python = ">=3.12"`; CI supports Python 3.12 and 3.13. Preserve existing wheel, typing, docs, license, and release contracts.
- No work in the dirty primary checkout. Public companion repository creation, branch push, PR, and either publication each need separate explicit authorization. Parser-only green checks do not complete acceptance or authorize release.
- The integrated Parser checkpoint requires explicit maintainer authorization before local commit; bind approval to the exact branch, HEAD, and reviewed diff. No local commit, push, PR, companion repository creation, or publication without its applicable authorization.
- Every shell command starts with `rtk`. Do not run CCP heavy work without its separate exact-bound authorization; use standard public GitHub-hosted CI for the eventual public-repository gate.

## Review Focus

1. Installed companion raises `ModuleNotFoundError` for its *own* transitive dependency: shim must propagate that failure, not misreport companion as absent. Task 2 test `test_shim_does_not_mask_companion_internal_import_error`.
2. Empty node list: installed companion returns `[]` without inventing a SOURCE node. Task 5 test `test_empty_input_returns_no_nodes`.
3. Two pages with identical basenames but different full `source_path` values: SOURCE IDs remain distinct. Task 5 test `test_same_basename_different_paths_have_distinct_sources`.
4. Explicit `page_source_id` on a single page versus a mixed-page list: preserve explicit ID for the single page and current per-path SOURCE behavior for mixed pages. Task 5 test `test_explicit_source_id_preserves_single_and_mixed_page_behavior`.
5. `parent_id` or `left_id` points outside supplied list: retain forward PARENT/PREVIOUS references but do not fabricate reciprocal CHILD/NEXT links. Task 5 test `test_out_of_batch_links_do_not_create_reciprocals`.

---

## File ownership and interface map

| Owner | Files | Boundary |
|---|---|---|
| Parser dependency | `pyproject.toml`, `uv.lock`, `tests/test_dependency_boundary.py`, `scripts/check_wheel_contract.py`, `tests/test_check_wheel_contract.py` | `[ai]`/`[all]` exclude LlamaIndex; lock/export/wheel proof. |
| Parser shim | `src/logseq_matryca_parser/synapse.py`, `tests/test_synapse.py`, `tests/test_optional_import_boundary.py` | Root `__init__.py` remains unchanged; call-time import of companion function only. |
| Parser assurance | `.github/workflows/ci.yml`, `.github/workflows/pypi_publish.yml`, `tests/test_quality_gate_contract.py`, `tests/test_dependency_advisory_exception.py` | Remove only exact NLTK waiver; every other advisory remains blocking. |
| Parser guidance | `README.md`, `docs/COOKBOOK.md`, `examples/run_synapse_rag.py`, `tests/test_synapse_example.py`, `docs/reference/API_STABILITY.md`, `docs/reference/CONFORMANCE_SUPPORT_MATRIX.md`, `docs/reference/DEPENDENCY_LICENSE_POLICY.md`, `docs/security/DEPENDENCY_ADVISORY_EXCEPTIONS.md`, `docs/CI_ASSURANCE.md`, `docs/ARCHITECTURE.md`, `docs/README.md`, `docs/index.md`, `docs/log.md`, `llms.txt`, `AGENTS.md`, `CHANGELOG.md`, `RELEASE_HIGHLIGHTS.md` | Migration, current dependency claim, maintained navigation, unreleased notes; historical release sections stay historical. |
| Companion, **separate authorized repository only** | `pyproject.toml`, `uv.lock`, `src/logseq_matryca_parser_llamaindex/__init__.py`, `src/logseq_matryca_parser_llamaindex/adapter.py`, `tests/test_adapter.py`, `tests/test_distribution.py`, `.github/workflows/ci.yml`, `README.md`, `docs/security/DEPENDENCY_ADVISORY_EXCEPTIONS.md` if needed | No companion manifest, lock, source, or tests in Parser repository. |

Parser `synapse.py` keeps `build_synapse_metadata(node: LogseqNode, *, source: str, extra: dict[str, Any] | None = None) -> dict[str, Any]` and `page_source_node_id(page_title: str, source_path: str | None = None) -> str`. Companion consumes these existing helpers under its tested bounded Parser range; do not silently duplicate metadata rules. Companion produces `to_llamaindex_nodes(nodes: list[LogseqNode], *, page_title: str | None = None, page_source_id: str | None = None) -> list[TextNode]`. Parser shim preserves its existing `list[Any]` return annotation and delegates these exact arguments. Existing `LogseqNode.accept(visitor)` supplies depth-first order.

### Task 1: Parser dependency and distribution boundary

**Files:** Modify `pyproject.toml`, `uv.lock`, `scripts/check_wheel_contract.py`, `tests/test_check_wheel_contract.py`; create `tests/test_dependency_boundary.py`.

**Interfaces:** Consumes current `uv.lock` and `check_wheel(path: Path, expected_version: str) -> list[str]`; produces Parser extras, lock, export, and wheel checks used by Tasks 3 and 7.

- [x] **Step 1: Write failing dependency tests.** `test_ai_and_all_exclude_llamaindex_and_nltk` asserts `ai == ["langchain-core"]`, `all` contains only `networkx`, `pyvis`, `langchain-core`, and no NLTK constraint; `test_root_lock_has_no_llamaindex_or_nltk` asserts neither normalized package name occurs in lock packages or root optional requirements. Extend synthetic-wheel fixture with `Requires-Dist`; `test_wheel_rejects_llamaindex_or_nltk_requirement` asserts `check_wheel` reports each forbidden requirement, including an extra-marked one.
- [x] **Step 2: Confirm RED.** Run `rtk uv run pytest -q tests/test_dependency_boundary.py tests/test_check_wheel_contract.py::test_wheel_rejects_llamaindex_or_nltk_requirement`; expect failures on present declarations/lock and absent wheel rule.
- [x] **Step 3: Implement minimum change.** Remove `llama-index-core` from both extras and `nltk>=3.10.3` from uv constraints only after inspecting remaining requirements; regenerate with `rtk uv lock`. In `check_wheel`, inspect every `Requires-Dist` name case-insensitively (including extra markers), retaining existing version/PEP 561 checks. No broad dependency upgrade.
- [x] **Step 4: Confirm GREEN and exported graph.** Run `rtk uv run pytest -q tests/test_dependency_boundary.py tests/test_check_wheel_contract.py`. Use `rtk mktemp -d` to obtain a fresh per-attempt directory; export locked production requirements there with `rtk uv export --locked --no-dev --no-emit-workspace --output-file <fresh-dir>/base.txt`, then repeat with `--extra ai` and `--all-extras` into distinct files. Inspect complete requirement names, not just grep output. Build with `rtk uv build --out-dir <fresh-dir>/dist` and run `rtk uv run python scripts/check_wheel_contract.py <fresh-dir>/dist/*.whl`; all four surfaces must lack `nltk` and `llama-index-core`.
- [x] **Step 5: Review checkpoint.** Record exact diff, lock hash, and wheel/export evidence. Sol and security reviews completed; this integrated checkpoint was committed locally after explicit maintainer authorization. Push and publication remain separately gated.

### Task 2: Parser lazy compatibility shim

**Files:** Modify `src/logseq_matryca_parser/synapse.py`, `tests/test_synapse.py`; create `tests/test_optional_import_boundary.py`. Keep `src/logseq_matryca_parser/__init__.py` unchanged.

**Interfaces:** Consumes Task 5 companion function signature above. Produces unchanged `SynapseAdapter.to_llamaindex_nodes(nodes: list[LogseqNode], *, page_title: str | None = None, page_source_id: str | None = None) -> list[Any]` and existing LangChain APIs.

- [x] **Step 1: Write failing shim/import tests.** `test_shim_forwards_nodes_and_keyword_arguments` injects a fake companion through `importlib.import_module` and asserts identity/argument forwarding; `test_missing_companion_names_install_command` patches that import to raise `ModuleNotFoundError(name="logseq_matryca_parser_llamaindex")` and asserts `ImportError` includes `pip install logseq-matryca-parser-llamaindex`; `test_shim_does_not_mask_companion_internal_import_error` raises `ModuleNotFoundError(name="llama_index.core")` and asserts the original module name survives. Fresh subprocess `test_root_import_and_base_parse_do_not_import_llamaindex_or_nltk` asserts neither prefix in `sys.modules` after root import and parsing a small page; `test_langchain_and_cli_paths_do_not_import_llamaindex_or_nltk` exercises existing non-LlamaIndex paths likewise.
- [x] **Step 2: Confirm RED.** Run `rtk uv run pytest -q tests/test_synapse.py::test_shim_forwards_nodes_and_keyword_arguments tests/test_optional_import_boundary.py`; expected forwarding/import-boundary failures observed.
- [x] **Step 3: Implement minimum shim.** Delete Parser-side `llama_index.core.schema` globals, `LlamaIndexVisitor`, and native-node construction. Call `importlib.import_module("logseq_matryca_parser_llamaindex")` inside the method only. Catch `ModuleNotFoundError` only when `exc.name == "logseq_matryca_parser_llamaindex"`; raise actionable `ImportError` from that exception. Preserve `page_source_node_id`, `build_synapse_metadata`, LangChain visitor, and unrelated methods. Replace old fake-LlamaIndex tests with shim tests; do not weaken LangChain tests.
- [x] **Step 4: Confirm GREEN.** Run `rtk uv run pytest -q tests/test_synapse.py tests/test_optional_import_boundary.py tests/test_public_api_contract.py tests/test_package_version.py tests/test_kinetic.py`; root export and non-LlamaIndex paths remain unchanged.
- [x] **Step 5: Review checkpoint.** Inspect exact signature and absence of eager `llama_index` imports; integrated Sol and security reviews completed. This integrated checkpoint was committed locally after explicit maintainer authorization. Push and publication remain separately gated.

### Task 3: Parser audit without waiver

**Files:** Modify `.github/workflows/ci.yml`, `.github/workflows/pypi_publish.yml`, `tests/test_quality_gate_contract.py`, `tests/test_dependency_advisory_exception.py`.

**Interfaces:** Consumes Task 1 lock/export/wheel proof. Produces unwaived Parser production audits; does not decide companion advisory policy.

- [x] **Step 1: Write failing policy tests.** Replace NLTK-floor assertions with lock/extras absence assertions. Replace exception-presence assertions with `test_parser_audits_have_no_nltk_waiver`, requiring both workflows retain `pip-audit --no-deps --disable-pip` and exported all-extras input but contain no `--ignore-vuln PYSEC-2026-3740`; retain test that production source has no direct NLTK import.
- [x] **Step 2: Confirm RED.** Run `rtk uv run pytest -q tests/test_quality_gate_contract.py tests/test_dependency_advisory_exception.py`; expected waiver/floor failures observed.
- [x] **Step 3: Remove only NLTK waiver** and its now-stale explanatory comments from both workflows. Retire only exception-specific Parser tests; keep other security and workflow assertions. Do not make audits `warn-only` or ignore any other advisory.
- [x] **Step 4: Confirm GREEN and real audit.** Focused tests passed; locked all-extras production export audited with `rtk uv run pip-audit --no-deps --disable-pip -r <exact-export-path>` and no ignore flag. Result: `No known vulnerabilities found`. Release workflow retains the same unwaived gate.
- [x] **Step 5: Review checkpoint.** Exact audit command and result recorded; Sol and security reviews completed. This integrated checkpoint was committed locally after explicit maintainer authorization. Push and publication remain separately gated.

### Task 4: Parser migration guidance and example

**Files:** Modify Parser guidance files in ownership map and `tests/test_synapse_example.py`. No historical changelog or release-highlight entry is rewritten as though it were a current claim.

**Interfaces:** Consumes Tasks 1–3 behavior and exact companion install command. Produces docs and example that say `[ai]`/`[all]` no longer install LlamaIndex, while companion users still face the NLTK advisory.

- [x] **Step 1: Write failing example tests.** `test_synapse_rag_example_exercises_all_public_exports` injects a fake companion for Parser-only CI and retains three-output/embedded-content assertions. `test_synapse_rag_example_explains_missing_companion` asserts exit 1 and the companion install command, distinct from missing LangChain's `uv sync --extra ai` message. `test_migration_docs_distinguish_parser_and_companion` asserts README/cookbook/API matrix name the separate install and companion NLTK boundary.
- [x] **Step 2: Confirm RED.** Run `rtk uv run pytest -q tests/test_synapse_example.py` and the new documentation assertions; initial failure exposed missing-companion guidance and ambiguous extras wording.
- [x] **Step 3: Update only current guidance.** Document `pip install logseq-matryca-parser-llamaindex` (or `uv add` in uv-managed consuming projects) beside every active LlamaIndex recipe; clarify `[ai]`/`[all]` migration, real-node output, companion's still-open advisory, and Parser's clean graph. Update example's install/error text. Retire active Parser exception entry as no longer applicable, retain historical release text, and add explicit `Unreleased` migration notes. Update maintained indexes and `last_verified` fields consistently with docs governance.
- [x] **Step 4: Confirm GREEN.** Focused example tests, `make all`, `make docs-check`, and `make vendor-name-check` pass. Final `make all`: 825 passed, 91.13% coverage. Final docs wording correction passed docs-check and focused tests.
- [x] **Step 5: Review checkpoint.** Compare current recipes/indexes to migration contract and preserve historical entries. Integrated Sol review is `PASS_WITH_NOTES` after correcting extras wording; security review is `PASS_WITH_NOTES`. This integrated checkpoint was committed locally after explicit maintainer authorization. Push and publication remain separately gated.

### Task 5: Companion native adapter — **pause until separate repository authority**

**Files, in the separate companion repository only:** Create `src/logseq_matryca_parser_llamaindex/__init__.py`, `src/logseq_matryca_parser_llamaindex/adapter.py`, `tests/test_adapter.py`.

**Interfaces:** Consumes `LogseqNode`, `ASTVisitor`, `build_synapse_metadata`, `page_source_node_id` from Parser's tested compatible range; produces `to_llamaindex_nodes(...) -> list[llama_index.core.schema.TextNode]` for Task 2 shim. Neither Parser repository nor Parser lock may contain companion files.

- [ ] **Step 1: Write failing tests with real LlamaIndex types.** `test_native_nodes_preserve_metadata_order_and_topology` asserts `isinstance(item, TextNode)`, `id_ == node.uuid`, `text == clean_text`, all existing metadata/property values, depth-first order, SOURCE, PARENT, CHILD, PREVIOUS, and NEXT. Add the four Task 5 Review Focus tests named above: `test_empty_input_returns_no_nodes` asserts `[]`; `test_same_basename_different_paths_have_distinct_sources` asserts distinct deterministic SOURCE IDs; `test_explicit_source_id_preserves_single_and_mixed_page_behavior` asserts explicit ID for single page and per-path IDs for mixed pages; `test_out_of_batch_links_do_not_create_reciprocals` asserts forward links only. Reuse current Parser fixture semantics, not fake schema objects.
- [ ] **Step 2: Confirm RED.** Run `rtk uv run pytest -q tests/test_adapter.py`; expect import/function failures before implementation.
- [ ] **Step 3: Move native construction and `LlamaIndexVisitor` logic** into `adapter.py`; export the named function from `__init__.py`. Preserve existing `source_path`-based source selection and relationship rules. Use shared Parser metadata/source-ID helpers; do not add NLP, network, or vault I/O.
- [ ] **Step 4: Confirm GREEN.** Run `rtk uv run pytest -q tests/test_adapter.py` in companion environment with real `llama-index-core`, and an installed-distribution test that imports Parser first, then calls its shim and verifies returned real `TextNode` objects.
- [ ] **Step 5: Review checkpoint.** Compare node outputs with pre-migration fixtures on exact same AST, including ID, metadata, order, and each relationship; commit only after exact maintainer authorization.

### Task 6: Companion package, audit, and compatibility range — **same authority gate**

**Files, in the separate companion repository only:** Create `pyproject.toml`, `uv.lock`, `tests/test_distribution.py`, `.github/workflows/ci.yml`, `README.md`; create `docs/security/DEPENDENCY_ADVISORY_EXCEPTIONS.md` only if live advisory review requires a temporary exception.

**Interfaces:** Consumes Task 5 adapter and maintainer-approved Parser version range; produces wheel metadata with bounded `logseq-matryca-parser` and `llama-index-core` requirements, own test/audit receipts. Candidate distribution name remains subject to live availability checks.

- [ ] **Step 1: Stop for gates.** Verify GitHub/PyPI candidate names and select an exact lower and exclusive upper Parser compatibility bound from tested releases; obtain maintainer approval before creating public repo or finalizing manifest. A local staging directory is not authorization to create/publish a public repository.
- [ ] **Step 2: Write failing package tests.** `test_companion_metadata_has_bounded_parser_range` inspects built wheel `Requires-Dist`; `test_parser_minimum_and_upper_boundary` installs/tests the approved minimum and highest supported Parser versions and verifies an incompatible version is rejected. `test_importing_parser_alone_does_not_load_companion` checks a fresh subprocess.
- [ ] **Step 3: Add minimal package/lock/CI.** Dependency set is bounded Parser plus `llama-index-core`, with Python 3.12/3.13 checks. Companion CI runs locked tests, wheel metadata, and its own exported production `pip-audit`. Recheck `PYSEC-2026-3740` immediately before policy: if still open, add an exact, owner/expiry-scoped companion exception and no broader ignore; if fixed, qualify the fixed release instead. Do not claim NLTK fixed because Parser no longer resolves it.
- [ ] **Step 4: Confirm GREEN or explicit security block.** Run `rtk uv sync --locked`, `rtk uv run pytest -q`, `rtk uv build`, inspect wheel metadata, and audit exact export. A still-open advisory with no approved exception is BLOCKED, not PASS. Verify license/lock and package provenance under companion repository policy before release.
- [ ] **Step 5: Review checkpoint.** Preserve exact companion HEAD, lock hash, tested Parser range, advisory state, and CI evidence; commit/push/publish only under each separate authorization.

### Task 7: Cross-repository acceptance and release gate

**Files:** No new code by default; correct the owning task if evidence exposes a defect. Release notes are already Task 4 files.

**Interfaces:** Consumes Tasks 1–6 and their exact commits/artifacts; produces an acceptance record, not publication authority.

- [ ] **Step 1: Rebind exact state.** Record both repository HEADs, dirty state, locks, distribution names, version range, wheel hashes, and advisory status. If companion repository was not authorized or its tests do not exist, stop with Parser-only partial result.
- [ ] **Step 2: Run Parser gate** on clean exact candidate: `rtk uv sync --locked --all-extras`, `rtk make all`, `rtk make vendor-name-check`, locked base/`ai`/`all` exports, unwaived CI-equivalent audit, wheel/sdist contract, and clean-environment import/CLI checks. Collect hosted Python 3.12/3.13 and platform CI receipts before claiming full release qualification.
- [ ] **Step 3: Run companion gate** against built Parser wheel within approved version range: real-node tests, exact package-contract and dependency audit, and current NLTK-advisory decision. Verify Parser wheel metadata has no companion/LlamaIndex/NLTK requirement; companion metadata has the bounded Parser requirement.
- [ ] **Step 4: Review migration and security claims.** Show clean Parser graph separately from companion's advisory; verify no manual alert dismissal and no silent patch release. Any failed or unavailable gate remains failed/unknown, never inferred from local PASS.
- [ ] **Step 5: Stop for external actions.** Maintainer reviews exact evidence and migration notes. Public companion repository creation (if still pending), branch push, PR, Parser release, companion release, and publication each require separate explicit authorization; follow existing release process only after those gates.
