# Changelog

All notable changes to **logseq-matryca-parser** (The Logos Protocol) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Community health files** — `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `.github/CODEOWNERS`, and `.github/ISSUE_TEMPLATE/config.yml` for GitHub Community Standards compliance.
- **PyPI project URLs** — `Repository`, `Source`, `Documentation`, and `Changelog` links in `pyproject.toml`.

### Changed

- **CI toolchain** — `.github/workflows/ci.yml` uses `astral-sh/setup-uv` and runs `uv sync --all-extras` followed by `make lint`, `make check`, and `make test` (parity with local `make all`).
- **CONTRIBUTING.md** — development setup documents `uv sync --all-extras` instead of `pip install -e .`.
- **Pre-commit** — Ruff and Mypy hook versions aligned with the `dev` dependency group in `pyproject.toml`.
- **Mypy scope** — unified to `src/`, `tests/`, and `examples/` in the Makefile, CI, CONTRIBUTING, and pre-commit.

## [1.2.0] - 2026-05-29

### Added

- **Asset extraction** — `LogseqNode.assets` collects markdown images, `{{pdf}}` macros, and local `[label](path)` attachments; `resolve_asset_path` decodes percent-encoded paths (`%20`).
- **YAML frontmatter** — `---` blocks at file start populate `LogseqPage.properties` like native Logseq page properties.
- **`page-tags::`** — block and page properties named `page-tags` inject implicit graph tokens like `tags::`.

### Fixed

- **Round-trip serialization** — soft-break continuations no longer double-indent; list-shaped block properties (`tags::` + bullets) serialize as Logseq bullet lists instead of Python repr; `:LOGBOOK:` drawers and derived temporal fields (`scheduled::`, `repeater::`, …) are not emitted as bogus `key::` lines; YAML frontmatter pages round-trip with `---` fences and stable block UUIDs; `title` from YAML or `title::` frontmatter overrides the graph page title for deterministic IDs.
- **Property comma-split in wikilinks** — `tags::` / `alias::` comma separation ignores commas inside `[[...]]` tokens.
- **Properties after code fences** — `key::` lines immediately following a closing fence are parsed into block properties (Logseq contiguity exception).
- **Org warning periods** — `DEADLINE` / `SCHEDULED` payloads with `-3d`-style warning periods parse without datetime failures.
- **Quoted property values** — outer `"` / `'` are stripped from block property values in the AST.
- **Query macro shielding** — `{{query}}` / `{{advancedquery}}` inline macros do not emit false wikilink graph tokens (embed macros still do).
- **Case-insensitive page routing** — `LogseqGraph.get_page` and `resolve_relative_page_link` resolve titles via a lowercase index (Datomic / Logseq parity).
- **HTML comment shielding** — wikilinks and tags inside `<!-- ... -->` are masked before entity extraction (no ghost graph links).
- **Graph token parity** — list-shaped block properties (`tags::` with bullets) feed wikilinks/tags into the AST; page-level properties (YAML and `key::` frontmatter) merge into `page.refs`.
- **Temporal ranges and repeaters** — `SCHEDULED` / `DEADLINE` markers with `HH:MM - HH:MM` ranges parse using the start time; repeater tokens (`.+1w`, `++1d`) are stripped before datetime parsing.
- **Legacy namespace filenames** — `filename_to_page_title` decodes `___`, `%2F`, and Dendron-style `.` separators.
- **BOM-prefixed graph files** — `parse_page_file` reads with `utf-8-sig` so Windows-synced BOM bytes do not break the first bullet.
- **Markdown escape shielding** — `\#` and `\[\[` no longer yield tags or wikilinks in graph metadata.
- **Empty bullets** — bare `-` / `*` lines parse as empty blocks instead of failing `BULLET_PATTERN`.
- **Wikilink header anchors** — `[[Page#Section]]` resolves to the page name only for graph routing.
- **Hybrid alias links** — `[Alias]([[Page]])` is no longer treated as a file asset.

## [1.1.1] - 2026-05-28

### Added

- **Graph page aliases** — `LogseqGraph.load_directory` honors `title::`, `alias::` / `aliases::` for `pages` lookup and backlinks; incremental reload re-applies enrichment after watcher edits.
- **LaTeX math shielding** — `_shield_inline_code` masks `$$...$$` and `$...$` spans so wikilinks/tags inside equations are not extracted.
- **Datalog query dead zones** — `#+BEGIN_QUERY` … `#+END_QUERY` blocks are ignored for entity extraction (parse-loop state plus shielding).
- **Numbered list blocks** — `logos_parser.py` recognizes ordered-list markers (`1. `, `12. `, etc.) as outliner bullets alongside `-` and `*`.
- **Markdown task checkboxes** — `[ ]`, `[-]`, and `[x]`/`[X]` on block text map to `TODO`, `DOING`, and `DONE` before Org-mode prefix fallback.

### Fixed

- **Logseq OG parity (parser)** — `{{embed [[Page]]}}` and similar macros expose nested wikilinks; Unicode tags and markdown boundaries (`**#tag**`, `==#tag==`); comma-separated `tags::` / `alias::` / `aliases::` inject implicit graph tokens; `~~~` fences share code-block immunity with ` ``` ` fences.
- **Property contiguity** — block `key:: value` lines apply only while contiguous below the bullet; after a soft-break, later `key::` lines stay in `content` / `clean_text` (Logseq-native behavior).
- **Property bullet lists** — empty `alias::` / `tags::` followed by indented `-` bullets serialize as `list[str]` without orphan AST children.
- **Case-insensitive property keys** — all property keys normalized to lowercase at parse time; `TITLE::` frontmatter overrides graph page titles like `title::`.
- **Extended task markers** — `DELEGATED`, `POSTPONED`, `IN-PROGRESS` (longest-prefix matching) alongside existing Org-mode statuses.
- **Aliased block references** — `[Visible](((uuid)))` clean text retains visible alias only (no surrounding `[` `]`).

## [1.0.0] - 2026-05-28

### Added

- **LOGOS engine** — deterministic Stack-Machine parser (`StackMachineParser`) producing strict `LogseqPage` / `LogseqNode` ASTs from Spatial Markdown.
- **SYNAPSE adapters** — LangChain and LlamaIndex exporters with parent-child lineage metadata.
- **FORGE exporters** — JSON, Markdown, Obsidian, and enriched chunk payloads.
- **LENS visualizer** — interactive topology HTML via NetworkX / PyVis.
- **KINETIC CLI** — `matryca-parse` Typer entry point for export, visualization, and agent read/write workflows.
- **Headless CRUD** — append-only agent writer and X-Ray press utilities for sovereign graph mutation.
- **Logseq-native serialization** — round-trip page and block property layout via `logseq_markdown.py`.
- **Graph query layer** — `LogseqGraph` with backlinks, effective property inheritance, and optional filesystem watcher.
