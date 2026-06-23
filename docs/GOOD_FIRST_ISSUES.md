# Good First Issues

Welcome! These tasks are scoped for a **first pull request** — mostly tests and documentation, with a few small CLI/FORGE features. Each has clear acceptance criteria and avoids changes to `logos_core.py` without prior design discussion.

**Before you start:**

1. Read [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) (skim the module map), and [`logseq_ast_primer.md`](logseq_ast_primer.md) if you touch parsing.
2. Run `uv sync --all-extras` then `make all` to confirm a green baseline.
3. Comment on the GitHub issue you want to claim so we avoid duplicate work.
4. Open a PR linking the issue (`Fixes #NNN`).

Integrators may prefer [`COOKBOOK.md`](COOKBOOK.md) for copy-paste recipes before picking a code task.

Filter open good-first issues on GitHub: [good first issue label](https://github.com/MarcoPorcellato/logseq-matryca-parser/labels/good%20first%20issue).

---

## Tier 1 — Tests only (~1–3 hours)

Ideal first PR: no production code changes, copy patterns from nearby tests.

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-01 | `test(kinetic): add CLI error-path coverage for missing graph and optional deps` | pytest, Typer | [#19](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/19) |
| GFI-02 | `test(kinetic): cover agent-write validation errors` | pytest, CLI | [#20](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/20) |
| GFI-03 | `test: add dedicated tests for exception hierarchy` | pytest | [#21](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/21) |
| GFI-04 | `test(logseq_paths): cover empty title and fallback graph-root derivation` | pytest | [#22](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/22) |
| GFI-05 | `test: add unit tests for extract_changelog release helper` | pytest | [#23](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/23) |
| GFI-06 | `test(agent): add CLI test for agent-read --query filter` | pytest, CLI | [#24](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/24) |

---

## Tier 2 — Documentation & DX (~2–4 hours)

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-07 | `docs: add examples cookbook for common integration recipes` | Markdown, Python snippets | [#25](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/25) *(initial [`COOKBOOK.md`](COOKBOOK.md) landed — extend or polish)* |
| GFI-08 | `docs: add docs/README.md index warning about historical design-docs` | Markdown | [#26](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/26) *(index exists — verify links and `design-docs/README.md`)* |
| GFI-09 | `test(kinetic): assert per-command --help renders without error` | pytest, Typer | [#27](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/27) |
| GFI-10 | `docs(examples): translate run_demo.py comments to English and align with package imports` | Python, docs | [#28](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/28) *(done in repo — close if satisfied)* |

---

## Tier 3 — Small bounded features (~3–6 hours)

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-11 | `feat(cli): add scan --broken-refs flag using LogseqGraph.get_broken_references()` | Typer, graph API | [#29](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/29) |
| GFI-12 | `test(forge): add direct ObsidianForgeVisitor visitor tests` | pytest, FORGE | [#30](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/30) |
| GFI-13 | `test(parser): table-driven tests for clean_node_content helper` | pytest | [#31](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/31) |
| GFI-14 | `test(parser): unit tests for normalize_logseq_timestamp edge inputs` | pytest | [#32](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/32) |

---

## Mentor issues (slightly larger)

| ID | Title | Note | Issue |
| :--- | :--- | :--- | :--- |
| GFI-15 | `feat(forge): add minimal CSV exporter` | Follow existing JSON visitor pattern in `forge.py` | [#33](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/33) |
| GFI-16 | `docs: RFC Ollama one-click local RAG` | Design-only RFC; implementation in follow-up issues | [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34) *(draft at [`rfc/OLLAMA_RAG.md`](rfc/OLLAMA_RAG.md))* |

---

## Out of scope for a first PR

- Changes to Pydantic models in `logos_core.py` (open a design issue first).
- Desktop GUI ([#3](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/3)) — multi-sprint epic.
- Bulk mldoc parity work in `logos_parser.py` — high regression risk.
- Obsidian namespace path alignment — cross-tool behavior, needs design.

---

## Definition of Done (all tiers)

- [ ] `make all` passes locally (Ruff, Mypy, Pytest ≥80% coverage).
- [ ] PR links the GitHub issue and describes the change briefly.
- [ ] `CHANGELOG.md` updated under `[Unreleased]` **only** for user-visible behavior changes.
