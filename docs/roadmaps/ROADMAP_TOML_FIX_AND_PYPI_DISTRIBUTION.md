# Architectural Contract: TOML Hotfix, Dynamic Versioning & PyPI Distribution Setup

**Contract Status:** Completed (Wave 8 — validated locally)

**Target Stack:** Python 3.12+ | Hatchling (PEP 621 compliant) | PyPI Distribution Standards

**Inspiration Architectures:** Drive Insights (Claude, Grok, DeepSeek deployment optimizations)

---

## Task 1: Clean TOML Structural Refactoring (Hotfix)

* **Objective:** Eliminate the `duplicate key` parsing error at line 48 in `pyproject.toml` by streamlining the optional dependencies table and ensuring full PEP 621 compliance for modern TOML parsers.
* **Target Files:**
    * `pyproject.toml`
* **Implementation Specifications:**
    1. Open the root `pyproject.toml` and locate the `[project.optional-dependencies]` section.
    2. Completely rewrite the configuration file using a clean, explicit order to eliminate block cross-contamination:
       * Define core `[project]` fields first.
       * Define explicit `dependencies = [...]`.
       * Declare a single, sterile `[project.optional-dependencies]` block.
       * Decouple the `[dependency-groups]` dev array to use exact strings or explicitly reference the project extras via standard syntax (e.g., `logseq-matryca-parser[all]`) to prevent metadata collisions.
    3. Remove the placeholder/empty `src/logseq_matryca_parser/pyproject.toml` if it is causing local routing ambiguities.
    4. **Quality Gate:** Run `uv pip compile pyproject.toml` or any basic setup linter to verify the syntax compiles perfectly without throwing parsing errors.

### Task 1 checklist

- [x] Root `pyproject.toml` rewritten with explicit section order and no duplicate keys
- [x] Optional extras and `dependency-groups.dev` decoupled (project extras referenced by name where appropriate)
- [x] Nested stray `pyproject.toml` under `src/` removed if present (none found)
- [x] `uv pip compile pyproject.toml` (or equivalent) succeeds

---

## Task 2: Dynamic Package Version Exposure & Layout Integration

* **Objective:** Ensure the package exposes its canonical version programmatically at runtime (`logseq_matryca_parser.__version__`), a mandatory requirement emphasized by multi-model distribution advice.
* **Target Files:**
    * `src/logseq_matryca_parser/__init__.py`
* **Implementation Specifications:**
    1. Open `src/logseq_matryca_parser/__init__.py`.
    2. Define a public `__version__` string constant reflecting the current project version state (`"0.3.0"`).
    3. Ensure `__version__` is explicitly listed within the `__all__` packaging array configuration.
    4. **Quality Gate:** Add a fast verification test inside `tests/test_kinetic.py` or a dedicated package test verifying that importing `__version__` yields a string matching standard semantic versioning rules.

### Task 2 checklist

- [x] `__version__ = "0.3.0"` defined and exported via `__all__`
- [x] Unit test asserts semver-shaped string from `logseq_matryca_parser.__version__` (`tests/test_package_version.py`)

---

## Task 3: Production GitHub Actions Workflow for PyPI Auto-Release

* **Objective:** Finalize the repository setup by automating package distribution whenever a new version release tag is pushed to GitHub.
* **Target Files:**
    * `.github/workflows/pypi_publish.yml` (New File)
* **Implementation Specifications:**
    1. Author a secure GitHub Actions workflow triggered exclusively on tag pushes matching `v*` (e.g., `v0.3.0`).
    2. Configure environment jobs to build source distributions and wheels using standard python build tools or Hatch.
    3. Inject trusted publishing permissions (`id-token: write`) to allow seamless, passwordless authentication with PyPI using OpenID Connect (OIDC).
    4. **Quality Gate:** Validate that the YAML syntax passes structural validation checks during local CI workflows.

### Task 3 checklist

- [x] `.github/workflows/pypi_publish.yml` added with `v*` tag trigger
- [x] Build produces sdist + wheel; publish uses OIDC (`id-token: write`)
- [x] Workflow YAML validated (structural parse check)

---

## Sprint completion (post-verification)

- [x] `make lint` green
- [x] `make check` (mypy) green
- [x] `make test` (pytest) green
