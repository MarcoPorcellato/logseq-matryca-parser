# Good First Issues

Welcome! These tasks are scoped for a **first pull request** — mostly tests and documentation, with a few small CLI/FORGE features. Each has clear acceptance criteria and avoids changes to `logos_core.py` without prior design discussion.

**Before you start:**

1. Read [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) (skim the module map), and [`logseq_ast_primer.md`](logseq_ast_primer.md) if you touch parsing.
2. Run `uv sync --all-extras` then `make all` to confirm a green baseline.
3. Comment on the GitHub issue you want to claim so we avoid duplicate work.
4. Open **one PR per issue**, branched from `main` (`Fixes #NNN`).

Integrators may prefer [`COOKBOOK.md`](COOKBOOK.md) for copy-paste recipes before picking a code task.

Filter open good-first issues on GitHub: [good first issue label](https://github.com/MarcoPorcellato/logseq-matryca-parser/labels/good%20first%20issue).

---

## Tier 1 — Tests only (~1–3 hours)

Ideal first PR: no production code changes, copy patterns from nearby tests.

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-01 | `test(kinetic): add CLI error-path coverage for missing graph and optional deps` | pytest, Typer | [#19](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/19) |
| GFI-02 | `test(kinetic): cover agent-write validation errors` | pytest, CLI | [#20](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/20) ✅ |
| GFI-03 | `test: add dedicated tests for exception hierarchy` | pytest | [#21](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/21) ✅ |
| GFI-04 | `test(logseq_paths): cover empty title and fallback graph-root derivation` | pytest | [#22](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/22) ✅ |
| GFI-05 | `test: add unit tests for extract_changelog release helper` | pytest | [#23](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/23) ✅ |
| GFI-06 | `test(agent): add CLI test for agent-read --query filter` | pytest, CLI | [#24](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/24) ✅ |
| GFI-17 | `test(logseq_markdown): unit tests for detect_tab_size_from_markdown` | pytest | [#43](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/43) ✅ |
| GFI-18 | `test(synapse): table-driven tests for _strip_markdown_for_embedding` | pytest | [#44](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/44) ✅ |
| GFI-19 | `test(graph): unit tests for _normalize_relative_link_target helper` | pytest | [#45](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/45) ✅ |
| GFI-20 | `test(extract_changelog): cover main() CLI exit codes and stdout` | pytest | [#47](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/47) ✅ |
| GFI-21 | `test(agent_writer): cover LogseqConfigReader format_timestamp and config fallback` | pytest, CLI | [#48](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/48) ✅ |
| GFI-22 | `test(lens): classify journal and project nodes in GraphVisualizer` | pytest | [#49](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/49) ✅ |
| GFI-23 | `test(graph): unit tests for backlink alias token helpers` | pytest | [#50](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/50) ✅ |
| GFI-24 | `test(synapse): direct build_synapse_metadata schema coverage` | pytest | [#51](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/51) ✅ |

---

## Tier 2 — Documentation & DX (~2–4 hours)

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-07 | `docs: add examples cookbook for common integration recipes` | Markdown, Python snippets | [#25](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/25) *(initial [`COOKBOOK.md`](COOKBOOK.md) landed — extend or polish)* |
| GFI-08 | `docs: add docs/README.md index warning about historical design-docs` | Markdown | [#26](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/26) *(index exists — verify links and `design-docs/README.md`)* |
| GFI-09 | `test(kinetic): assert per-command --help renders without error` | pytest, Typer | [#27](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/27) ✅ |
| GFI-10 | `docs(examples): translate run_demo.py comments to English and align with package imports` | Python, docs | [#28](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/28) *(done in repo — close if satisfied)* |

---

## Tier 3 — Small bounded features (~3–6 hours)

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-11 | `feat(cli): add scan --broken-refs flag using LogseqGraph.get_broken_references()` | Typer, graph API | [#29](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/29) |
| GFI-12 | `test(forge): add direct ObsidianForgeVisitor visitor tests` | pytest, FORGE | [#30](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/30) ✅ |
| GFI-13 | `test(parser): table-driven tests for clean_node_content helper` | pytest | [#31](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/31) ✅ |
| GFI-14 | `test(parser): unit tests for normalize_logseq_timestamp edge inputs` | pytest | [#32](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/32) ✅ |
| GFI-25 | `test(forge): direct MarkdownForgeVisitor property and id filtering` | pytest, FORGE | [#46](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/46) ✅ |
| GFI-26 | `test(forge): direct JSONForgeVisitor nested stack behavior` | pytest, FORGE | [#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52) ✅ |

---

## Mentor issues (slightly larger)

| ID | Title | Note | Issue |
| :--- | :--- | :--- | :--- |
| GFI-15 | `feat(forge): add minimal CSV exporter` | Follow existing JSON visitor pattern in `forge.py` | [#33](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/33) |
| GFI-16 | `docs: RFC Ollama one-click local RAG` | Design-only RFC; implementation in follow-up issues | [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34) *(draft at [`rfc/OLLAMA_RAG.md`](rfc/OLLAMA_RAG.md))* |

---

## Recommended starter pack (wave 2)

Wave 2 (GFI-17–GFI-26, GFI-02) is **complete** ([#58](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/58)). Next picks: GFI-01 ([#19](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/19)), GFI-11 ([#29](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/29)), or Tier 2 docs tasks.

---

## Test suite (v1.4.1+)

| Module | Test file |
| :--- | :--- |
| Parser (LOGOS) | `tests/test_logos_parser.py` |
| Graph & watcher | `tests/test_graph.py` |
| SYNAPSE adapters | `tests/test_synapse.py` |
| FORGE exporters | `tests/test_forge.py` |
| KINETIC CLI | `tests/test_kinetic.py` |
| Agent read/write | `tests/test_agent_press.py`, `tests/test_agent_writer.py` |
| Paths & markdown | `tests/test_logseq_paths.py`, `tests/test_logseq_markdown.py` |
| Release helpers | `tests/test_extract_changelog.py`, `tests/test_package_version.py` |
| Exceptions | `tests/test_exceptions.py` |

Run the full gate: `make all` (**443** pytest cases after wave 2).

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
