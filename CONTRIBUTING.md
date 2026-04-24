# 🔱 Contributing to the Logos Protocol

First off, thank you for considering contributing to the **Logseq Matryca Parser (Logos Protocol)**!

This repository is the foundational AST engine for [Matryca.ai](https://matryca.ai), designed to preserve the spatial hierarchy of thought in Logseq graphs. We value deterministic logic, strict typing, and high performance.

To maintain the architectural integrity of the project, please follow the guidelines below.

---

## 🏛️ Architectural Philosophy

Before writing any code, please understand our core principles:

1. **The Graph is Sacred:** Logos does not guess or chunk text arbitrarily. It reconstructs the exact hierarchical tree based on spatial indentation.
2. **Deterministic Output:** Given the same `.md` file, the parser must *always* produce the exact same AST and identical UUIDs.
3. **No Bloat:** We strictly limit external dependencies to maximize compatibility with AOT compilers (like Nuitka) and ensure blazing-fast execution.

> **Note:** The `logos_core.py` module is the beating heart of the protocol. If your PR proposes changes to the Pydantic V2 models within it, please open an **Issue** for discussion first.

---

## 🛠️ Development Setup

To set up your local environment:

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/logseq-matryca-parser.git
   cd logseq-matryca-parser
   ```

2. **Create an Isolated Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the Project in Editable Mode:**
   *(Includes development dependencies)*
   ```bash
   pip install -e .
   pip install pytest mypy ruff
   ```

---

## 🚦 The Contribution Workflow

### 1. Find or Create an Issue

Whether it's a bug fix or a new feature (like a new exporter in `forge.py`), check the **Issues** tab first. If it's a new idea, open an Issue to discuss it with the maintainers before investing hours of work.

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

We run a strict CI pipeline. Before committing, you must ensure your code passes static analysis and tests.

We provide a `Makefile` to simplify running these commands. You can execute them individually or all at once:

```bash
# Run all checks (linting, static typing, and tests)
make all

# Or run them individually:
make lint   # Check formatting and linting with Ruff
make check  # Check static typing with Mypy
make test   # Run unit tests with Pytest
```

Alternatively, you can run the commands directly:

```bash
# Check formatting and linting
ruff check .

# Check static typing
mypy src/ tests/ examples/

# Run tests
pytest
```

### 5. Commit Standards

We follow [Conventional Commits](https://www.conventionalcommits.org/). Your commit messages should be structured like this:

- `feat(forge): add XML export functionality`
- `fix(parser): resolve stack overflow on deep indentation`
- `docs: update setup instructions`

### 6. Submit a Pull Request (PR)

- Push your branch and open a PR against the `main` branch.
- Describe why the change is needed.
- Link the relevant Issue (e.g., `Fixes #123`).
- Ensure all GitHub Actions (CI) checks pass.

---

## 🤝 Code of Conduct

We expect all contributors to maintain a professional, respectful, and constructive tone. We are building the future of sovereign knowledge management together.

> *By contributing to this project, you agree that your contributions will be licensed under its Apache 2.0 License.*
