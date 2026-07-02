# Integration cookbook

Copy-paste recipes for common **Logseq Matryca Parser** workflows. All snippets assume you installed the package and synced extras:

```bash
uv sync --all-extras
```

Imports use the stable package root (`logseq_matryca_parser.__all__`). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for module roles and [`logseq_ast_primer.md`](logseq_ast_primer.md) for Spatial Markdown rules.

---

## Recipe 1 — Single page → LangChain documents

Parse one `.md` file and emit lineage-aware `Document` objects for embedding pipelines.

```python
from logseq_matryca_parser import LogosParser, SynapseAdapter

page = LogosParser().parse_page_file("pages/My Page.md")

docs = SynapseAdapter.to_langchain_documents(
    page.root_nodes,
    source_name=page.title,
)

for doc in docs[:3]:
    print(doc.page_content)
    print(doc.metadata.get("parent_id"), doc.metadata.get("path"))
```

**CLI equivalent:**

```bash
matryca-parse export /path/to/graph output --format langchain
```

Requires optional `[ai]` extra (`uv sync --extra ai`).

---

## Recipe 2 — Load vault + fluent graph query

Build the in-memory graph index (pages, backlinks, node registry) and filter blocks topologically.

```python
from logseq_matryca_parser import LogseqGraph

graph = LogseqGraph.load_directory("/path/to/logseq/graph")

hits = (
    graph.query()
    .has_tag("idea")
    .is_task_state("TODO")
    .execute()
)

for node in hits:
    print(node.clean_text, "←", graph.get_effective_properties(node.uuid))
```

**Tips:**

- `graph.get_page("my page")` is case-insensitive (Datomic / Logseq parity).
- `graph.get_broken_references()` flags `((uuid))` refs missing from the registry.
- Iterate `graph.iter_canonical_pages()` when exporting or counting pages — alias keys share the same `LogseqPage` instance.

---

## Recipe 3 — Live filesystem watcher (incremental reload)

Re-parse only the page that changed under `pages/` or `journals/` instead of cold-reloading the vault.

```python
from logseq_matryca_parser import LogseqGraph

graph = LogseqGraph.load_directory("/path/to/logseq/graph")

observer = graph.start_watching()  # requires [watch] extra

# ... your app runs; on change, the graph invalidates and reloads that file ...

observer.stop()
observer.join()
```

Install the watcher extra:

```bash
uv sync --extra watch
```

Debouncing (~500ms) and editor temp-file ignores are built in — see [Architecture §3.6 — Live watch](ARCHITECTURE.md#36-logseqgraph--namespace-scoping-o1-invalidation-live-watch).

---

## Recipe 4 — Agent read / write (X-Ray + headless splice)

Compress context for LLM agents, then append a child block without Logseq's HTTP API.

```bash
matryca-parse agent-read /path/to/graph --tag idea
matryca-parse agent-write /path/to/graph --alias 0 --content "Follow-up from the agent"
```

The alias map is persisted at `.matryca_xray_state.json` in the graph root between CLI invocations.

---

## Recipe 5 — Canonical pages & strict reference lint

Avoid duplicate exports when alias keys point at the same page, and fail fast on broken block refs.

```python
from logseq_matryca_parser import LogseqGraph

# Optional: raise BlockReferenceError when any ((uuid)) is missing after load
graph = LogseqGraph.load_directory("/path/to/logseq/graph", strict_refs=True)

for page in graph.iter_canonical_pages():
    owner = graph.page_for_node(page.root_nodes[0])
    assert owner is page

broken = graph.get_broken_references()
if broken:
    for node in broken:
        print("broken ref in", node.clean_text)
```

**CLI tip:** `matryca-parse scan /path/to/graph --broken-refs` prints a Rich table of unresolved refs and exits `1` for CI (since v1.5.0). For programmatic checks, use `graph.get_broken_references()` as above.

**CLI tip:** run `matryca-parse export` after `load_directory` — KINETIC scans canonical pages internally (since v1.4.0).

---

## Recipe 6 — Contributor test patterns

Pick a scoped task from [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) (wave 2: [#43](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/43)–[#52](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/52)), then mirror nearby tests:

```bash
uv sync --all-extras
make all   # 378 pytest cases, ≥80% coverage gate
```

| Pattern | Example module | Test file |
| :--- | :--- | :--- |
| Pure helper | `normalize_logseq_timestamp` | `tests/test_logos_parser.py` |
| CLI `--help` / errors | `kinetic.py` | `tests/test_kinetic.py` |
| FORGE visitor | `ObsidianForgeVisitor` | `tests/test_forge.py` |
| Release script | `scripts/extract_changelog.py` | `tests/test_extract_changelog.py` |
| Exception hierarchy | `exceptions.py` | `tests/test_exceptions.py` |

Test-only PRs should not change runtime behavior — update `CHANGELOG.md` under `[Unreleased]` only when user-visible behavior changes.

---

## Related

| Resource | Link |
| :--- | :--- |
| Quickstart | [`README.md`](../README.md) |
| Live demo script | [`examples/run_demo.py`](../examples/run_demo.py) |
| First contributions | [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) |
| Full architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Clean Architecture (Uncle Bob) | [`CLEAN_CODE_ARCHITECTURE.md`](CLEAN_CODE_ARCHITECTURE.md) |
| v1.6 roadmap & triage | [`quality/GITHUB_CLEAN_ARCH_ROADMAP.md`](quality/GITHUB_CLEAN_ARCH_ROADMAP.md) |
