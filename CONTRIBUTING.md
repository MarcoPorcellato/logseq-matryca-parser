# 🔱 Contributing to the Logos Protocol

First off, thank you for considering contributing to the **Logseq Matryca Parser (Logos Protocol)**!

This repository is the foundational AST engine for [Matryca.ai](https://matryca.ai), designed to preserve the spatial hierarchy of thought in Logseq graphs. We value deterministic logic, strict typing, and high performance.

To maintain the architectural integrity of the project, please follow the guidelines below.

---

## 📚 Documentation

User-facing behavior is documented in:

- [`README.md`](README.md) — overview, quickstart, and feature matrix
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — LOGOS, SYNAPSE, `LogseqGraph`, agents, and data flow
- [`docs/logseq_ast_primer.md`](docs/logseq_ast_primer.md) — Logseq Spatial Markdown domain rules
- [`CHANGELOG.md`](CHANGELOG.md) — shipped releases (current: **1.4.1**) and **Unreleased** changes (Keep a Changelog)
- [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) — version bump, tag, and PyPI publish checklist
- [`docs/CODEQL.md`](docs/CODEQL.md) — CodeQL default setup (no custom `codeql.yml`)
- [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md) — curated starter tasks for new contributors
- [`docs/COOKBOOK.md`](docs/COOKBOOK.md) — integration recipes (Synapse, graph query, watcher)
- [`docs/README.md`](docs/README.md) — documentation index (active vs historical)
- [`docs/rfc/OLLAMA_RAG.md`](docs/rfc/OLLAMA_RAG.md) — draft RFC for Ollama local RAG ([#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34))
- [`docs/internal/STATIC_ANALYSIS_POLICY.md`](docs/internal/STATIC_ANALYSIS_POLICY.md) — Ghost Tooling policy (vendor-agnostic CI and public docs)

When you add or change observable parser or graph behavior, update the relevant doc sections and add a bullet under **`## [Unreleased]`** in `CHANGELOG.md` (see [`.cursor/rules/05-auto-changelog.mdc`](.cursor/rules/05-auto-changelog.mdc)).

### Tooling policy

CI and automation in this repository are limited to the core runtime and standard open-source linters (Ruff, Mypy, Pytest, CodeQL). Do not add third-party AST indexers, experimental analysis scripts, or custom MCP servers to the public tree, workflows, or `pyproject.toml`. See [`docs/internal/STATIC_ANALYSIS_POLICY.md`](docs/internal/STATIC_ANALYSIS_POLICY.md).

Maintainers closing PRs that propose such integrations may use:

> *"Closing this PR. We've decided to keep our CI and automation scripts strictly focused on the core runtime and standard linters (e.g., ruff/mypy). Advanced local static analysis tools and experimental scripts will be maintained outside the main repository to keep the codebase lightweight, vendor-agnostic, and to reduce maintenance overhead."*

---

## 🌱 Your first PR

New to the codebase? Start here:

1. **Pick a task** from [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md) (label: `good first issue` on GitHub).
2. **Comment on the issue** so others know you are working on it.
3. **Set up** with `uv sync --all-extras` and confirm `make all` is green on `main`.
4. **Branch** using `feat/…`, `test/…`, or `docs/…` naming (see workflow below).
5. **Submit** one PR per issue, branched from `main` (`Fixes #123`).

Tier 1 tasks are **test-only** — no parser changes, ideal for learning `CliRunner` and pytest patterns in `tests/`. Tier 2 is documentation. Tier 3 adds small CLI or FORGE features with explicit acceptance criteria.

> **Avoid for a first PR:** changes to `logos_core.py` Pydantic models (open a design issue first) and large stack-machine refactors in `logos_parser.py`.

---

## 🏛️ Architectural Philosophy

Before writing any code, please understand our core principles:

1. **The Graph is Sacred:** Logos does not guess or chunk text arbitrarily. It reconstructs the exact hierarchical tree based on spatial indentation.
2. **Deterministic Output:** Given the same `.md` file, the parser must *always* produce the exact same AST and identical UUIDs.
3. **No Bloat:** We strictly limit external dependencies to maximize compatibility with AOT compilers (like Nuitka) and ensure blazing-fast execution.

> **Note:** The `logos_core.py` module is the beating heart of the protocol. If your PR proposes changes to the Pydantic V2 models within it, please open an **Issue** for discussion first.

---

## 🛠️ Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and a virtual environment in `.venv/`. Do not use `pip install -e .` — CI and local workflows both go through `uv`.

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/logseq-matryca-parser.git
   cd logseq-matryca-parser
   ```

2. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Sync the environment** (project + optional extras + dev tools from `pyproject.toml`):
   ```bash
   uv sync --all-extras
   ```

4. **Optional — install pre-commit hooks** (Ruff + Mypy, aligned with CI):
   ```bash
   uv run pre-commit install
   ```
   If `pre-commit` is not yet available, add it once with `uv tool install pre-commit` or `uv add --dev pre-commit`.

---

## 🚦 The Contribution Workflow

### 1. Find or Create an Issue

Whether it's a bug fix or a new feature (like a new exporter in `forge.py`), check the **Issues** tab first — especially [good first issues](docs/GOOD_FIRST_ISSUES.md). If it's a new idea, open an Issue to discuss it with the maintainers before investing hours of work.

### 2. Branch Naming Convention

Create a branch from `main` using the following naming format:

- `feat/your-feature-name` (for new features)
- `bugfix/issue-number-description` (for bug fixes)
- `docs/update-readme` (for documentation)

**Example:**
```bash
git checkout -b feat/add-html-exporter
```

### 3. Write Code & Tests

- If you fix a bug, write a unit test in `tests/` that fails without your patch and passes with it.
- If you add a feature, ensure it is covered by a comprehensive test.

### 4. Code Quality & Linting (Mandatory)

CI runs the same commands as your local environment: `uv sync --all-extras`, then `make lint`, `make check`, and `make test`. Before committing, run the full gate:

```bash
make all
```

As of **v1.4.1+**, `make test` runs **443** pytest cases with **≥80%** line coverage on `src/logseq_matryca_parser` (currently ~**90%**). New contributors should mirror patterns in [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md) and the module map in that file’s **Test suite** section.

Or run each step individually:

```bash
make lint   # Ruff (with auto-fix)
make check  # Mypy on src/, tests/, examples/
make test   # Pytest on tests/
```

Equivalent `uv run` invocations:

```bash
uv run ruff check . --fix
uv run mypy src/ tests/ examples/
uv run pytest -v tests/
```

### 5. Commit Standards

We follow [Conventional Commits](https://www.conventionalcommits.org/). Your commit messages should be structured like this:

- `feat(forge): add XML export functionality`
- `fix(parser): resolve stack overflow on deep indentation`
- `docs: update setup instructions`

### 6. Submit a Pull Request (PR)

- Push your branch and open a PR against the `main` branch (**one issue per PR**).
- Describe why the change is needed.
- Link the relevant Issue (e.g., `Fixes #123`). **One issue per PR** — do not stack multiple issues on a single branch.
- Ensure all GitHub Actions (CI) checks pass.

---

## 🤝 Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold a professional, respectful, and constructive community.

Report unacceptable behavior to [marco@marcoporcellato.it](mailto:marco@marcoporcellato.it).

> *By contributing to this project, you agree that your contributions will be licensed under its Apache 2.0 License.*
