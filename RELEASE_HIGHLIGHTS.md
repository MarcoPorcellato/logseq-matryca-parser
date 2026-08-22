# Release highlights

This page preserves the reader-focused highlights for each documented release.
For the exhaustive change history, see the [changelog](CHANGELOG.md). For
published artifacts and attestations, see
[GitHub Releases](https://github.com/MarcoPorcellato/logseq-matryca-parser/releases).

## v1.8.1

Patch release — removes pathological parser work growth, corrects incremental backlink
reloads, and adds reproducible assurance evidence. **No intentional breaking
changes** to stable package imports or CLI behavior.

| Area | Change |
| :--- | :--- |
| **Parser correctness and work** | Valid 1024-level outlines stay iterative; derived metadata is finalized once per node; strict-reference state is page-local; returned-node registry identity is preserved. |
| **Incremental graph reloads** | Delete and filesystem-move identity changes reindex affected backlinks to match a cold load without rebuilding the global backlink registry. This is a bounded #103 correctness slice, not the complete concurrency contract. |
| **Runtime evidence** | A deterministic offline synthetic-vault generator and source-free runner establish repeatable parser, graph, search, and optional SYNAPSE observations. #111 remains open for explicit vault-scale budgets. |
| **Parser internals** | Private lexical state now owns eligibility transitions while reduction, AST construction, semantic enrichment, identities, and public behavior remain in the parser. #108 remains open. |
| **Test suite** | **692** pytest cases with **89.82%** coverage at release preparation. |

## v1.8.0

Minor release — adds project-owned parser assurance, bounded local graph checks,
and stronger release supply-chain evidence. **No intentional breaking changes**
to stable package imports or CLI behavior.

| Area | Change |
| :--- | :--- |
| **Parser assurance** | Versioned compatibility fixtures, deterministic adversarial cases, work-growth evidence, and one-based source-line contracts protect semantics without adopting an external parser oracle. |
| **Local graph assurance** | New bounded `matryca-parse assure` command runs in a fresh worker and emits aggregate-only results without retaining vault content, paths, titles, UUIDs, or exception text. |
| **Parser internals** | The first private line-classification phase preserves parser reduction, identities, public imports, and dependencies. |
| **Supply chain** | Release jobs produce a CycloneDX SBOM, dependency/license inventory, checksums, and provenance attestations for the exact published distributions. |

## v1.7.1

Patch release — completes the promised SYNAPSE example and closes the security
alerts found during v1.7.0 post-release verification. **No intentional breaking
changes** to package APIs or CLI behavior.

| Area | Change |
| :--- | :--- |
| **SYNAPSE RAG** | New offline [`examples/run_synapse_rag.py`](examples/run_synapse_rag.py) exercises LangChain, LlamaIndex, context enrichment, and resolved page-embed expansion. |
| **Release integrity** | Release notes now fail validation when a repository-local link is missing or escapes the source tree. |
| **Dependency security** | Optional AI/development resolution constrains `aiohttp>=3.14.3` and `setuptools>=83.0.0`; base runtime dependencies are unchanged. |
| **Test suite** | **532** pytest cases with **91.90%** coverage. |

## v1.7.0

Minor release — repository-wide correctness, safety, API, documentation, and
release-engineering hardening. **No intentional breaking changes** to default
CLI behavior or stable package exports.

| Area | Change |
| :--- | :--- |
| **Correctness** | Arbitrary-depth immutable parser refreshes preserve ordering, identity, properties, soft breaks, fences, and round trips. |
| **Diagnostics and graph** | Stable structured findings, JSON output, deterministic title-collision diagnostics, and opt-in strict rejection. |
| **Writer security** | Vault containment, symlink and target-identity checks, metadata preservation, dry-run patches, and bounded writes. |
| **Public package** | PEP 561 `py.typed`, documented API stability tiers, root exports, signature tests, and wheel/downstream Mypy contracts. |
| **Documentation** | English maintained-document profile, authority and lifecycle metadata, deterministic link/freshness validation, and Matryca Knowledge federation guidance. |
| **Release integrity** | One checksummed wheel/sdist build is reused for attested PyPI publication and GitHub Release assets. |
| **Test suite** | **528** pytest cases with **91.81%** coverage. |

## v1.6.0

Minor release — Clean Architecture v1 structural slices, new public graph APIs, layer-boundary CI, and documentation SSOT. **No intentional breaking changes** to existing `matryca-parse` CLI behavior or stable package exports.

| Area | Change |
| :--- | :--- |
| **Clean Architecture** | Clean Architecture SSOT, extracted KINETIC subcommands, and strategy pattern for embed expansion. |
| **Public APIs** | Public graph iterator `LogseqGraph.iter_attached_nodes()` and DIP path check `LogseqGraph.is_tracked_markdown_path()`. |
| **Quality & CI** | Layer-boundary CI tests and `make vendor-name-check` documentation gate. |
| **Test suite** | **456** pytest cases. |

## v1.5.0

Minor release — CLI vault hygiene for broken block references. **No intentional
breaking changes** to default `scan` behavior (`--broken-refs` is opt-in).

| Area | Change |
| :--- | :--- |
| **KINETIC `scan`** | New `--broken-refs` flag prints unresolved `((uuid))` refs in a Rich table and exits `1` for CI pipelines ([#77](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/77)). |
| **Test suite** | **451** pytest cases (**+1** vs v1.4.2). |

## v1.4.2

Patch release — agent-write and SYNAPSE correctness fixes. **No intentional
breaking changes** to public APIs.

| Area | Change |
| :--- | :--- |
| **agent-write** | Headless splice normalizes files missing a final newline; corrupt `.matryca_xray_state.json` yields a controlled CLI exit ([#72](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/72), [#60](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/60)). |
| **SYNAPSE RAG** | Cyclic `{{embed [[Page]]}}` chains truncate at the re-entrant edge without duplicating parent literal text ([#65](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/65)). |
| **Test suite** | **450** pytest cases (**+72** vs v1.4.1): wave 2 community coverage ([#58](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/58)) plus regression tests for the three fixes. |

## v1.4.1

Patch release — contributor test coverage and onboarding refresh. **No
intentional changes** to parser, graph, or CLI runtime behavior.

| Area | Change |
| :--- | :--- |
| **Test suite** | **378** pytest cases (**+107** vs v1.4.0): `normalize_logseq_timestamp`, `clean_node_content`, `logseq_paths` fallbacks, exception hierarchy, `extract_changelog` script, KINETIC `--help`, `agent-read --query`, direct `ObsidianForgeVisitor` tests ([#42](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/42)). |
| **New test modules** | `tests/test_exceptions.py`, `tests/test_extract_changelog.py`. |
| **Contributor index** | [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md) wave 2 ([#43](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/43)–[#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52)); wave-1 items marked complete. |

## v1.4.0

Minor release — graph integrity, export hygiene, and parser hardening from the
local static-analysis bug hunt (waves 1–8). No intentional breaking changes to
default parse behavior.

| Area | Change |
| :--- | :--- |
| **Graph index** | **`iter_canonical_pages()`** and **`page_for_node()`** deduplicate alias keys; **`load_directory`** rebuilds **`_node_registry`** from indexed pages only (no ghost nodes after title collision). |
| **Case-insensitive queries** | **`search_content`**, **`GraphQuery.has_tag`**, and **`get_nodes_by_tag`** match tags case-insensitively (optional `#` prefix). |
| **Live watcher** | **`LogseqGraphWatcher`** handles **`on_deleted`** and **`on_moved`**; **`invalidate_and_reload_page`** purges registries when a page file was deleted. |
| **Agent writes** | **`append_child_to_node`** calls **`invalidate_and_reload_page`** so the in-memory graph matches disk after headless splice. |
| **SYNAPSE** | Page/block embed expansion uses **`get_page`** (case-insensitive) and fail-safe empty replacement (no infinite loops on unresolved embeds). |
| **Serialization** | Per-page **`tab_size`** at parse time; **`serialize_logseq_page`** and **`append_child_to_node`** preserve four-space vault indentation. |
| **Paths & assets** | **`resolve_relative_page_link`** supports **`../`** / **`./`**; **`resolve_asset_path`** rejects absolute paths and links that escape the graph root. |
| **Strict refs** | **`LogseqGraph.load_directory(strict_refs=True)`** validates cross-page block refs via **`raise_if_broken_references()`**. |
| **Docs & community** | [`docs/COOKBOOK.md`](docs/COOKBOOK.md), [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md), [`docs/BUG_HUNT_REPORT.md`](docs/BUG_HUNT_REPORT.md) (audit complete). |

## v1.3.1

Patch release — aligns example and skill install docs with the project's **`uv`**
workflow. No parser or public API changes.

| Area | Change |
| :--- | :--- |
| **Examples** | `examples/run_demo.py` error hint uses **`uv sync --all-extras`**. |
| **Claude skill** | **`claude-skill-logseq-read/SKILL.md`** recommends **`uv pip install`**. |

## v1.3.0

Minor release — architectural quick wins, runtime robustness, and expanded
public API. No breaking changes to default parser behavior.

| Area | Change |
| :--- | :--- |
| **Public API** | Root **`logseq_matryca_parser`** exports **`SynapseAdapter`**, **`SessionAliasRegistry`**, **`GraphVisualizer`**, **`discover_graph_files`**, and core LOGOS symbols via explicit **`__all__`**. |
| **Graph model** | **`LogseqGraph`** uses **`validate_assignment=True`** instead of frozen/`object.__setattr__` for incremental reloads. |
| **Live watcher** | **`start_watching()`** debounces filesystem events (~500ms) and ignores editor temp/swap files (`.swp`, `~`, `.tmp`, `.DS_Store`). |
| **Strict refs** | **`StackMachineParser(strict_refs=True)`** raises **`BlockReferenceError`** for unresolved same-page `((uuid))` refs (default off). |
| **SYNAPSE** | **`SynapseMetadata`** / **`build_synapse_metadata`** for vector-store-safe fields; **LlamaIndex** adds **`SOURCE`**, **`NEXT`**, **`PREVIOUS`** relationships. |
| **KINETIC CLI** | Global **`--verbose`** / **`--graph`** via **`@app.callback()`**; optional-dependency hints recommend **`uv sync --extra ai\|viz`**. |
| **LENS** | Lazy-imports NetworkX/PyVis so core installs stay lightweight. |
| **Security** | Transitive **`aiohttp`** / **`nltk`** constraints for optional **`[ai]`** extras. |

## v1.2.2

Patch release — fixes a failing CodeQL GitHub Actions workflow; **no parser or
public API changes**.

| Area | Change |
| :--- | :--- |
| **CodeQL** | Removed duplicate `.github/workflows/codeql.yml`; scanning continues via GitHub **default setup** (Node 24 runners). |
| **Docs** | New [`docs/CODEQL.md`](docs/CODEQL.md) explains default vs advanced setup and troubleshooting. |

## v1.2.1

Infrastructure and contributor experience — no parser API breaks.

| Area | Capability |
| :--- | :--- |
| **Python matrix** | CI and PyPI pre-flight test **3.12** and **3.13**; PyPI classifier for 3.13. |
| **Quality gates** | `make all` parity in GitHub Actions (`uv sync --all-extras` → lint, mypy, pytest with **≥80%** coverage). |
| **Security** | GitHub CodeQL default setup (SAST), `pip-audit` on production deps, expanded `SECURITY.md`, PyPI publish blocked until pre-flight passes. |
| **Community** | `CODE_OF_CONDUCT.md`, `CODEOWNERS`, issue-template config, CONTRIBUTING with `uv` workflow. |
| **Docs** | Root `ROADMAP_*.md` consolidated under [`docs/roadmaps/`](docs/roadmaps/). |

Contributor setup: [`CONTRIBUTING.md`](CONTRIBUTING.md) ·
[`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md) · Security:
[`SECURITY.md`](SECURITY.md) · CodeQL: [`docs/CODEQL.md`](docs/CODEQL.md)

## v1.2.0

### Graph parity, assets, and parser hardening

| Area | Capability |
| :--- | :--- |
| **Asset extraction** | `LogseqNode.assets` collects markdown images, `{{pdf}}` macros, and local `[label](path)` attachments; `LogseqPage.resolve_asset_path` maps to absolute paths (`%20` decode, graph-root relative). |
| **YAML frontmatter** | `---` blocks at file start populate `LogseqPage.properties` like native `key::` lines; **`title:`** in YAML sets `page.title` at parse; **`serialize_logseq_page`** preserves `---` fences on round-trip when the source file used YAML. |
| **`page-tags::`** | Block and page `page-tags::` inject implicit graph tokens like `tags::`; list-shaped values feed `refs`. |
| **Case-insensitive routing** | `LogseqGraph.get_page` and `resolve_relative_page_link` resolve titles via a lowercase index (Datomic parity). |
| **Extended shielding** | HTML comments, `{{query}}` / `{{advancedquery}}`, and escaped `\#` / `\[\[` do not emit false graph tokens (embed macros still harvest nested wikilinks). |
| **Property & temporal fixes** | Comma-split ignores commas inside `[[wikilinks]]`; properties after code fences; quoted value stripping; `SCHEDULED`/`DEADLINE` ranges, repeaters, and Org warning periods; legacy `___` / `%2F` / Dendron filenames; UTF-8 BOM via `utf-8-sig`. |

### Round-trip serialization

| Area | Capability |
| :--- | :--- |
| **Soft-break bodies** | Multiline block continuations serialize without double-indenting alignment spaces. |
| **List-shaped block props** | `tags::` / `page-tags::` with indented `-` bullets round-trip as Logseq lists (not Python repr). |
| **`:LOGBOOK:` drawers** | Org drawers re-emit as `:LOGBOOK:` / `:END:` blocks, not bogus `logbook::` property lines. |
| **Derived temporal keys** | Parsed `scheduled::`, `repeater::`, and related derived fields are omitted from serialized `key::` output. |
| **Stable block UUIDs** | Parse → `serialize_logseq_page` → parse preserves block `id::` / UUIDs on the same outline. |

```python
from logseq_matryca_parser.graph import LogseqGraph
from logseq_matryca_parser.logos_parser import LogosParser

graph = LogseqGraph.load_directory("/path/to/logseq/graph")

# Case-insensitive page lookup
page = graph.get_page("my page")  # same object as graph.pages["My Page"]

# Assets on a parsed block (Vision / document pipelines)
single = LogosParser().parse_page_file("pages/Notes.md")
block = single.root_nodes[0]
if block.assets:
    abs_path = single.resolve_asset_path(block.assets[0])
```

Deep dive: [Architecture §3.1 — LOGOS](docs/ARCHITECTURE.md#31-logos--deterministic-stack-machine-parsing) ·
[§3.6 — LogseqGraph](docs/ARCHITECTURE.md#36-logseqgraph--namespace-scoping-o1-invalidation-live-watch) ·
[AST primer](docs/logseq_ast_primer.md).

### Still included from v1.1.1

| Area | Capability |
| :--- | :--- |
| **Graph index** | `title::` / `TITLE::` overrides filename titles; `alias::` / `aliases::` inject extra `graph.pages` keys. |
| **Backlinks** | `[[Dev]]` resolves against alias keys (`get_backlinks("Dev")`). |
| **Incremental reload** | `invalidate_and_reload_page` re-applies title/alias enrichment after watcher edits. |
| **Parser shields** | LaTeX, `#+BEGIN_QUERY`, fenced code, drawers; `{{embed [[Page]]}}` harvests nested wikilinks. |
| **Property contiguity** | `key::` contiguous under bullets; soft-break closes the window (fence exception in v1.2.0). |
| **Tasks & bullets** | GFM checkboxes, extended Org markers, ordered-list bullets, aliased `((uuid))` clean text. |

### Obsidian-native export

Compile an entire Logseq graph into an **Obsidian vault layout**: YAML
frontmatter from page properties, list body preserved, Logseq `((uuid))` links
rewritten to **`[[Page#^anchor]]`**, and trailing **`^block-id`** on referenced
blocks. Namespace titles become nested folders (for example,
`Projects/AI/Demo.md`).

```bash
matryca-parse export /path/to/logseq/graph /path/to/obsidian/vault --format obsidian
```

> **Note:** Wikilinks currently use the **Logseq page title** (for example,
> `[[Target#^…]]`). Vault files may live under namespace folders
> (`Projects/AI/Demo.md`). Obsidian usually resolves unique titles; aligning link
> text to folder paths is a possible future refinement.

### Live incremental watcher

`LogseqGraph` supports **surgical file invalidation** (optional dependency:
`uv sync --extra watch`). `start_watching()` runs a recursive **watchdog**
observer with **~500ms debounce** and ignores editor temp/swap files (`.swp`,
`~`, `.tmp`, `.DS_Store`). On `created`, `modified`, `deleted`, or `moved`
events under `pages/` or `journals/`, only the affected file is re-parsed or
purged; stale synthetic UUIDs are removed from `_node_registry` and scrubbed
from `_backlink_registry`—no full-graph cold reload.

### Fluent topological queries

Filter the global node registry with a chainable API:

```python
from logseq_matryca_parser.graph import LogseqGraph

graph = LogseqGraph.load_directory("/path/to/logseq/graph")
hits = (
    graph.query()
    .has_tag("idea")
    .under_parent("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    .is_task_state("TODO")
    .execute()
)
```

### Agent-native X-Ray mode (token optimization)

For autonomous LLM agents, passing raw Markdown into the context window wastes
thousands of tokens on **36-character UUIDs**, hidden `id::` properties,
drawers, and collapsed directives that carry no immediate semantic signal.
**X-Ray mode** compresses the parsed AST into **ultra-dense, zero-fluff plain
text**: each block becomes `{indent}[{alias}] {clean_text}`, with heavy Logseq
UUIDs replaced by **sequential integer aliases** (`[0]`, `[1]`, …) held in a
session registry. On typical outlines this can reduce context consumption by
**up to ~35×** compared to dumping full block payloads.

```bash
matryca-parse agent-read /path/to/graph --tag idea
matryca-parse agent-read /path/to/graph --query "quantum"
```

The agent reads cheap topology now; the registry resolves aliases back to
sovereign UUIDs when you wire targeted writes.

### Headless write engine and AST linter (Wave 12)

The parser is **no longer read-only**. Wave 12 adds a **headless Markdown
splicer** ([`agent_writer.py`](src/logseq_matryca_parser/agent_writer.py)):
`append_child_to_node` uses AST line numbers and indentation
(`(indent_level + 1) × tab_size`) to insert a new bullet **atomically** into the
sovereign `.md` file—via `tempfile` + `os.replace`—without Logseq's fragile HTTP
API. Beyond surgical node splicing, the engine supports **full bidirectional
page generation** through
[`serialize_logseq_page`](src/logseq_matryca_parser/logseq_markdown.py) and
[`write_logseq_page`](src/logseq_matryca_parser/logseq_markdown.py), rebuilding
entire Logseq-compliant `.md` pages from an in-memory AST. Pair **`agent-read`**
with **`agent-write`**: X-Ray persists its alias map to
`.matryca_xray_state.json` at the graph root so stateless CLI invocations can
read, then write in sequence.

```bash
matryca-parse agent-read /path/to/graph --tag idea
matryca-parse agent-write /path/to/graph --alias 0 --content "Follow-up from the agent"
```

For graph hygiene, **`LogseqGraph.get_broken_references()`** flags nodes whose
`((uuid))` block refs point at missing registry targets—structural linting, not
regex guessing. The CLI exposes the same check through
`matryca-parse scan /path/to/graph --broken-refs` and exits `1` when broken
references exist.
