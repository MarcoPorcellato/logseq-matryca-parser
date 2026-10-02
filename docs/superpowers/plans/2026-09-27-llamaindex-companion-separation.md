# LlamaIndex Companion Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the LlamaIndex-to-NLTK chain from the Parser distribution while preserving framework-native LlamaIndex export through a separately maintained companion.

**Architecture:** Parser keeps the experimental `SynapseAdapter` entry point and a call-time delegation shim; it retains framework-neutral metadata and source-ID helpers but owns no LlamaIndex imports, visitor, manifest entry, or lock entry. A separate distribution owns the real LlamaIndex visitor and its own lock, audit, tests, and release evidence. Parser and companion have distinct release gates: prequalify the companion against the exact candidate Parser wheel, independently qualify and authorize Parser 1.10.0, then complete registry-installed companion acceptance before any companion release.

**Tech Stack:** Python 3.12/3.13, uv 0.11.7, Hatchling, pytest, LlamaIndex core, GitHub Actions, pip-audit.

**Spec:** `docs/superpowers/specs/2026-09-27-llamaindex-companion-separation-design.md`

## Historical checkpoint status — 2026-09-27

> This section records the state at the 2026-09-27 checkpoint. Its pending
> release and PR statements are historical; the current status refresh at the
> end records later evidence.

- Parser Tasks 1–4 are implemented at `1d11d97e1806b534a74a82585fc1aec54e56a4fa`
  on `design/nltk-llamaindex-companion`; Sol's integrated review is
  `PASS_WITH_NOTES`. The candidate package version is 1.10.0. `make all`
  passes (825 tests, 91.13% coverage); the dependency boundary, wheel/sdist
  contract, unwaived audit, docs, and vendor-name checks pass on this local
  source state.
- Tasks 5–6 have a **companion implementation checkpoint** in
  [draft PR #1](https://github.com/MarcoPorcellato/logseq-matryca-parser-llamaindex/pull/1),
  branch `feat/native-llamaindex-adapter`, implementation evidence at
  `bcf7576caa99cf884280cffdb05238358b6be2f3` and draft-PR head
  `14fd8de399d5abd38c70e52125e81da8dda5c5b2`. The companion has real
  LlamaIndex `TextNode` construction, package metadata, tests, README, and an
  exact Apache-2.0 license copy. Its initial Parser range is provisionally
  bounded to `>=1.10.0,<1.11.0`; `llama-index-core` is bounded to
  `>=0.14.22,<0.15`.
- Local companion verification: 8 tests pass; wheel and sdist build; Ruff
  passes on a clean clone; bounded wheel metadata and packaged license were
  checked. Sol review of the local slice is `PASS_WITH_NOTES`; security review
  of local code is `PASS_WITH_NOTES`. These are not release gates.
- Candidate-wheel prequalification passed on Python 3.12.13: exact Parser and
  companion wheels resolved together with 71 consistent distributions;
  installed-only native-node, topology, source-ID, and shim assertions passed.
  Wheel hashes and limits are recorded in the public checkpoint. This is not
  registry compatibility or companion security qualification.
- Companion Task 6 release qualification and the post-Parser-publication part
  of Task 7 remain **BLOCKED**: Parser 1.10.0 is not published, so
  registry-resolved minimum/upper-bound testing and a portable lock are not yet
  possible; hosted Python 3.12/3.13 CI, production export audit,
  installed-release acceptance, and an advisory disposition remain
  unqualified. Exact candidate-wheel prequalification can proceed before that
  publication. Security review marks companion release `BLOCKED`.
- The exact public GitHub companion repository was created after explicit
  authorization. Its bootstrap and feature branches were pushed; at this
  checkpoint companion PR #1 and Parser PR #225 were both drafts. No merge or
  package publication had occurred. See
  [`docs/internal/LLAMAINDEX_COMPANION_MIGRATION_CHECKPOINT_2026-09-27.md`](../../internal/LLAMAINDEX_COMPANION_MIGRATION_CHECKPOINT_2026-09-27.md)
  for restart facts and stop boundaries.

## Global Constraints

- Design began from `main@1c28aa6ceb01ada0ed8f4838ffb58903dc56f6f4`. Parser code was qualified at `1d11d97e1806b534a74a82585fc1aec54e56a4fa`; later documentation commits exist, so rebind HEAD/status before resuming. Live Parser `main` was read as `fc2af61221ed2b8eb1026082987938a996b2d73f` during the companion investigation; this is a historical observation, not a current remote guarantee.
- Public repository slug: `logseq-matryca-parser-llamaindex`, now created on GitHub. The package distribution name remains a candidate until PyPI availability and publication gates are verified. Python import module in this plan: `logseq_matryca_parser_llamaindex`.
- Keep `SynapseAdapter.to_llamaindex_nodes(nodes, *, page_title=None, page_source_id=None)` and the package-root `SynapseAdapter` export. Missing companion must produce an actionable installation command; no dictionary substitute for real LlamaIndex nodes.
- Keep `[ai]` for LangChain export; `[all]` retains visualization and LangChain dependencies only. Remove the NLTK uv constraint only after confirming no remaining Parser dependency requires it.
- Parser base, `[ai]`, `[all]`, root `uv.lock`, exported audit requirements, and built package metadata must contain neither `llama-index-core` nor `nltk`.
- Do not change AST, graph, parser, serialization, LangChain, or Logseq semantics. No adapter-wide refactor beyond imports and bridge boundary; do not replace NLTK with another NLP library.
- `PYSEC-2026-3740` remains a companion concern until an upstream fixed NLTK release is available and qualified. Remove Parser's waiver and exception test only after Parser dependency evidence is clean; never dismiss the Parser alert manually.
- Companion's local manifest currently declares `logseq-matryca-parser>=1.10.0,<1.11.0` and `llama-index-core>=0.14.22,<0.15`. The former avoids the invalid 1.9.0 lower bound because released Parser 1.9.0 still includes the old adapter; it is a provisional compatibility window, not yet release-qualified. Do not widen the upper bound without testing each newly supported Parser minor. Recheck the advisory before any exception or release decision.
- Parser user-facing docs and messages remain English. Existing Parser `requires-python = ">=3.12"`; CI supports Python 3.12 and 3.13. Preserve existing wheel, typing, docs, license, and release contracts.
- No work in the dirty primary checkout. Public repository creation, branch pushes, and draft PRs are complete. Merge and either publication remain separate authorization gates. Parser-only or local-companion green checks do not complete acceptance or authorize release.
- At this checkpoint, Parser implementation and checkpoint commits were on the isolated branch. Reverify exact branch, HEAD, and diff before continuing. Parser PR #225 and companion PR #1 were drafts pending cross-repository qualification.
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

### Task 5: Companion native adapter — **local implementation checkpoint; publication blocked**

**Files, in the separate companion repository only:** `src/logseq_matryca_parser_llamaindex/__init__.py`, `src/logseq_matryca_parser_llamaindex/adapter.py`, `tests/test_adapter.py`. The companion checkout and public draft PR #1 exist at the locations recorded in the current checkpoint.

**Interfaces:** Consumes `LogseqNode`, `ASTVisitor`, `build_synapse_metadata`, `page_source_node_id` from Parser's tested compatible range; produces `to_llamaindex_nodes(...) -> list[llama_index.core.schema.TextNode]` for Task 2 shim. Neither Parser repository nor Parser lock may contain companion files.

- [x] **Step 1: Write failing tests with real LlamaIndex types.** Native node type, IDs, text, metadata, depth-first order and relationship tests were written against real `TextNode` / `NodeRelationship` types, including empty input, same-basename paths, explicit/mixed source IDs, and out-of-batch links.
- [x] **Step 2: Confirm RED.** Initial tests failed before the implementation was added.
- [x] **Step 3: Move native construction and `LlamaIndexVisitor` logic** into the local companion adapter, preserving Parser metadata/source-ID helpers and topology rules.
- [x] **Step 4: Confirm local GREEN.** Six adapter tests passed; package-stage evidence later added two distribution/import-boundary tests (8 total). Local source-to-source shim and built-wheel smoke evidence are recorded in the checkpoint. This does not equal registry-installed minimum-version acceptance.
- [x] **Step 5: Review checkpoint.** Sol review of the local slice is `PASS_WITH_NOTES`; four parity scenarios were recorded. Broader installed-release acceptance and the exact supported-version matrix remain pending Task 6.

### Task 6: Companion package, audit, and compatibility range — **local package checkpoint; release BLOCKED**

**Files, in the separate companion repository only:** Local checkout contains `pyproject.toml`, `tests/test_distribution.py`, `README.md`, and exact Apache-2.0 `LICENSE`. A portable `uv.lock`, hosted workflow, and advisory exception have intentionally not been added.

**Interfaces:** Consumes Task 5 adapter and the provisional Parser version range recorded above; produces wheel metadata with bounded `logseq-matryca-parser` and `llama-index-core` requirements. The range is not release-approved until real registry endpoints are tested; companion audit receipts remain absent. Candidate distribution name remains subject to live availability checks.

- [x] **Step 1: Select provisional package bounds.** The local manifest uses Parser `>=1.10.0,<1.11.0` and `llama-index-core>=0.14.22,<0.15`; 1.10.0 is not yet registry-available, so the Parser window is intentionally provisional and unqualified. The former suggested `>=1.9.0` lower bound was incorrect because released 1.9.0 still carries the old adapter.
- [x] **Step 2: Write pre-release package-contract tests.** Wheel metadata tests assert bounded Parser/LlamaIndex requirements; a subprocess test verifies Parser import does not load the companion. Existing adapter tests cover real LlamaIndex types. Minimum/upper-bound registry install tests remain blocked until the Parser 1.10.0 artifact and next supported boundary are available.
- [x] **Step 3: Add minimal local metadata and documentation.** Python `>=3.12`, version `0.1.0`, Apache-2.0 license copied byte-for-byte from Parser, package metadata, consumer-data disclosure, and readiness gates are present. No `uv.lock`, hosted CI, or advisory waiver was added because those would falsely claim registry-resolved/release-qualified inputs.
- [x] **Step 4: Confirm local package evidence and record release block.** On clean local clone at companion HEAD `bcf7576caa99cf884280cffdb05238358b6be2f3`, `uv build --offline` succeeded; 8 tests passed; Ruff `0.15.12` passed on `tests/test_distribution.py`; wheel metadata and packaged license were verified. Full-tree Ruff passed after review. This is local evidence only. Parser 1.10.0 registry tests, portable lock, hosted Python 3.12/3.13 CI, production export audit and advisory disposition remain **BLOCKED**.
- [x] **Step 5: Review checkpoint.** Sol and security review of the local code are each `PASS_WITH_NOTES`; release remains `BLOCKED`. LlamaIndex 0.14.22 resolves NLTK 3.10.3. GitHub advisory says affected `<=3.10.3` with no fixed release; PyPA advisory prose and machine range conflict. Do not add an exception, claim a fix, or release until the authoritative advisory state is reconciled and an accepted security disposition exists.

### Task 7: Cross-repository acceptance and release gate

**Files:** No new code by default; correct the owning task if evidence exposes a defect. Release notes are already Task 4 files.

**Interfaces:** Prequalification consumes completed Parser Tasks 1–4 and local companion Tasks 5–6 artifacts. Post-Parser-publication acceptance additionally consumes companion Task 6 release evidence. Both stages produce evidence, not publication authority.

- [ ] **Step 1: Rebind exact state.** Record Parser and companion HEADs, dirty state, locks, distribution names, version range, wheel hashes, advisory status, and draft PR states. If the companion implementation or its required evidence is absent, stop with Parser-only partial result. A public GitHub repository exists, but its presence alone does not qualify either distribution.
- [ ] **Step 2: Run Parser gate** on clean exact candidate: `rtk uv sync --locked --all-extras`, `rtk make all`, `rtk make vendor-name-check`, locked base/`ai`/`all` exports, unwaived CI-equivalent audit, wheel/sdist contract, and clean-environment import/CLI checks. Collect hosted Python 3.12/3.13 and platform CI receipts before claiming full release qualification.
- [ ] **Step 3: Prequalify companion against the exact candidate Parser wheel.** Run real-node, shim, and wheel-metadata checks with explicit artifact hashes. A local `--no-deps` install is smoke evidence, not registry resolution or complete compatibility proof. Keep NLTK advisory status separate from Parser's clean graph.
- [x] **Step 4: Decide Parser integration and release independently.** Parser PR #225 merged on 2026-09-27 at `870a35eb8014c030aaa874e8f1ce550556e0decb`; tag `v1.10.0` was published on 2026-09-28 and resolves to `4966144b5cd3e95ce36d38c8c1a9823a6ecab056`. This closes the Parser release gate only; it does not qualify the companion.
- [ ] **Step 5: Qualify the registry-installed companion after Parser publication.** Install actual Parser 1.10.0 distribution, verify the supported lower bound and `<1.11.0` exclusion, generate a portable companion lock, run hosted Python 3.12/3.13 CI and the exact production export audit, and repeat installed-release shim/native-node acceptance. Reconcile the NLTK advisory or obtain a separately approved, narrow, time-bound exception before considering companion release.
- [ ] **Step 6: Stop before companion merge and publication.** Companion PR #1 remains draft until its hosted and security gates pass. Review exact evidence; companion PR merge and package publication each require a separate maintainer decision. No local or hosted PASS implicitly authorizes either.

## Current status refresh — 2026-10-02

The 2026-09-27 checkpoint above remains historical evidence. Current verified
state: Parser v1.10.0 is the latest PyPI/GitHub release; Parser PR #225 and Org
parser PR #229 have merged. Parser `main` was observed at
`8c07b2e9235852fcbf9aac16bce5ff13bcc82534`. The companion distribution is not
published (PyPI returned HTTP 404), and companion PR #1 remains open/draft at
`e6824c3e50aeac942b01a9aa3f2bbed1663b1230`. The companion's provisional
`>=1.10.0,<1.11.0` Parser range is now resolvable at its lower bound but remains
unqualified; do not widen it to include a future Parser 1.11.0 without new
compatibility evidence. Parser v1.11.0 is in release preparation, not yet
published, and does not alter the companion's state or authorization gates.
