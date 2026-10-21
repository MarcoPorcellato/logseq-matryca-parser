---
type: Document
---
# Good First Issues

Welcome! These tasks are scoped for a **first pull request** — mostly tests and documentation, with a few small CLI/FORGE features. Each has clear acceptance criteria and avoids changes to `logos_core.py` without prior design discussion.

**Before you start:**

1. Read [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) (skim the module map), and [`logseq_ast_primer.md`](logseq_ast_primer.md) if you touch parsing.
2. Run `uv sync --locked --all-extras` then `make all` to confirm a green baseline.
3. Comment on the GitHub issue you want to claim so we avoid duplicate work.
4. Open **one PR per issue**, branched from `main` (`Fixes #NNN`).

Integrators may prefer [`COOKBOOK.md`](COOKBOOK.md) for copy-paste recipes before picking a code task.

Filter open good-first issues on GitHub: [good first issue label](https://github.com/MarcoPorcellato/logseq-matryca-parser/labels/good%20first%20issue).

**Status checked: 2026-10-18.** Start with the [recommended starter pack](#recommended-starter-pack).
The 2026-10-21 consolidation preserves this snapshot; it is not a fresh audit
of all issue states or assignments.
Open and closed labels below describe that dated GitHub snapshot, not a task
reservation or a promise that no related work exists. Check assignments,
comments and linked PRs before claiming. Earlier GFI IDs remain available for
historical references; a closed issue is not a request to repeat its work.

## Wave 5 — GFI-49 through GFI-58

These are the existing [#129–#138 catalog tasks](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/138),
not newly created issues. Estimates are the original issue ranges, not delivery
commitments; the exact missing assertions or documentation scope still need review.

| ID | Task | Tier | Skills | Estimate | GitHub state |
|---|---|---|---|---|---|
| GFI-49 | [#129: v1.6.0 release summary](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/129) | 2 — docs | Markdown, release evidence | 1–2 h | Closed |
| GFI-50 | [#130: module CLI entrypoint](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/130) | 1 — tests | pytest, subprocess CLI | 1–2 h | Closed |
| GFI-51 | [#131: diagnostic payload invariants](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/131) | 1 — tests | pytest, immutable payloads | 1–3 h | Open |
| GFI-52 | [#132: human diagnostics table](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/132) | 1 — tests | pytest, Typer/Rich output | 2–3 h | Open |
| GFI-53 | [#133: nested scan statistics](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/133) | 1 — tests | pytest, tree fixtures | 1–3 h | Open |
| GFI-54 | [#134: LOGBOOK serialization](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/134) | 1 — tests | pytest, Markdown fixtures | 1–3 h | Open |
| GFI-55 | [#135: deterministic file discovery](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/135) | 1 — tests | pytest, tmp_path | 1–2 h | Closed |
| GFI-56 | [#136: offline demo smoke test](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/136) | 1 — tests | pytest, CLI | 1–3 h | Closed |
| GFI-57 | [#137: optional extras reference](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/137) | 2 — docs | Markdown, packaging extras | 2–4 h | Open |
| GFI-58 | [#138: this catalog refresh](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/138) | 2 — docs | Markdown, issue reconciliation | 2–4 h | Open; addressed by this documentation update, not yet closed |

## Wave 6 — GFI-59 through GFI-68

| ID | Task | Tier | Skills | Estimate | GitHub state |
|---|---|---|---|---|---|
| GFI-59 | [#149: YAML frontmatter quoting](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/149) | 1 — tests | pytest, YAML scalars | 1–3 h | Open |
| GFI-60 | [#150: duplicate block anchors](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/150) | 1 — tests | pytest, FORGE exports | 2–4 h | Open |
| GFI-61 | [#151: empty/mixed property values](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/151) | 1 — tests | pytest, Markdown | 1–3 h | Open |
| GFI-62 | [#152: invalid wheel and CLI output](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/152) | 1 — tests | pytest, ZIP/metadata fixtures | 1–2 h | Open; [PR #218](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/218) exists—coordinate first |
| GFI-63 | [#153: reference-style documentation links](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/153) | 1 — tests | pytest, Markdown links | 2–3 h | Open |
| GFI-64 | [#154: titles, filenames and namespaces](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/154) | 2 — docs | Markdown, path contracts | 2–4 h | Open |
| GFI-65 | [#155: Python library quickstart](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/155) | 2 — docs | Python examples, graph API | 2–4 h | Open; compare the existing Cookbook before adding another recipe |
| GFI-66 | [#156: safe-write dry-run walkthrough](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/156) | 2 — docs | CLI, safety contracts | 2–4 h | Open |
| GFI-67 | [#157: Markdown construct support map](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/157) | 2 — docs | Markdown, evidence-backed compatibility | 3–4 h | Open |
| GFI-68 | [#158: focused test-contribution guide](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/158) | 2 — docs | pytest examples, contributor workflow | 2–3 h | Open; avoid duplicating CONTRIBUTING |

## Earlier waves — preserved IDs

The earlier tier tables retain their original IDs. A check mark means the
linked issue is closed at the verification date; read its resolution rather
than assuming every original proposal became a shipped feature.

---

## Tier 1 — Tests only (~1–3 hours)

Ideal first PR: no production code changes, copy patterns from nearby tests.

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-01 | `test(kinetic): add CLI error-path coverage for missing graph and optional deps` | pytest, Typer | ~~#19~~ → **GFI-47** [#95](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/95) |
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
| GFI-27 | `test(lens): regression test for unresolved wikilink ghost nodes` | pytest | [#62](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/62) ✅ ([#86](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/86)) |
| GFI-28 | `test(agent_press): cover malformed SessionAliasRegistry JSON on load` | pytest, CLI | [#63](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/63) ✅ |
| GFI-31 | `test(synapse): table-driven embed expansion edge cases` | pytest | [#71](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/71) ✅ ([#85](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/85)) |
| GFI-34 | `test(agent_writer): append_child without trailing source newline` | pytest, CLI | [#73](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/73) ✅ |
| GFI-39 | `test(synapse_embed): unit tests for embed expansion strategies` | pytest | [#88](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/88) — open, assigned; coordinate with the current owner |
| GFI-40 | `test(graph): public API coverage for iter_attached_nodes() and is_tracked_markdown_path()` | pytest | [#89](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/89) |
| GFI-41 | `test(kinetic_export): unit tests for export_obsidian path helpers` | pytest, FORGE | [#91](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/91) |
| GFI-42 | `test(lens): get_deep_statistics dedupes alias page duplicates (BUG-019)` | pytest | [#94](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/94) ✅ |
| GFI-46 | `test(synapse): table-driven tests for unresolved embed policy (#66 prep)` | pytest | [#96](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/96) ✅ |
| GFI-47 | `test(kinetic): table-driven CLI error-path coverage` | pytest, CLI | [#95](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/95) |
| GFI-48 | `test(graph): iter_attached_nodes excludes orphan nodes after registry collision` | pytest | [#97](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/97) ✅ |

---

## Tier 2 — Documentation & DX (~2–4 hours)

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-07 | `docs: add examples cookbook for common integration recipes` | Markdown, Python snippets | [#25](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/25) ✅ |
| GFI-08 | `docs: add docs/README.md index warning about historical design-docs` | Markdown | [#26](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/26) ✅ |
| GFI-09 | `test(kinetic): assert per-command --help renders without error` | pytest, Typer | [#27](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/27) ✅ |
| GFI-10 | `docs(examples): translate run_demo.py comments to English and align with package imports` | Python, docs | [#28](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/28) ✅ |
| GFI-43 | `docs(examples): add run_synapse_rag.py Synapse integration demo` | Python, docs | [#90](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/90) ✅ |
| GFI-44 | `docs(COOKBOOK): add scan --broken-refs and LENS visualize recipes` | Markdown, CLI | [#93](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/93) ✅ |

---

## Tier 3 — Small bounded features (~3–6 hours)

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-11 | `feat(cli): add scan --broken-refs flag using LogseqGraph.get_broken_references()` | Typer, graph API | [#29](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/29) ✅ ([#77](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/77)) |
| GFI-12 | `test(forge): add direct ObsidianForgeVisitor visitor tests` | pytest, FORGE | [#30](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/30) ✅ |
| GFI-13 | `test(parser): table-driven tests for clean_node_content helper` | pytest | [#31](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/31) ✅ |
| GFI-14 | `test(parser): unit tests for normalize_logseq_timestamp edge inputs` | pytest | [#32](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/32) ✅ |
| GFI-25 | `test(forge): direct MarkdownForgeVisitor property and id filtering` | pytest, FORGE | [#46](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/46) ✅ |
| GFI-26 | `test(forge): direct JSONForgeVisitor nested stack behavior` | pytest, FORGE | [#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52) ✅ |
| GFI-29 | `fix(lens): skip ghost page nodes for unresolved wikilinks` | pytest, LENS | [#59](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/59) ✅ ([#86](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/86)) |
| GFI-30 | `fix(agent): handle corrupt X-Ray state files without crashing agent-write` | pytest, CLI | [#60](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/60) ✅ |
| GFI-32 | `chore(synapse): replace Italian ImportError strings with English DX messages` | docs, SYNAPSE | [#69](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/69) ✅ |
| GFI-35 | `fix(agent_writer): append_child corrupts files missing trailing newline` | pytest, CLI | [#72](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/72) ✅ |
| GFI-45 | `fix(lens): resolve wikilink aliases to canonical page nodes (BUG-020)` | pytest, LENS | [#92](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/92) ✅ |

---

## Tier 4 — Clean Architecture slices (~1–4 hours)

**SSOT:** [`CLEAN_CODE_ARCHITECTURE.md`](CLEAN_CODE_ARCHITECTURE.md) · **Historical epic:** [#78](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/78) · **Closed milestone:** v1.6 — Clean Architecture & Code Quality · **Label:** `clean-code`

These structural slices are delivered history, not unclaimed refactor tasks.
New driver work needs its own reviewed scope; residual parser work follows
#104/#111/#108 and is not a first-PR assignment.

| ID | Title | Skills | Issue |
| :--- | :--- | :--- | :--- |
| GFI-36 | `test(arch): layer boundary import tests for entities and use cases` | pytest | *(landed — extend when adding modules)* |
| GFI-37 | `test(arch): assert adapters do not import kinetic` | pytest | ✅ (`tests/test_layer_boundary.py`) |
| GFI-38 | `refactor(kinetic): extract export handlers to dedicated module (SRP)` | Typer, refactor | **shipped** [#80](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/80) |
| GFI-33 | `refactor(synapse): extract embed-expansion strategy (OCP)` | pytest, refactor | **shipped** [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) |

**Verify (boundary tests):**

```bash
uv run pytest tests/test_layer_boundary.py -q
make check
```

---

## Mentor issues (slightly larger)

| ID | Title | Note | Issue |
| :--- | :--- | :--- | :--- |
| GFI-15 | `feat(forge): add minimal CSV exporter` | Follow existing JSON visitor pattern in `forge.py` | [#33](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/33) |
| GFI-16 | `docs: RFC Ollama one-click local RAG` | Design-only RFC; implementation in follow-up issues | [#34](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/34) *(draft at [`rfc/OLLAMA_RAG.md`](rfc/OLLAMA_RAG.md))* |
| GFI-33 | `refactor(synapse): extract embed-expansion strategy (OCP)` | Historical strategy slice, already closed | [#70](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/70) ✅ |

---

## Recommended starter pack

Prioritize these existing Wave 5 tasks. At the 2026-10-18 check, each was open
with no assignee and no claim discussion recorded. Recheck GitHub before starting;
this snapshot does not reserve the task or authorize changing production behavior.

| Priority | ID | Why |
| :---: | :--- | :--- |
| 1 | GFI-57 ([#137](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/137)) | Concise extras/troubleshooting reference; reuse existing installation guidance |
| 2 | GFI-51 ([#131](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/131)) | Small diagnostic payload assertions; compare existing coverage before adding tests |
| 3 | GFI-52 ([#132](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/132)) | Human-readable diagnostic table cases without changing producers |
| 4 | GFI-53 ([#133](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/133)) | Small nested fixture and exact scan statistics |
| 5 | GFI-54 ([#134](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/134)) | Focused LOGBOOK serializer cases, preserving existing behavior |

Do not duplicate assigned #88 or the packaging work already proposed in #218.
The mentor proposals #33/#34 require a separate product/design decision; LENS
is feature-frozen, and the old #92/#96/#66 work is not a current open assignment.

---

## Test navigation

| Module | Test file |
| :--- | :--- |
| Parser (LOGOS) | `tests/test_logos_parser.py` |
| Graph & watcher | `tests/test_graph.py` |
| SYNAPSE adapters | `tests/test_synapse.py`; direct strategy coverage is tracked by GFI-39 |
| KINETIC export | `tests/test_kinetic.py`; direct helper coverage is tracked by GFI-41 |
| FORGE exporters | `tests/test_forge.py` |
| KINETIC CLI | `tests/test_kinetic.py` |
| Agent read/write | `tests/test_agent_press.py`, `tests/test_agent_writer.py` |
| Architecture boundaries | `tests/test_layer_boundary.py` |
| Paths & markdown | `tests/test_logseq_paths.py`, `tests/test_logseq_markdown.py` |
| Release helpers | `tests/test_extract_changelog.py`, `tests/test_package_version.py` |
| Exceptions | `tests/test_exceptions.py` |

Full gate: `make all` (Ruff, Mypy, vendor/documentation checks and Pytest with
the existing 80% coverage floor). Use the actual run result, not a stale suite
count. For bounded generated assurance and its separate acceptance decision,
see the [#104 evidence package](quality/PARSER_ASSURANCE_ACCEPTANCE_2026-10-18.md).

Run `make vendor-name-check` before docs PRs to ensure Ghost Tooling policy (no vendor AST indexer names in the tree).

## Out of scope for a first PR

- Changes to Pydantic models in `logos_core.py` (open a design issue first).
- Parser/graph hub refactors, including `_refresh_node`, `load_directory` and
  incremental reload; these require impact analysis and a separately approved scope.
- Trama graph-intelligence UI ([#3](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/3)) — cross-product work; Parser LENS remains compatible and no Parser GUI work belongs in a first PR.
- Bulk mldoc parity work in `logos_parser.py` — high regression risk.
- Obsidian namespace path alignment — cross-tool behavior, needs design.

---

## Definition of Done (all tiers)

- [ ] `make all` passes locally (Ruff, Mypy, Pytest ≥80% coverage).
- [ ] PR links the GitHub issue and describes the change briefly.
- [ ] `CHANGELOG.md` updated under `[Unreleased]` **only** for user-visible behavior changes.
