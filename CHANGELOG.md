# Changelog

All notable changes to **logseq-matryca-parser** (The Logos Protocol) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Cursor rules** — modular `.cursor/rules/*.mdc` guidance adapted from Matryca Plumber; `CHANGELOG.md`, `scripts/extract_changelog.py`, and `docs/RELEASE_PROCESS.md`.

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
