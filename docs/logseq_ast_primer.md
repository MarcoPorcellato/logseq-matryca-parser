# 🧠 Logseq AST Primer: Understanding Spatial Markdown and the Logos Protocol

To contribute to or understand the **Logos Protocol**, you must first understand the idiosyncratic nature of Logseq's data structure. 

Logseq does not use standard Markdown; it uses an **Outliner-based Spatial Markdown**. 
Standard NLP text splitters and RAG chunkers destroy Logseq data because they parse text linearly. Logseq must be parsed **topologically**.

Here is the domain logic that the Logos Stack-Machine is built to handle.

---

## 1. The Outliner Paradigm (Spatial Indentation)

In standard Markdown, lists are just formatting. In Logseq, **indentation dictates the Abstract Syntax Tree (AST)**. The physical space defines the semantic parent-child relationship.

**Example:**

```markdown
- Strategy Meeting
  - Discussed Q3 goals
    - Marketing budget needs approval
  - Fired the PR agency
```

### The AST Translation

- **"Strategy Meeting" (Level 0)** is the Parent.
- **"Discussed Q3 goals" (Level 1)** is a Child. 

If you delete the parent, this child loses its context. Standard chunkers will split these lines into different vector embeddings, destroying the semantic link. The Logos engine preserves this topology via exact `parent_id` and `path` lineage.

**Empty bullets:** A bare `-` or `*` line (marker only) parses as an empty block instead of failing the bullet detector.

---

## 2. Block Properties (The Metadata Layer)

Logseq allows injecting metadata directly into blocks. These are not standard Markdown frontmatter, but inline key-value pairs that must immediately follow the block's first line.

**Example:**

```markdown
- Advanced RAG Architecture #[[AI]]
  id:: 6628ec8c-5544-486a-8d77-62860c239851
  collapsed:: true
  custom_state:: verified
  - First principle of data extraction...
```

### Parsing Rules for Logos

1. Properties (like `id::`) belong to the block above them and must appear **contiguously** immediately after the bullet line (or after other property lines in the same window).
2. If a **soft-break** plain-text line appears in the block body, the property window **closes**: later `key:: value` lines are **plain text**, not metadata — **unless** the line sits immediately after a closing code fence (Logseq contiguity exception).
3. Property keys are stored **lowercase** (`Title::` → `title`) to match Logseq’s case-insensitive Datomic attributes.
4. Outer **`"`** / **`'`** on property values are stripped in the AST.
5. Comma-separated **`tags::`**, **`alias::`**, **`aliases::`**, and **`page-tags::`** split on commas but **ignore commas inside `[[wikilink]]` tokens**.
6. They must be stripped from the raw text content to avoid polluting the AI's context window (`clean_node_content` uses case-insensitive matching).
7. The `id::` property is sacred: it overrides any deterministic UUID generation because it is the native anchor for Logseq's internal block-references `((uuid))`.

**Bullet-list property values** (Logseq-native):

```markdown
- Root block
  tags::
    - Alpha
    - Beta
```

When `key::` has no inline value, indented bullet children are absorbed into **`properties["tags"] == ["Alpha", "Beta"]`** — they do **not** become outline child nodes. List-shaped **`tags::`** / **`page-tags::`** values also feed implicit graph tokens on **`LogseqNode.refs`**.

---

## 3. Soft Breaks vs. Hard Breaks (Multiline Blocks)

A single block in Logseq can contain multiple lines of text without creating a new node. This is represented by `Shift+Enter` (soft breaks).

**Example:**

```markdown
- This is the first line of the block.
  This is the second line of the SAME block.
  - This is a new child block.
```

### Parsing Rules for Logos

If a line does not start with a bullet (`-` or `*`), and is not a property (`key:: value`), it is treated as a multiline continuation of the `current_node`.

**Ordered lists:** Lines matching `1. `, `12. `, etc. are treated as structural bullets with the same indentation rules as `-` and `*`.

**GFM checkboxes:** On the first line of a block, `[ ]`, `[-]`, and `[x]` / `[X]` map to `task_status` values `TODO`, `DOING`, and `DONE` respectively (checked before Org-mode prefixes).

**Org-mode task markers:** Prefixes such as `TODO`, `DOING`, `DELEGATED`, `POSTPONED`, and `IN-PROGRESS` (longest match first) set `task_status` and are removed from `clean_text`.

**Temporal markers:** `SCHEDULED` / `DEADLINE` payloads support time ranges (`HH:MM - HH:MM`, start time used), repeater tokens (`.+1w`, `++1d`), and Org warning periods (`-3d`) without parse failures.

**Aliased block references:** `[My Label](((block-uuid)))` resolves the UUID for `block_refs` but `clean_text` exposes only `My Label` (no square brackets).

**Wikilink anchors:** `[[Page#Section]]` resolves to **`Page`** only for graph routing (section header stripped).

---

## 4. Page Properties (Frontmatter) and Graph Indexing

Unlike block properties, **page properties** live at the **top of the file**, followed by a blank line before the first outline bullet. LOGOS accepts two formats at **read** time:

### Native Logseq frontmatter

Raw `key:: value` lines (no leading `- `):

```markdown
title:: Custom Title
alias:: Dev, Coding
tags:: parser, logseq

- First root block
```

### YAML frontmatter

A `---` delimited block at file start (common in tools that export YAML metadata):

```markdown
---
title: Custom Title
tags: parser, logseq
---

- First root block
```

Both map into **`LogseqPage.properties`** with **lowercase keys**. **`serialize_logseq_page`** is **format-preserving**: pages that began with `---` re-emit YAML frontmatter; otherwise the serializer writes native `key::` lines. **Obsidian FORGE** export may add YAML even on natively `key::` pages — that is a separate projection, not sovereign round-trip output.

**`page-tags::`** at page or block level is treated like **`tags::`** for implicit graph token injection.

### Parsing rules

1. Keys and values are stored in **`LogseqPage.properties`** with **lowercase keys**. A non-empty **`title`** property (YAML `title:` or `title::`) sets **`LogseqPage.title`** at parse time (overriding the filename-derived default). **`LogseqGraph.load_directory`** re-applies **`title::`** enrichment when indexing the vault.
2. **`alias::`** and **`aliases::`** accept comma-separated strings, **bullet-list** values (`alias::` followed by indented `-` lines), or Python `list` values after parse. Serialization strips `[[wikilink]]` and `#tag` adornments from each token.
3. Harvested page wikilinks/tags merge into **`LogseqPage.refs`** for graph indexing.

### Serialization round-trip

[`serialize_logseq_page`](../src/logseq_matryca_parser/logseq_markdown.py) rebuilds sovereign Spatial Markdown from a parsed **`LogseqPage`**:

| Behavior | Detail |
| :--- | :--- |
| **Page header** | YAML `---` preserved when `raw_content` started with `---`; else `key::` lines via `format_logseq_page_properties`. |
| **List block properties** | `tags::` / `page-tags::` (and ref keys) with list values emit `key::` plus indented `-` bullets — not Python repr. |
| **`:LOGBOOK:`** | Drawer blocks re-emit as `:LOGBOOK:` / `:END:`, not `logbook::` lines. |
| **Derived temporal keys** | `scheduled::`, `repeater::`, and related parsed fields are omitted from serialized `key::` output. |
| **Soft-break bodies** | Continuation lines keep single alignment at `parent + 2` spaces without double-indent. |
| **Block UUIDs** | Parse → serialize → parse preserves block UUIDs on the same outline (see `tests/test_pre_release_roundtrip.py`). |

### `LogseqGraph` enrichment

When you call **`LogseqGraph.load_directory`**, a post-parse pass:

- Applies **`title::`** → updates **`page.title`** and re-keys **`graph.pages`**
- Injects **alias keys** → `graph.pages["Dev"]` points to the same object as `graph.pages["Development"]`
- Builds **backlinks** so `[[Dev]]` resolves like a canonical page link
- Resolves **`get_page`** and relative links **case-insensitively** (Datomic parity)

See [Architecture §3.6](ARCHITECTURE.md#36-logseqgraph--namespace-scoping-o1-invalidation-live-watch) for the full pipeline.

**File encoding:** `parse_page_file` uses **`utf-8-sig`** so a UTF-8 BOM from Windows-synced files does not corrupt the first bullet.

---

## 5. Protected Regions (Dead Zones)

Logseq markdown often contains syntax that **looks** like links or tags but must not become graph entities:

| Region | Why it is shielded |
| :--- | :--- |
| Fenced / inline code | Literals such as `[[not-a-page]]` inside samples |
| LaTeX `$…$` and `$$…$$` | Equations may contain bracket-heavy notation |
| `#+BEGIN_QUERY` … `#+END_QUERY` | Datalog snippets reference `[[pages]]` symbolically |
| HTML comments `<!-- … -->` | Hidden markup must not emit ghost wikilinks |
| Escaped Markdown `\#`, `\[\[` | Backslash escapes must not become tags or wikilinks |
| `{{query}}` / `{{advancedquery}}` | Query macros must not harvest nested wikilinks |
| Org drawers (`:LOGBOOK:`, etc.) | System metadata, not prose |
| `{{embed [[Page]]}}` macros | Nested wikilinks inside embed bodies **are** extracted for the graph |

The LOGOS engine masks these spans before wikilink/tag/block-ref extraction (see `_shield_inline_code` in `logos_parser.py`). This keeps vector pipelines and backlink registries aligned with **human navigation intent**, not accidental token matches inside non-prose regions.

---

## 6. Assets and Multimodal Links

Logseq attachments are not wikilinks. During parse, **`_extract_assets`** collects local file references into **`LogseqNode.assets`**:

| Syntax | Example | Stored value |
| :--- | :--- | :--- |
| Markdown image | `![scan](../assets/scan.png)` | `../assets/scan.png` |
| PDF macro | `{{pdf report.pdf}}` | `report.pdf` |
| Local link | `[spec](../assets/specs.pdf)` | `../assets/specs.pdf` |

**Not assets:** `[Alias]([[Target Page]])` — that is a hybrid wikilink alias, not a filesystem attachment.

At page scope, **`LogseqPage.resolve_asset_path(link)`** maps a stored asset string to an absolute path (graph-root relative, percent-decoding, `/assets` fallback). Set **`graph_root`** on the page (via parse context) for resolution to succeed.

See [Architecture §3.1 — Asset extraction](ARCHITECTURE.md#asset-extraction-and-path-resolution) and the design note [`LOGSEQ_ASSET_RESOLUTION_SPEC.md`](design-docs/LOGSEQ_ASSET_RESOLUTION_SPEC.md).

---

## 7. The Matryca Moat: Why Standard RAG Fails

If you feed Logseq Markdown into `RecursiveCharacterTextSplitter` (LangChain) or similar naive chunkers:

- It splits blocks mid-sentence based on character count.
- It completely loses the parent-child indentation context.
- It ingests system properties (e.g., `collapsed:: true`) as semantic text, confusing the LLM.

The **Logos Protocol** solves this by walking the AST deterministically, isolating properties, shielding dead-zone literals, and using the `SYNAPSE` adapter to export native LangChain `Document` or LlamaIndex `TextNode` objects. Every generated object retains its exact hierarchical lineage in the metadata, feeding your local LLM perfectly structured data.

For vault-wide navigation (aliases, backlinks, namespace shadowing, assets), load the graph with **`LogseqGraph`** — see the [README](../README.md) and [CHANGELOG](../CHANGELOG.md) (graph parity from **v1.2.0**; **v1.2.1** adds CI/OSS hardening; **v1.2.2** fixes CodeQL CI and documents default setup).
