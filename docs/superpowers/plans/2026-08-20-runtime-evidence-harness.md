# Runtime Evidence Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project-owned, test-only, source-free runtime-evidence harness for issue #111 that produces reproducible local observations without adding a public API or CI timing gate.

**Architecture:** The harness lives entirely below `tests/performance/`. A deterministic synthetic-vault generator owns the fixed input and aggregate source fingerprint; a pure measurement model owns sampling, statistics, receipt shaping, and source-free validation; a runner materializes only temporary synthetic files and executes the five semantic scenarios. A maintained reference document explains replay and noise handling but makes no portability or release-performance claim.

**Tech Stack:** Python 3.12+, `pytest`, standard library (`argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `statistics`-free rank calculation, `tempfile`, `time`), existing `StackMachineParser`, `LogseqGraph`, and optional `SynapseAdapter`.

**Spec:** `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md` (M8 — Reproducible measured-runtime evidence, issue #111)

## Global Constraints

- Create all production-free implementation under `tests/performance/`; do not change `src/`, package exports, CLI entry points, dependencies, build metadata, or normal CI timing thresholds.
- Generate only an original deterministic synthetic vault: 96 pages, 24 blocks per ordinary page, cross-page links, aliases, tags, and one 1024-level deep-chain page. Never accept a caller-supplied vault path.
- Default execution emits exactly one JSON receipt to stdout and persists no receipt. Temporary synthetic files may exist only inside a `TemporaryDirectory` during a scenario.
- Receipts must omit generated Markdown, paths, page titles, UUIDs, host names, and exception text. They may retain aggregate counts, SHA-256 fingerprints, fixed scenario identifiers, fixed availability codes, Python version, platform system/machine, and replay command.
- Each available scenario runs exactly 3 warm-ups and 21 measured samples with `time.perf_counter_ns`; median and p95 are reported in nanoseconds. p95 is the sorted sample at `ceil(0.95 * n) - 1`.
- A scenario sample is valid only when its semantic assertion succeeds. The optional SYNAPSE scenario is `unavailable` with the fixed reason `optional_adapter_unavailable` if LangChain is not importable; it is never a pass or skip in that state.
- RSS is a labelled native high-water observation, with `bytes` on Darwin, `KiB` on supported Unix, or explicit `unavailable`; it is not normalized or compared across machines.
- Use the existing #87 tree-invariant helpers and the #103 incremental-versus-cold backlink equivalence pattern. Do not copy external code, corpus, schemas, control flow, or documentation.
- Run fresh impact analysis and verify zero source import cycles before any later edit of protected parser/graph hubs. This plan itself does not modify them.
- Keep all documentation and emitted operator messages in English. Do not include private-vault content, credentials, tool caches, or generated receipts in commits.

---

## File structure

| Path | Responsibility |
|---|---|
| `tests/performance/__init__.py` | Marks the private harness as a runnable test package; exports nothing. |
| `tests/performance/synthetic_vault.py` | Fixed original vault schema, deterministic Markdown bytes, aggregate fingerprint, and temporary materialization helper. |
| `tests/performance/runtime_evidence.py` | Scenario names, availability/result/receipt dataclasses, deterministic percentile calculation, source-free receipt serialization, semantic scenario functions, and `python -m` entry point. |
| `tests/test_performance_synthetic_vault.py` | Generator cardinality, determinism, bounds, materialization, and no-private-input tests. |
| `tests/test_runtime_evidence.py` | Sampling protocol, statistics, source-free receipt schema, semantic gates, optional-adapter classification, and stdout-only CLI tests. |
| `docs/reference/PERFORMANCE_EVIDENCE.md` | Maintained operator contract, replay command, receipt interpretation, and noise policy. |
| `docs/index.md` | Adds the maintained performance-evidence entry point. |
| `docs/maintained.toml` | Adds the new maintained reference document to the documentation checker. |
| `docs/log.md` | Records the source-level documentation evolution without inventing a measured performance result. |

## Task 1: Deterministic synthetic vault

**Files:**

- Create: `tests/performance/__init__.py`
- Create: `tests/performance/synthetic_vault.py`
- Create: `tests/test_performance_synthetic_vault.py`

**Interfaces:**

- Consumes: standard-library `Path`, `TemporaryDirectory` callers, and no repository runtime API.
- Produces: `SyntheticVault`, `build_synthetic_vault()`, `PAGE_COUNT`, `BLOCKS_PER_PAGE`, `DEEP_CHAIN_DEPTH`, and `SYNTHETIC_VAULT_SCHEMA_VERSION` for the runner.

- [ ] **Step 1: Write failing generator-contract tests**

```python
from tests.performance.synthetic_vault import (
    BLOCKS_PER_PAGE,
    DEEP_CHAIN_DEPTH,
    PAGE_COUNT,
    build_synthetic_vault,
)


def test_synthetic_vault_has_the_fixed_original_shape() -> None:
    vault = build_synthetic_vault()

    assert vault.page_count == PAGE_COUNT == 96
    assert vault.blocks_per_page == BLOCKS_PER_PAGE == 24
    assert vault.deep_chain_depth == DEEP_CHAIN_DEPTH == 1024
    assert len(vault.files) == PAGE_COUNT
    assert vault.total_source_bytes > 0


def test_synthetic_vault_is_deterministic_and_materializes_only_under_destination(tmp_path: Path) -> None:
    first = build_synthetic_vault()
    second = build_synthetic_vault()
    destination = tmp_path / "synthetic"

    first.materialize(destination)

    assert first.source_sha256 == second.source_sha256
    assert sorted(path.relative_to(destination) for path in destination.rglob("*.md"))
    assert all(path.is_relative_to(destination) for path in destination.rglob("*.md"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk .venv/bin/python -m pytest tests/test_performance_synthetic_vault.py -q`

Expected: FAIL during collection because `tests.performance.synthetic_vault` does not exist.

- [ ] **Step 3: Implement the fixed generator and bounded materializer**

```python
SYNTHETIC_VAULT_SCHEMA_VERSION: Final = 1
PAGE_COUNT: Final = 96
BLOCKS_PER_PAGE: Final = 24
DEEP_CHAIN_DEPTH: Final = 1024


@dataclass(frozen=True)
class SyntheticVault:
    files: tuple[tuple[PurePosixPath, bytes], ...]
    page_count: int
    blocks_per_page: int
    deep_chain_depth: int

    @property
    def total_source_bytes(self) -> int:
        return sum(len(content) for _, content in self.files)

    @property
    def deep_chain_source(self) -> str:
        return next(
            content.decode("utf-8")
            for relative_path, content in self.files
            if relative_path == PurePosixPath("pages/runtime-evidence-deep.md")
        )

    @property
    def source_sha256(self) -> str:
        digest = hashlib.sha256()
        for relative_path, content in self.files:
            digest.update(relative_path.as_posix().encode("utf-8"))
            digest.update(b"\\0")
            digest.update(content)
            digest.update(b"\\0")
        return digest.hexdigest()

    def materialize(self, destination: Path) -> Path:
        root = destination.resolve()
        for relative_path, content in self.files:
            target = (root / relative_path).resolve()
            try:
                target.relative_to(root)
            except ValueError as error:
                raise ValueError("synthetic vault path escapes destination") from error
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return root
```

Generate 95 ordinary `pages/` files and one deep-chain `pages/` file. Each ordinary page must contain exactly 24 blocks, one fixed tag, one alias, and a deterministic link to the next page. Build the deep source from `DEEP_CHAIN_DEPTH` two-space-indented outline lines. Sort paths before freezing `files`; do not place generated labels in any public receipt.

- [ ] **Step 4: Add exact boundary tests**

```python
def test_synthetic_vault_has_no_external_input_parameter() -> None:
    assert inspect.signature(build_synthetic_vault).parameters == {}


def test_synthetic_vault_rejects_materialization_escape(tmp_path: Path) -> None:
    vault = SyntheticVault(
        files=((PurePosixPath("../escape.md"), b"- prohibited\\n"),),
        page_count=1,
        blocks_per_page=1,
        deep_chain_depth=1,
    )

    with pytest.raises(ValueError):
        vault.materialize(tmp_path / "root")
```

Raise `ValueError("synthetic vault path escapes destination")` when a resolved target is outside the resolved destination. The public fixed builder must never generate this condition.

- [ ] **Step 5: Run the focused tests to verify they pass**

Run: `rtk .venv/bin/python -m pytest tests/test_performance_synthetic_vault.py -q`

Expected: PASS. The source fingerprint is identical across two builds, exactly 96 Markdown files materialize below the destination, and the escape test fails closed.

- [ ] **Step 6: Commit the self-contained generator slice**

```bash
rtk git add tests/performance/__init__.py tests/performance/synthetic_vault.py tests/test_performance_synthetic_vault.py
rtk git commit -m "test: add deterministic runtime evidence vault"
```

## Task 2: Source-free measurement model and receipt schema

**Files:**

- Create: `tests/performance/runtime_evidence.py`
- Create: `tests/test_runtime_evidence.py`

**Interfaces:**

- Consumes: `SyntheticVault` and its aggregate properties from Task 1.
- Produces: `ScenarioName`, `ScenarioAvailability`, `ScenarioReceipt`, `RuntimeEvidenceReceipt`, `build_runtime_receipt()`, `measure_scenario()`, `percentile_p95_ns()`, and `resident_high_water_observation()` for Task 3.

- [ ] **Step 1: Write failing pure-model tests**

```python
def test_p95_uses_the_declared_nearest_rank_rule() -> None:
    assert percentile_p95_ns(tuple(range(1, 22))) == 20


def test_measurement_protocol_uses_three_warmups_and_twenty_one_samples() -> None:
    calls = 0

    def semantic_action() -> None:
        nonlocal calls
        calls += 1

    receipt = measure_scenario("cold_graph_load", semantic_action, clock_ns=lambda: calls * 10)

    assert calls == 24
    assert receipt.warmup_count == 3
    assert receipt.sample_count == 21
    assert receipt.availability == "available"
    assert receipt.semantic_gate_passed is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk .venv/bin/python -m pytest tests/test_runtime_evidence.py -q`

Expected: FAIL during collection because `tests.performance.runtime_evidence` does not exist.

- [ ] **Step 3: Implement immutable receipts and deterministic statistics**

```python
WARMUP_COUNT: Final = 3
SAMPLE_COUNT: Final = 21
RUNTIME_EVIDENCE_SCHEMA_VERSION: Final = 1
RUNTIME_EVIDENCE_HARNESS_VERSION: Final = 1

ScenarioName = Literal[
    "deep_parse_1024",
    "cold_graph_load",
    "incremental_alias_move_reload",
    "search_content",
    "synapse_context_chunks",
]
ScenarioAvailability = Literal["available", "unavailable", "invalid"]


@dataclass(frozen=True)
class ScenarioReceipt:
    scenario: ScenarioName
    availability: ScenarioAvailability
    unavailable_reason: Literal["optional_adapter_unavailable"] | None
    semantic_gate_passed: bool
    warmup_count: int
    sample_count: int
    median_duration_ns: int | None
    p95_duration_ns: int | None


@dataclass(frozen=True)
class RuntimeEvidenceReceipt:
    runtime_evidence_schema_version: int
    runtime_evidence_harness_version: int
    synthetic_vault_schema_version: int
    source_sha256: str
    aggregate_counts: dict[str, int]
    python_version: str
    platform_system: str
    platform_machine: str
    replay_command: str
    resident_high_water: dict[str, int | str]
    scenarios: tuple[ScenarioReceipt, ...]

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


def percentile_p95_ns(samples: tuple[int, ...]) -> int:
    if not samples:
        raise ValueError("p95 requires at least one sample")
    return sorted(samples)[math.ceil(0.95 * len(samples)) - 1]


def median_ns(samples: tuple[int, ...]) -> int:
    if len(samples) % 2 != 1:
        raise ValueError("runtime evidence requires an odd sample count")
    return sorted(samples)[len(samples) // 2]
```

`measure_scenario()` must call the supplied no-argument action three times before capturing any duration and 21 times inside `started = clock_ns(); action(); elapsed = clock_ns() - started`. Reject negative elapsed values. Use `median_ns()` and `percentile_p95_ns()` for available samples. If any action raises or fails its semantic assertion, return `availability="invalid"`, `semantic_gate_passed=False`, and all duration fields as `None`; store neither the exception nor its text.

- [ ] **Step 4: Write receipt privacy and platform-observation tests**

```python
def test_receipt_payload_is_source_free() -> None:
    vault = build_synthetic_vault()
    scenario = ScenarioReceipt(
        scenario="cold_graph_load",
        availability="available",
        unavailable_reason=None,
        semantic_gate_passed=True,
        warmup_count=3,
        sample_count=21,
        median_duration_ns=10,
        p95_duration_ns=20,
    )
    receipt = build_runtime_receipt(vault, (scenario,))
    payload = receipt.to_payload()

    assert payload["source_sha256"] == vault.source_sha256
    rendered = json.dumps(payload, sort_keys=True)
    assert "source" not in {key for key in payload if key != "source_sha256"}
    assert vault.files[0][0].name not in rendered
    assert vault.files[0][1].decode("utf-8") not in rendered
    assert "path" not in rendered.casefold()
    assert "exception" not in rendered.casefold()
    assert "host" not in rendered.casefold()


def test_missing_native_rss_is_explicitly_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_evidence, "resource", None)
    assert resident_high_water_observation() == {"availability": "unavailable"}
```

The outer receipt must include only: schema/harness/generator versions, source hash, aggregate page/block/deep-depth/byte counts, Python version, platform system/machine, a fixed replay command, RSS observation, and scenario receipts. Its `to_payload()` must not expose a `samples` field, raw source, generated filename, page title, UUID, exception, current working directory, or host name.

- [ ] **Step 5: Run the focused model tests to verify they pass**

Run: `rtk .venv/bin/python -m pytest tests/test_runtime_evidence.py -q`

Expected: PASS. Tests prove the exact 3+21 protocol, nearest-rank p95, invalid semantic handling without exception disclosure, optional RSS availability, and source-free serialization.

- [ ] **Step 6: Commit the pure measurement slice**

```bash
rtk git add tests/performance/runtime_evidence.py tests/test_runtime_evidence.py
rtk git commit -m "test: add source-free runtime receipt model"
```

## Task 3: Semantic scenario runner and stdout-only replay interface

**Files:**

- Modify: `tests/performance/runtime_evidence.py`
- Modify: `tests/test_runtime_evidence.py`

**Interfaces:**

- Consumes: `build_synthetic_vault()`, `SyntheticVault.materialize()`, `measure_scenario()`, `RuntimeEvidenceReceipt`, `StackMachineParser`, `LogseqGraph`, `SynapseAdapter`, and `assert_tree_invariants()`.
- Produces: `run_runtime_evidence() -> RuntimeEvidenceReceipt` and `main(argv: Sequence[str] | None = None) -> int`; both are private test-harness surfaces, not package APIs.

- [ ] **Step 1: Write failing semantic-scenario tests**

```python
def test_all_core_scenarios_are_semantically_valid() -> None:
    receipt = run_runtime_evidence()
    by_name = {scenario.scenario: scenario for scenario in receipt.scenarios}

    assert set(by_name) == {
        "deep_parse_1024",
        "cold_graph_load",
        "incremental_alias_move_reload",
        "search_content",
        "synapse_context_chunks",
    }
    for name in by_name:
        if name != "synapse_context_chunks":
            assert by_name[name].availability == "available"
            assert by_name[name].semantic_gate_passed is True


def test_optional_synapse_is_unavailable_not_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_evidence.synapse_module, "Document", None)

    scenario = runtime_evidence.run_synapse_context_chunks()

    assert scenario.availability == "unavailable"
    assert scenario.unavailable_reason == "optional_adapter_unavailable"
    assert scenario.semantic_gate_passed is False
    assert scenario.sample_count == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `rtk .venv/bin/python -m pytest tests/test_runtime_evidence.py -q`

Expected: FAIL because the scenario functions and runner do not yet exist.

- [ ] **Step 3: Implement the five semantic actions**

```python
def run_deep_parse_1024(vault: SyntheticVault) -> ScenarioReceipt:
    def action() -> None:
        page = StackMachineParser().parse(vault.deep_chain_source, page_title="runtime-deep")
        assert_tree_invariants(page)
        assert len(tuple(walk_nodes(page.root_nodes))) == DEEP_CHAIN_DEPTH

    return measure_scenario("deep_parse_1024", action)


def run_cold_graph_load(vault: SyntheticVault) -> ScenarioReceipt:
    def action() -> None:
        with TemporaryDirectory() as temporary:
            graph = LogseqGraph.load_directory(vault.materialize(Path(temporary)))
            assert len(graph.pages) == vault.page_count

    return measure_scenario("cold_graph_load", action)
```

For `incremental_alias_move_reload`, materialize a new temporary synthetic vault for every action, alter only the known generated title/alias fixture, call `invalidate_and_reload_page()` on the former and moved paths, cold-load the same temporary vault, and compare the ordered backlink source UUID lists for the former title, new title, retained alias, and new alias. The UUID lists are semantic assertions only and must never enter the receipt.

For `search_content`, cold-load a temporary vault, search the fixed unique token embedded by the generator, and assert the expected aggregate count and non-empty node identities. Import `logseq_matryca_parser.synapse` as `synapse_module`. For `synapse_context_chunks`, return `unavailable` before sampling when `synapse_module.Document is None`; otherwise patch `synapse_module.Document` with a small local `HarnessDocument`, run `SynapseAdapter.to_context_enriched_chunks()`, and assert expected count plus non-empty lineage metadata (`page_title`, `source_path`, `line_start`, and `parent_id` where applicable). Do not import, invoke, or serialize any real vault.

- [ ] **Step 4: Write the failing stdout-only CLI test**

```python
def test_module_cli_emits_one_source_free_json_object() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "tests.performance.runtime_evidence"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["replay_command"] == "uv run python -m tests.performance.runtime_evidence"
    assert "exception" not in completed.stdout.casefold()
```

- [ ] **Step 5: Implement the replay entry point and execute focused verification**

```python
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a source-free local runtime-evidence receipt.")
    parser.parse_args(argv)
    print(json.dumps(run_runtime_evidence().to_payload(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `rtk .venv/bin/python -m pytest tests/test_performance_synthetic_vault.py tests/test_runtime_evidence.py -q`

Expected: PASS. The core scenarios are valid, SYNAPSE has an explicit unavailable state if optional support is absent, and subprocess output is one parseable source-free JSON object with no persisted file.

- [ ] **Step 6: Inspect a manual local receipt without recording it in the repository**

Run: `rtk .venv/bin/python -m tests.performance.runtime_evidence`

Expected: one JSON object with five scenario entries, each available entry reporting exactly 3 warm-ups and 21 samples, and no generated Markdown, paths, titles, UUIDs, host name, or exception text. Treat observed time and RSS values as local diagnostics only.

- [ ] **Step 7: Commit the executable test-only harness**

```bash
rtk git add tests/performance/runtime_evidence.py tests/test_runtime_evidence.py
rtk git commit -m "test: add runtime evidence scenarios"
```

## Task 4: Maintained operator documentation and final validation

**Files:**

- Create: `docs/reference/PERFORMANCE_EVIDENCE.md`
- Modify: `docs/index.md`
- Modify: `docs/maintained.toml`
- Modify: `docs/log.md`

**Interfaces:**

- Consumes: the fixed replay command and receipt field contract from Task 3; the M8 decision from the canonical execution plan.
- Produces: a maintained human/agent-facing reference that explains how to obtain and interpret local evidence without adding a public performance promise.

- [ ] **Step 1: Write failing maintained-document registration checks**

```python
def test_performance_evidence_reference_is_maintained_and_indexed() -> None:
    maintained = Path("docs/maintained.toml").read_text(encoding="utf-8")
    index = Path("docs/index.md").read_text(encoding="utf-8")

    assert '"docs/reference/PERFORMANCE_EVIDENCE.md"' in maintained
    assert "[Runtime evidence](reference/PERFORMANCE_EVIDENCE.md)" in index
```

Place this focused assertion in `tests/test_runtime_evidence.py`; `tests/test_check_documentation.py` already validates the checker itself against disposable fixtures, while this assertion protects the real M8 registration and avoids a second documentation-test framework.

- [ ] **Step 2: Run the registration check to verify it fails**

Run: `rtk .venv/bin/python -m pytest tests/test_runtime_evidence.py -q`

Expected: FAIL because the reference and registrations do not yet exist.

- [ ] **Step 3: Add the reference document with exact operational boundaries**

The new document must have the repository-required frontmatter fields and state all of the following in direct English:

```markdown
---
type: ReferenceGuide
title: Runtime evidence
description: Test-only local runtime evidence protocol and source-free receipt contract.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-20
verified: 2026-08-20
stale_after: 2027-02-20
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Runtime evidence

Run `uv run python -m tests.performance.runtime_evidence` from an exact committed checkout.
The command prints one source-free JSON receipt and does not persist a result.

Interpret each receipt only on its recorded Python/platform/machine context.
It is an observation, not a cross-machine comparison, CI gate, release claim,
or general performance guarantee.
```

Add a compact noise policy: run on an exact committed head; record the unmodified JSON externally only when a maintainer explicitly needs it; close competing local workloads when practical; repeat only with the same command and environment; never average observations across machines; investigate a semantic-gate failure before considering any duration; and require a separately approved baseline/promotion decision before a budget, release statement, or public headline. State the fixed 3 warm-up/21-sample protocol, nearest-rank p95, native RSS labelling, synthetic-only scope, no private input path, and SYNAPSE `unavailable` status.

- [ ] **Step 4: Register the document and record the documentation evolution**

Add exactly one `Runtime evidence` row to the maintained-entry table in `docs/index.md`, add the exact path to `maintained_documents` in `docs/maintained.toml`, and add a concise dated entry to `docs/log.md`. The log may claim that the contract and replay documentation were added; it must not claim benchmark results, cross-machine comparability, CI enforcement, release qualification, or a public performance improvement.

- [ ] **Step 5: Run focused and repository documentation validation**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_performance_synthetic_vault.py tests/test_runtime_evidence.py -q
rtk .venv/bin/python scripts/check_documentation.py --root . --profile docs/maintained.toml --as-of-date 2026-08-20
rtk bash scripts/check_vendor_free_docs.sh
rtk git diff --check
```

Expected: PASS. The maintained checker accepts frontmatter and registration, the terminology policy accepts public files, and no whitespace error is present.

- [ ] **Step 6: Perform required structural and full-suite verification**

Run:

```bash
rtk .venv/bin/python -m pytest -q --cov=src/logseq_matryca_parser --cov-report=term-missing
rtk .venv/bin/ruff check src tests
rtk .venv/bin/mypy src
rtk make vendor-name-check
rtk git diff --check
```

Before this command block, run the approved local audit-code workflow for `LogseqGraph.load_directory` and `LogseqGraph.invalidate_and_reload_page`, then run its cycle check. Retain only the local terminal receipt: the repository policy deliberately forbids naming the indexer product in source-controlled artifacts. Expected: impact evidence is reviewed before any protected-hub change, import cycles report zero, full tests meet the existing coverage floor, lint/type/documentation/policy checks pass, and whitespace is clean.

- [ ] **Step 7: Commit documentation and hand off for review**

```bash
rtk git add docs/reference/PERFORMANCE_EVIDENCE.md docs/index.md docs/maintained.toml docs/log.md tests/test_runtime_evidence.py
rtk git commit -m "docs: document runtime evidence protocol"
rtk git status --short --branch
```

Report the exact commit, branch, command receipts, optional SYNAPSE availability, and any unavailable verification. Do not push, open a pull request, merge, tag, or release without separate live GitHub checks and authorization.

## Plan self-review

### Spec coverage

| M8 requirement | Implementing task |
|---|---|
| Test-only harness; no public API, dependency, or CI threshold | Tasks 1–3 global constraints and isolated `tests/performance/` files |
| Original deterministic vault with 96 pages, 24 blocks, cross-links, aliases, tags, and a bounded deep chain | Task 1 |
| Five named scenarios | Task 3 |
| Three warm-ups, 21 samples, `perf_counter_ns`, median, and nearest-rank p95 | Task 2 |
| Native-unit RSS with explicit unavailable state | Task 2 |
| Source-free, stdout-only JSON with aggregate identity and exact replay | Tasks 2–3 |
| Semantic validity in every available sample | Task 3 |
| Optional SYNAPSE unavailable, never passed or skipped | Tasks 2–3 |
| No universal performance claim; documented noise and promotion policy | Task 4 |
| Fresh hub impact evidence, zero cycles, and full validation | Task 4 |

### Placeholder scan

The plan contains no unbounded work item, unresolved interface, external corpus dependency, or unspecified validation command. The approved local audit wrapper is deliberately abstract only in a private execution command, because the repository policy forbids placing a particular third-party tool name in source-controlled artifacts.

### Type and contract consistency

`SyntheticVault` is the only generated-source carrier and supplies aggregate fields to `RuntimeEvidenceReceipt`. `measure_scenario()` returns `ScenarioReceipt`; each scenario runner returns the same type; `run_runtime_evidence()` aggregates those five scenario receipts. Receipt serialization is the sole data path to stdout, which keeps generated source and exception objects out of emitted data.
