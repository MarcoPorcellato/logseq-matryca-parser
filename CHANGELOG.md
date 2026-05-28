# Changelog

All notable changes to **logseq-matryca-parser** (The Logos Protocol) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
