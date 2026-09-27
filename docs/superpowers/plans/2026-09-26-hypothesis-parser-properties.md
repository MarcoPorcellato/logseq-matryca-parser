# Bounded Hypothesis Parser Properties — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task by task. Keep each task test-first and stop at its stated gate.

**Goal:** Add a small, bounded, development-only Hypothesis suite that explores valid Logseq outline inputs and checks existing parser structure and semantic round-trip contracts for issue #104.

**Architecture:** Keep all generated inputs and assertions under `tests/`. Reuse `StackMachineParser`, `serialize_logseq_page`, `project_page(profile="semantic_roundtrip_v1")`, fixture-specific identity policy, and `assert_tree_invariants`. Add no production code, public API, runtime dependency, external parser/oracle, real-vault access, benchmark, or separate CI job.

**Tech Stack:** Python 3.12+, pytest, Hypothesis (development dependency only), existing parser-assurance projections and invariants.

**Base:** `origin/main` at `d85ea35ec2dbd37f5121d5052bf1e481bded973d` (2026-09-26). Refresh and verify the exact base before implementation.

**Scope:** First bounded Hypothesis slice for #104; not completion of #104 or M4.

## Global constraints

- Keep all persisted documentation and maintainer-facing text in English.
- Generate only in-memory, synthetic Markdown. Never read a user vault, network source, or external oracle.
- Keep generated documents small (maximum 16 KiB), outline depth at most 5, and at most 16 blocks per example. Set `max_examples=40`, `derandomize=True`, `deadline=None`, `database=None`, and `print_blob=True`. Forty is the successful-generation target, not a hard cap on executions: rejection, replay, shrinking, and explanation may add calls. Input/generation shape is bounded; this in-process suite has no hard execution-time bound.
- This slice does not replace or claim the M3 parent-enforced subprocess timeout/no-hang evidence in `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`. If a hard time limit is required for a future generator, use that isolated harness rather than treating Hypothesis settings as a watchdog.
- Reuse the existing `semantic_roundtrip_v1` contract and explicit identity policy. Do not claim byte-for-byte serialization equality or universal synthetic-UUID stability.
- This Hypothesis slice covers only valid grammar-generated inputs. It adds no Hypothesis-specific malformed-input strategy, timeout isolation, minimized receipt, graph/filesystem behavior, concurrency, or performance work; existing M3 adversarial and work-growth harnesses remain authoritative for their current contracts.
- Add Hypothesis only to the `dev` dependency group. Before selecting a version, recheck the official release metadata, project license, Python support, and repository dependency policy; resolve and review the full lock diff. Do not add a runtime extra, separate workflow/job, or special CI profile; the bounded tests run within the existing pytest suite.
- Do not weaken coverage thresholds or change production behavior. `#104` remains open until its full acceptance criteria are independently evidenced.
- Run tests through the repository's locked environment. Required final gates: focused property/corpus tests, `rtk make all`, `rtk make vendor-name-check`, the exact wheel/sdist contract from `.github/workflows/ci.yml`, and `rtk git diff --check`; report any pre-existing or environment failure distinctly.

## Files and ownership

| File | Change |
|---|---|
| `pyproject.toml` | Add a reviewed Hypothesis version constraint to `dependency-groups.dev`; leave runtime dependencies untouched. |
| `uv.lock` | Regenerate from the declaration and inspect every Hypothesis-related package/version/source/license delta. |
| `.pre-commit-config.yaml` | Pin the same Hypothesis release in the isolated mypy hook environment so it can type-check tests importing the dev-only dependency; do not change hosted CI workflows. |
| `tests/test_parser_properties.py` | New bounded generated outline and round-trip properties only. |
| `docs/ROADMAP_2026-2027.md` | Update #104 progress only if the implementation and evidence are accepted; do not mark the issue complete. |
| `docs/log.md` | Add a concise dated entry only after validation; state the exact bounded scope and residual work. |

## Task 1 — Admit Hypothesis as development-only tooling

**Files:** `pyproject.toml`, `uv.lock`

- [ ] Reconfirm `origin/main`, working-tree state, and #104 scope; inspect the current dependency/license policy.
- [ ] Verify current official Hypothesis release metadata, supported Python versions, and MPL-2.0 license from primary sources. Record the chosen constraint and exact lock resolution in the eventual change review.
- [ ] Add the constraint only to `dependency-groups.dev`; regenerate `uv.lock` using the locked project workflow.
- [ ] Review the complete lock diff. Confirm no runtime or optional-extra dependency changed and no unrelated package drift was introduced.
- [ ] Confirm the project dependency/license workflow can identify Hypothesis and its transitive packages in development scope. Record any unavailable development-license evidence as a gate; do not create or publish release SBOM artifacts for this test-only change.
- [ ] Keep the isolated mypy pre-commit environment able to type-check the test tree by pinning the selected Hypothesis release in that hook's `additional_dependencies`; do not add Hypothesis to runtime dependencies or hosted CI jobs.

**Gate:** stop if the package metadata, compatibility, or lock provenance is ambiguous; do not substitute a VCS dependency.

## Task 2 — Define generated valid outline models and verify baseline and oracle sensitivity

**Files:** `tests/test_parser_properties.py`, optionally a narrowly scoped helper under `tests/parser_assurance/` only if the test file becomes materially clearer.

- [ ] Create a bounded Hypothesis strategy for small recursive outline models: safe single-line block text, zero-to-three children per node, maximum depth 5, maximum 16 total nodes, and no Markdown syntax outside the strategy's declared grammar. Generate directly from the grammar; avoid rejection-heavy `.filter()` or `assume()` loops.
- [ ] Render each model to deterministic Logseq Markdown with two-space indentation and a final newline; assert the generated source is no more than 16 KiB.
- [ ] Compare parsed `(content, ordered children)` recursively against the independently generated model, or compare model-derived `(outline_path, content)` pairs. Node count and preorder alone are insufficient to prove hierarchy.
- [ ] Also run `assert_tree_invariants(page)` to verify UUID uniqueness, parent/left pointers, paths, and outline paths within the parsed tree.
- [ ] Establish the baseline outcome without requiring a parser failure; new properties may pass on the current implementation.
- [ ] Prove oracle sensitivity in test-only scope: (a) a hierarchy mutation that preserves preorder and rebuilds internally consistent pointers must fail the independent model comparison, and (b) a corrupted parent/left pointer must fail `assert_tree_invariants`. Do not mutate or commit production code for these checks.
- [ ] If the parser fails on an in-scope valid model, preserve Hypothesis' minimized failing example/blob, test node ID, exact source revision, locked Hypothesis version, and Python version. Stop for a separate parser-fix decision rather than weakening the property.

## Task 3 — Add semantic round-trip properties

**Files:** `tests/test_parser_properties.py`

- [ ] Add a bounded strategy for simple block properties and safe wikilink values only after the plain-outline property passes; avoid ambiguous Markdown, macros, embeds, and syntax not needed for the first slice.
- [ ] Parse generated source, serialize with `serialize_logseq_page`, parse again with the same page title, and compare both results through `project_page(..., profile="semantic_roundtrip_v1", identity_policy=...)`.
- [ ] Use an explicit policy consistent with the selected generated fixture family. Assert structure invariants on both parse results. Do not compare raw UUIDs unless the policy explicitly guarantees them.
- [ ] Add one test-only negative control showing that a changed semantic field is detected by the projection comparison; keep it deterministic and avoid a mutation-testing dependency.
- [ ] Set `print_blob=True` explicitly. Record the failing test node ID, Python version, locked Hypothesis version, source revision, and printed reproduction blob in local review evidence; do not commit opaque blobs or generated source by default. Promote a minimized failure to a normal explicit regression example only after maintainer review.
- [ ] Run `rtk uv run pytest -q tests/test_parser_properties.py tests/test_compat_corpus.py tests/test_parser_deep_refresh.py`; inspect Hypothesis reproduction output on any failure and preserve no generated source artifact by default.

## Task 4 — Verify integration and record only proven progress

**Files:** `docs/ROADMAP_2026-2027.md`, `docs/log.md` only if earned by evidence.

- [ ] Run `rtk uv sync --locked --all-extras` and the focused tests, then `rtk make all` and `rtk make vendor-name-check`.
- [ ] Reproduce the `package-contract` job from `.github/workflows/ci.yml`: build wheel and sdist, run `scripts/check_wheel_contract.py`, run the pinned Twine metadata check, and run downstream strict-typing verification from the built wheel.
- [ ] Run `rtk git diff --check` and inspect the final diff and lockfile for unintended changes.
- [ ] Run the mypy pre-commit hook in its isolated environment so the new dev-only import is validated by the normal commit gate.
- [ ] Confirm coverage does not regress below the existing floor; do not lower thresholds to accommodate generated tests.
- [ ] Confirm ordinary CI cost and stability remain acceptable. Do not add a separate high-example CI job in this slice. Report that bounded input generation is not a hard timeout and makes no new no-hang claim.
- [ ] Update the roadmap/log with an exact-head evidence statement only after all required gates pass. Keep #104 open and list only deferred Hypothesis-specific expansions; do not imply existing M3 adversarial/replay/timeout capabilities are missing.
- [ ] Request independent read-only review of the complete diff and test evidence before commit or publication.

## Acceptance criteria

1. The new tests explore bounded, grammar-valid synthetic Logseq outlines and detect hierarchy/order/identity-invariant violations.
2. Parse/serialize/parse semantic equality is checked using the repository's existing versioned projection and explicit identity rules.
3. Hypothesis is development-only, its resolved dependency graph is reviewed, and no runtime or CI contract changes.
4. The suite bounds generated input and target example count, shrinks failures, and reports enough information to replay a failing example; it explicitly does not claim a hard call or wall-clock limit.
5. Full quality/package gates pass, or failures are classified accurately without claiming completion.
6. Documentation describes this as one partial #104 increment; no claim of general parser correctness, full fuzzing, performance improvement, or issue closure.

## Sources and repository context

- Repository semantic profiles and invariants: `tests/parser_assurance/projection.py`, `tests/parser_assurance/invariants.py`, `tests/test_compat_corpus.py`, and `tests/test_parser_deep_refresh.py`.
- Existing #104 direction: `docs/ROADMAP_2026-2027.md` and M3 in `docs/LSDOC_REFERENCE_STUDY_AND_EXECUTION_PLAN_2026-08-16.md`.
- Dependency admission rules: `docs/reference/DEPENDENCY_LICENSE_POLICY.md`.
- Official Hypothesis project, documentation, releases, and license: <https://github.com/HypothesisWorks/hypothesis>, <https://hypothesis.readthedocs.io/>, and <https://github.com/HypothesisWorks/hypothesis/blob/master/LICENSE.txt>.
- Official execution-count caveats: <https://hypothesis.readthedocs.io/en/latest/explanation/test-case-count.html>. Settings and replay contracts: <https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html> and <https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html>.
