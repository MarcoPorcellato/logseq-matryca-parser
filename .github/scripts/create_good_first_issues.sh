#!/usr/bin/env bash
# Creates Good First Issues on GitHub. Run from repo root:
#   bash .github/scripts/create_good_first_issues.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OUT="$ROOT/.github/gfi_issue_numbers.txt"
: > "$OUT"

create_issue() {
  local id="$1"
  local title="$2"
  local labels="$3"
  local body_file="$4"
  local url
  url=$(gh issue create --title "$title" --label "$labels" --body-file "$body_file")
  local num="${url##*/}"
  echo "$id=$num" >> "$OUT"
  echo "Created $id -> #$num"
}

BODY_DIR=$(mktemp -d)
trap 'rm -rf "$BODY_DIR"' EXIT

# GFI-01
cat > "$BODY_DIR/gfi01.md" <<'EOF'
## Context

`tests/test_kinetic.py` covers happy paths for the KINETIC CLI (`matryca-parse`). Error messages for missing graph paths and optional dependencies (`[viz]`, `[ai]`) are implemented in `kinetic.py` but not asserted in tests.

## Objectives

- [ ] `scan` / `export` on an empty vault → output contains `"No Markdown files found"`
- [ ] Command without positional graph path and without `--graph` → `"Graph path required"`
- [ ] `visualize` / `demo` without `[viz]` extra → dependency hint message
- [ ] `export --format langchain` without `[ai]` extra → dependency hint message
- [ ] Reuse existing `CliRunner` and `_create_graph()` patterns from `tests/test_kinetic.py`

## Files

- `tests/test_kinetic.py`
- Reference: `src/logseq_matryca_parser/kinetic.py`

## Getting started

1. `uv sync --all-extras`
2. `make all`
3. Copy an existing CLI test (e.g. `test_scan_command_prints_graph_statistics`) and assert `result.exit_code != 0` plus substring in `result.stdout` / `result.stderr`

## Out of scope

- Changes to `logos_core.py`
- Production CLI behavior changes (tests only)

## Definition of Done

- `make all` passes
- No `CHANGELOG.md` entry needed (test-only)
EOF
create_issue "GFI-01" "test(kinetic): add CLI error-path coverage for missing graph and optional deps" "good first issue,tests,cli" "$BODY_DIR/gfi01.md"

# GFI-02
cat > "$BODY_DIR/gfi02.md" <<'EOF'
## Context

`matryca-parse agent-write` validates `--alias` vs `--target-uuid` and X-Ray state files, but validation error paths lack dedicated CLI tests.

## Objectives

- [ ] Neither `--alias` nor `--target-uuid` → non-zero exit
- [ ] Both flags together → mutual exclusion error
- [ ] Unknown alias without `.matryca_xray_state.json` → clear error message
- [ ] Missing `--state-file` when required by code path (if applicable)

## Files

- `tests/test_kinetic.py` and/or `tests/test_agent_press.py`

## Getting started

1. `uv sync --all-extras`
2. `make all`
3. Inspect `agent_write` command in `src/logseq_matryca_parser/kinetic.py`

## Out of scope

- `logos_core.py` model changes
- Agent write engine logic changes (tests only unless a bug is found)

## Definition of Done

- `make all` passes
- No `CHANGELOG.md` entry needed (test-only)
EOF
create_issue "GFI-02" "test(kinetic): cover agent-write validation errors" "good first issue,tests,cli" "$BODY_DIR/gfi02.md"

# GFI-03
cat > "$BODY_DIR/gfi03.md" <<'EOF'
## Context

`src/logseq_matryca_parser/exceptions.py` defines the public exception hierarchy exported in `__all__`, but there is no dedicated test module. `LogseqIndentationError` is reserved for future strict indentation mode and is not raised today.

## Objectives

- [ ] Add `tests/test_exceptions.py`
- [ ] Assert `BlockReferenceError` is a subclass of `LogseqParserError`
- [ ] Assert `LogseqIndentationError` is a subclass of `LogseqParserError`
- [ ] Document via test docstring that `LogseqIndentationError` is currently unused (no behavior change)

## Files

- New: `tests/test_exceptions.py`
- Reference: `src/logseq_matryca_parser/exceptions.py`

## Getting started

1. `uv sync --all-extras`
2. `make all`

## Out of scope

- Raising `LogseqIndentationError` from the parser
- `logos_core.py` changes

## Definition of Done

- `make all` passes
- No `CHANGELOG.md` entry needed
EOF
create_issue "GFI-03" "test: add dedicated tests for exception hierarchy" "good first issue,tests" "$BODY_DIR/gfi03.md"

# GFI-04
cat > "$BODY_DIR/gfi04.md" <<'EOF'
## Context

`logseq_paths.py` has edge-case helpers that are partially covered. Empty page titles and fallback graph-root derivation need explicit tests.

## Objectives

- [ ] `page_title_to_relative_path("")` → `untitled.md`
- [ ] `derive_graph_root_from_source_path` without `pages/` or `journals/` marker → falls back to `path.parent`
- [ ] `derive_page_title_from_source_path` outside `pages/`/`journals/` → uses `filename_to_page_title(stem)`

## Files

- `tests/test_logseq_paths.py`
- Reference: `src/logseq_matryca_parser/logseq_paths.py`

## Getting started

1. `uv sync --all-extras`
2. `make all`
3. Follow patterns in existing `test_logseq_paths.py` tests

## Out of scope

- Changing path encoding rules

## Definition of Done

- `make all` passes
- No `CHANGELOG.md` entry needed
EOF
create_issue "GFI-04" "test(logseq_paths): cover empty title and fallback graph-root derivation" "good first issue,tests" "$BODY_DIR/gfi04.md"

# GFI-05
cat > "$BODY_DIR/gfi05.md" <<'EOF'
## Context

`scripts/extract_changelog.py` provides pure functions for release notes extraction but has no unit tests. This is an ideal first PR with zero parser knowledge required.

## Objectives

- [ ] Add `tests/test_extract_changelog.py`
- [ ] `normalize_version("v1.0.0")` → `"1.0.0"`
- [ ] Extract existing section from a minimal CHANGELOG fixture
- [ ] Missing version raises `LookupError` or documented exit code
- [ ] `[Unreleased]` rejected when `allow_unreleased=False`

## Files

- New: `tests/test_extract_changelog.py`
- Reference: `scripts/extract_changelog.py`

## Getting started

1. `uv sync --all-extras`
2. `make all`
3. Import functions from `scripts/extract_changelog.py` (add `tests/` import path or use `importlib` pattern used elsewhere)

## Out of scope

- Changing release script CLI behavior

## Definition of Done

- `make all` passes
- No `CHANGELOG.md` entry needed
EOF
create_issue "GFI-05" "test: add unit tests for extract_changelog release helper" "good first issue,tests" "$BODY_DIR/gfi05.md"

# GFI-06
cat > "$BODY_DIR/gfi06.md" <<'EOF'
## Context

README documents `matryca-parse agent-read --query "needle"` but only `--tag` filtering is tested in `tests/test_agent_press.py`.

## Objectives

- [ ] CLI test: fixture graph with known text; `--query "needle"` prints only matching blocks
- [ ] Assert stdout uses X-Ray alias format (e.g. `[0]` prefix style)
- [ ] Output is plain text (no Rich markup)

## Files

- `tests/test_agent_press.py` and/or `tests/test_kinetic.py`

## Getting started

1. `uv sync --all-extras`
2. `make all`
3. Mirror existing `agent-read --tag` test setup

## Out of scope

- X-Ray formatting changes

## Definition of Done

- `make all` passes
- No `CHANGELOG.md` entry needed
EOF
create_issue "GFI-06" "test(agent): add CLI test for agent-read --query filter" "good first issue,tests,cli" "$BODY_DIR/gfi06.md"

# GFI-07
cat > "$BODY_DIR/gfi07.md" <<'EOF'
## Context

The repo has `examples/run_demo.py` and a journal fixture, but no copy-paste integration cookbook for Synapse, graph queries, or the filesystem watcher.

## Objectives

- [ ] Add `docs/COOKBOOK.md` with three minimal recipes:
  1. Parse a single page + `SynapseAdapter.to_langchain_documents`
  2. `LogseqGraph.load_directory` + fluent `graph.query()`
  3. `start_watching()` with note on `uv sync --extra watch`
- [ ] Link from `CONTRIBUTING.md` and README Contributing table
- [ ] Snippets import from package root (`logseq_matryca_parser` `__all__`)

## Files

- New: `docs/COOKBOOK.md`
- `CONTRIBUTING.md`, `README.md`, `docs/README.md`

## Getting started

1. `uv sync --all-extras`
2. Run snippets locally to verify they work

## Out of scope

- New Python modules or API changes

## Definition of Done

- Links verified
- Optional: brief `CHANGELOG.md` `### Added` entry for cookbook
EOF
create_issue "GFI-07" "docs: add examples cookbook for common integration recipes" "good first issue,documentation" "$BODY_DIR/gfi07.md"

# GFI-08
cat > "$BODY_DIR/gfi08.md" <<'EOF'
## Context

`docs/design-docs/` contains rich historical blueprints that can mislead newcomers. A documentation index (`docs/README.md`) was added to distinguish active vs historical docs — verify completeness and cross-links.

## Objectives

- [ ] Review `docs/README.md`: active vs historical table is accurate
- [ ] Link to `ARCHITECTURE.md`, `logseq_ast_primer.md`, `GOOD_FIRST_ISSUES.md`
- [ ] Add one-line pointer in `CONTRIBUTING.md` Documentation section (if missing)
- [ ] Optionally add a one-line banner at the top of `docs/design-docs/README.md` (new stub) pointing to `docs/README.md`

## Files

- `docs/README.md`
- `CONTRIBUTING.md`
- Optional: `docs/design-docs/README.md`

## Getting started

1. Read `docs/design-docs/CODE_SCAFFOLD.md` banner text for tone
2. Walk the `docs/` tree and confirm the index matches reality

## Out of scope

- Rewriting historical design docs

## Definition of Done

- All links resolve
- Optional `CHANGELOG.md` `### Added` for docs index
EOF
create_issue "GFI-08" "docs: add docs/README.md index warning about historical design-docs" "good first issue,documentation" "$BODY_DIR/gfi08.md"

# GFI-09
cat > "$BODY_DIR/gfi09.md" <<'EOF'
## Context

Only root `--help` is tested for Rich markup mode. Per-subcommand `--help` should render without errors to lock in CLI UX.

## Objectives

- [ ] `runner.invoke(app, ["<cmd>", "--help"])` returns exit code 0 for: `scan`, `export`, `visualize`, `agent-read`, `agent-write`, `append`, `demo`
- [ ] Optional: assert key flags appear (`--format`, `--tag`, `--graph`)

## Files

- `tests/test_kinetic.py`

## Getting started

1. `uv sync --all-extras`
2. See `test_cli_help_uses_rich_markup_mode` for pattern

## Out of scope

- Changing help text content

## Definition of Done

- `make all` passes
EOF
create_issue "GFI-09" "test(kinetic): assert per-command --help renders without error" "good first issue,tests,cli" "$BODY_DIR/gfi09.md"

# GFI-10
cat > "$BODY_DIR/gfi10.md" <<'EOF'
## Context

`examples/run_demo.py` has Italian comments and uses `sys.path` manipulation instead of package imports after `uv sync`.

## Objectives

- [ ] Translate comments and error messages to English
- [ ] Use `from logseq_matryca_parser...` imports without `sys.path` hack when possible
- [ ] `make check` passes on `examples/run_demo.py`

## Files

- `examples/run_demo.py`

## Getting started

1. `uv sync --all-extras`
2. `uv run python examples/run_demo.py`

## Out of scope

- New example features

## Definition of Done

- `make all` passes
- Optional `CHANGELOG.md` docs bullet
EOF
create_issue "GFI-10" "docs(examples): translate run_demo.py comments to English and align with package imports" "good first issue,documentation" "$BODY_DIR/gfi10.md"

# GFI-11
cat > "$BODY_DIR/gfi11.md" <<'EOF'
## Context

`LogseqGraph.get_broken_references()` (v1.3.0) scans the vault for unresolved `((uuid))` block refs but is not exposed in the CLI. A `--broken-refs` flag on `scan` would help CI vault hygiene.

## Objectives

- [ ] `matryca-parse scan GRAPH --broken-refs` prints missing refs (Rich table or one line per ref)
- [ ] Optional: exit code 1 when broken refs > 0 (document behavior in help text)
- [ ] Tests in `tests/test_kinetic.py` with fixture referencing `((fake-uuid))`
- [ ] `CHANGELOG.md` `### Added` entry

## Files

- `src/logseq_matryca_parser/kinetic.py`
- `tests/test_kinetic.py`

## Getting started

1. Read `get_broken_references()` in `graph.py`
2. See existing `test_get_broken_references_flags_missing_uuid` in `tests/test_graph.py`

## Out of scope

- `logos_core.py` changes

## Definition of Done

- `make all` passes
- CHANGELOG updated
EOF
create_issue "GFI-11" "feat(cli): add scan --broken-refs flag using LogseqGraph.get_broken_references()" "good first issue,cli,help wanted" "$BODY_DIR/gfi11.md"

# GFI-12
cat > "$BODY_DIR/gfi12.md" <<'EOF'
## Context

`ObsidianForgeVisitor` is public API (`__all__`) but `tests/test_forge.py` only exercises `ForgeExporter.to_obsidian_markdown`.

## Objectives

- [ ] Direct visitor tests: `((uuid))` → `[[Page#^anchor]]` with mock resolver
- [ ] Referenced block receives `^block-id` suffix
- [ ] YAML frontmatter from `page_properties`

## Files

- `tests/test_forge.py`
- Reference: `src/logseq_matryca_parser/forge.py`

## Getting started

1. `uv sync --all-extras`
2. See `test_forge_visitors_are_ast_compatible` for visitor patterns

## Out of scope

- Obsidian namespace path alignment (separate design issue)

## Definition of Done

- `make all` passes
EOF
create_issue "GFI-12" "test(forge): add direct ObsidianForgeVisitor visitor tests" "good first issue,tests,forge" "$BODY_DIR/gfi12.md"

# GFI-13
cat > "$BODY_DIR/gfi13.md" <<'EOF'
## Context

`clean_node_content` is exported in `__all__` and used throughout the parser pipeline but only tested indirectly.

## Objectives

- [ ] Table-driven tests in `tests/test_logos_parser.py`
- [ ] Cases: strip `id::`, `SCHEDULED`/`DEADLINE` markers, case-insensitive property keys
- [ ] No changes to `StackMachineParser`

## Files

- `tests/test_logos_parser.py`
- Reference: `clean_node_content` in `logos_parser.py`

## Getting started

1. `uv sync --all-extras`
2. Import `clean_node_content` from `logseq_matryca_parser`

## Out of scope

- Parser stack-machine changes

## Definition of Done

- `make all` passes
EOF
create_issue "GFI-13" "test(parser): table-driven tests for clean_node_content helper" "good first issue,tests" "$BODY_DIR/gfi13.md"

# GFI-14
cat > "$BODY_DIR/gfi14.md" <<'EOF'
## Context

`normalize_logseq_timestamp` complements `resolve_journal_day` (already tested) but has no direct unit tests for edge inputs.

## Objectives

- [ ] Valid Org/Logseq timestamp strings → UTC epoch `int`
- [ ] `None`, empty string, invalid format → `None`
- [ ] Tests in `tests/test_logos_parser.py`

## Files

- `tests/test_logos_parser.py`
- Reference: `normalize_logseq_timestamp` in `logos_parser.py`

## Getting started

1. `uv sync --all-extras`
2. Read function implementation before writing cases

## Out of scope

- Changing timestamp parsing rules

## Definition of Done

- `make all` passes
EOF
create_issue "GFI-14" "test(parser): unit tests for normalize_logseq_timestamp edge inputs" "good first issue,tests" "$BODY_DIR/gfi14.md"

# GFI-15
cat > "$BODY_DIR/gfi15.md" <<'EOF'
## Context

CONTRIBUTING cites "a new exporter in `forge.py`" as an example feature. A minimal CSV exporter is a bounded way to learn the FORGE visitor pattern.

## Objectives

- [ ] Add CSV export visitor (or static method on `ForgeExporter`)
- [ ] Columns: at minimum `uuid`, `clean_text`, `indent_level`, `parent_id`
- [ ] Tests in `tests/test_forge.py`
- [ ] Optional CLI `--format csv` (discuss in PR if scope grows)
- [ ] `CHANGELOG.md` if user-visible

## Files

- `src/logseq_matryca_parser/forge.py`
- `tests/test_forge.py`

## Getting started

1. Copy pattern from JSON exporter in `forge.py`
2. `uv sync --all-extras` && `make all`

## Out of scope

- `logos_core.py` model changes

## Definition of Done

- `make all` passes
EOF
create_issue "GFI-15" "feat(forge): add minimal CSV exporter" "help wanted,forge,enhancement" "$BODY_DIR/gfi15.md"

# GFI-16
cat > "$BODY_DIR/gfi16.md" <<'EOF'
## Context

README roadmap lists "Ollama Integration: One-click local RAG setup" with no linked design issue. This RFC captures scope before implementation.

## Objectives

- [ ] Add `docs/rfc/OLLAMA_RAG.md` (or section in COOKBOOK) describing:
  - Target user story (local vault → embeddings → Ollama chat)
  - Dependencies (`[ai]` extra, optional Ollama binary)
  - Proposed CLI or script entry point (e.g. `matryca-parse export` + sample pipeline)
  - Non-goals (no cloud, no telemetry)
- [ ] Link RFC from README roadmap item
- [ ] Break implementation into follow-up issues

## Files

- New: `docs/rfc/OLLAMA_RAG.md`
- `README.md`

## Getting started

1. Review `SynapseAdapter` and existing `export --format langchain` flow
2. Research Ollama embedding/chat APIs (document links)

## Out of scope

- Production Ollama integration code in this issue

## Definition of Done

- RFC merged; follow-up issues filed for implementation slices
EOF
create_issue "GFI-16" "docs: RFC Ollama one-click local RAG" "documentation,enhancement,help wanted" "$BODY_DIR/gfi16.md"

echo "---"
echo "Issue numbers written to $OUT"
cat "$OUT"
