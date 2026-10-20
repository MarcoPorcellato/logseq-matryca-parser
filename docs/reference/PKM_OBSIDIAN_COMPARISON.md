---
type: PKMComparisonStudy
title: Obsidian, Logseq and Matryca Parser comparison
description: Source-backed comparison of local files, block identity, graph structure, metadata, automation and interoperability for the README PKM landscape.
status: draft
classification: active
audience: users_and_integrators
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-20
verified: 2026-10-20
stale_after: 2027-01-18
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Obsidian, Logseq and Matryca Parser: the useful differences

Obsidian is a local-file knowledge application with substantial native structure
and automation. Matryca Parser is a Python library that interprets **Logseq
Markdown block semantics** and exposes an AST and in-memory graph. Its useful
distinction is that specific data and integration contract, not a claim that
Obsidian lacks graphs, properties, queries or command-line tools.

This is the detailed source for the concise PKM landscape in the
[README](../../README.md). It is a workflow comparison, not a quality ranking,
benchmark or recommendation to migrate.

## Scope and evidence

Official product documentation was checked on **2026-10-20** in two independent
Luna Max research lanes, followed by source reconciliation in this repository.
Product facts are cited beside their claims; implications and workflow choices
below are synthesis. Live documentation can change, particularly CLI, Headless,
export and pricing behavior.

Parser implementation references use source
[`0f357160be3dd9c15ccd3600f112e60ae201b987`](https://github.com/MarcoPorcellato/logseq-matryca-parser/tree/0f357160be3dd9c15ccd3600f112e60ae201b987).
The [support matrix](CONFORMANCE_SUPPORT_MATRIX.md) and
[API stability contract](API_STABILITY.md) remain authoritative. This study adds
no runtime capability, stable API, release or compatibility certification.

## Compare the same layer

| Surface | What it is | What not to infer |
|---|---|---|
| Vanilla Markdown | A text format plus conventions chosen by tools | A graph, query engine, sync service or Git history is not supplied by the format |
| Logseq OG file graph | Logseq's file-based, block-oriented knowledge model | Its properties, UUID references and outline conventions are not interchangeable with every Markdown dialect |
| Obsidian | A note-taking application over local files, with core features and optional community plugins | Local Markdown does not mean absence of structure or app-specific syntax |
| Matryca Parser | A Python parser/graph library for Logseq Markdown | It is not an editor, hosted database, Obsidian runtime or replacement for either application's UI |
| Logseq DB | Logseq's DB-backed application model | An exported `.md` file is not necessarily a complete representation of the DB graph |
| Tana Outliner | A hosted outliner with node references, fields and supertags | Hosted storage does not mean that export is unavailable |

The Logseq OG distinction follows this project's
[AST primer](../logseq_ast_primer.md). DB and Tana qualifications are sourced
separately [below](#logseq-db-and-tana-context).

## Fundamental Obsidian differences

### 1. Local files are shared ground, not a competitive disadvantage

Obsidian keeps notes as plain-text Markdown in a local vault, alongside settings
and other files. Other editors can access the notes. The application maintains a
separate metadata cache for derived views. Optional synchronization does not turn
the local Markdown files into a proprietary working database.
[Official storage documentation](https://obsidian.md/help/data-storage).

Parser likewise treats Logseq Markdown as source and its graph as derived state.
Neither a local file nor an in-memory graph proves that a downstream AI model,
plugin or external service keeps data local. Those are separate integration
choices; see the [agent action contract](AGENT_ACTION_CONTRACT.md).

### 2. Hierarchy and graph granularity are different questions

Obsidian supports headings and nested Markdown lists. Its native Outline lists
headings, while Graph view primarily visualizes notes and their internal links,
with optional tag/attachment display. It is incorrect to call it structureless.
[Outline](https://obsidian.md/help/plugins/outline),
[Graph view](https://obsidian.md/help/Plugins/Graph%2Bview).

Parser models Logseq outline blocks as typed nodes with explicit parent, sibling
and path relations. This helps a Python consumer retain the enclosing context
of an individual block rather than treating a note as an undifferentiated
string. This is a model/integration distinction, not evidence that one graph
visualization is better than another. See the
[AST primer](../logseq_ast_primer.md) and [architecture contract](../CLEAN_CODE_ARCHITECTURE.md).

### 3. Block references exist in both ecosystems, with different identities

Obsidian supports file, heading and block links. A block can have a `^block-id`
anchor and be addressed through `[[Note#^block-id]]`. These anchors are optional
and Obsidian-specific, not standard Markdown. Do not describe every Obsidian
block as requiring a persistent UUID.
[Internal links](https://obsidian.md/help/links).

Note aliases and Backlinks are native too. Both ecosystems have reverse links;
the distinguishing question here is identity and block context, not the mere
presence of linking. [Backlinks](https://obsidian.md/help/plugins/backlinks),
[aliases in Properties](https://obsidian.md/help/properties).

Logseq OG uses explicit `id::` UUID properties and `((uuid))` block references.
Parser preserves explicit identities and derives identities where its contract
requires them. Generated identities should not be mistaken for persistent UUID
properties present in every source block. The
[semantic projection and identity policy](../../tests/parser_assurance/projection.py)
define which identity comparisons are meaningful.

Illustrative syntax, **not generated export or conversion-test evidence**:

```markdown
- TODO Review plan
  id:: 11111111-1111-4111-8111-111111111111
- Revisit ((11111111-1111-4111-8111-111111111111))
```

```markdown
- [ ] Review plan ^review-plan

Revisit [[Plan#^review-plan]].
```

Matching the visible reference syntax does not by itself preserve task states,
outline relations, metadata or application behavior.

### 4. Metadata is native in Obsidian; its default unit differs

Obsidian Properties stores typed note metadata in YAML frontmatter, including
aliases, tags, links, numbers, dates and checkboxes. This is a native feature,
not something that always requires a community plugin.
[Properties](https://obsidian.md/help/properties).

Parser exposes Logseq page and block properties and the documented
`get_effective_properties` ancestor/page merge. A note-level YAML field is not
automatically equivalent to a value attached to one nested Logseq block. Use
the [Cookbook](../COOKBOOK.md) and [AST primer](../logseq_ast_primer.md) for actual
property and inheritance contracts; do not infer cross-app schema equivalence.

### 5. Queries and tasks are not absent from Obsidian

Core Search includes property, block, section and task operators. Core Bases
provides views and formulas over files and properties; in its table view a row
is a file. View definitions can be stored in `.base` files. These are native
capabilities, not evidence that Obsidian requires a separate working-note DB.
[Search](https://obsidian.md/help/plugins/search),
[Bases](https://obsidian.md/help/bases).

Dataview and Tasks add community query/task workflows. They are separately
installed plugins, not core features and not the only way to query or inspect
tasks. [Dataview listing](https://community.obsidian.md/plugins/dataview),
[Tasks listing](https://community.obsidian.md/plugins/obsidian-tasks-plugin).

Parser provides Python graph access and typed Logseq task/timestamp data; it
does not execute arbitrary Obsidian plugin queries or promise equivalence with
Logseq DB queries. Select the relevant data model before comparing query power.

### 6. A visual canvas is not the same artifact as a parsed outline

Obsidian Canvas is a core visual workspace. Its `.canvas` files use the open
JSON Canvas format and are distinct from Markdown notes. It should not be
described as a proprietary binary format or equated with the note-link graph.
[Canvas](https://obsidian.md/help/plugins/canvas).

Parser's optional, experimental LENS visualization is a reference-topology view,
not a Canvas importer, layout-preserving converter or interactive editor.
Its compatibility and transition boundary remain in
[API stability](API_STABILITY.md#experimental-package-root-surface).

### 7. Obsidian has current APIs, CLI and headless services

The official TypeScript plugin API exposes app services; the Vault API supports
file access. It is not correct to say Obsidian has no programmatic interface.
[Official API](https://github.com/obsidianmd/obsidian-api),
[Vault developer guide](https://docs.obsidian.md/Plugins/Vault).

The current official CLI supports search, backlinks, tasks, properties and Bases
queries. It controls a running Obsidian app and can launch the app when needed;
the documented installer requirement applies. Obsidian Headless is a separate
**open-beta** client for Sync and Publish that runs without the desktop app.
Do not extend that service-client contract into a claim of full headless editor
or plugin-runtime parity. [CLI](https://obsidian.md/help/cli),
[Headless](https://obsidian.md/help/headless).

Parser instead supplies a Python library and CLI that do not require a running
note-taking application. This is useful for Logseq-specific scripts and services.
It is not a claim that Obsidian lacks automation, or that this study verified a
standalone Obsidian Python AST/graph interface.

### 8. Git, recovery, sync and backup are separate mechanisms

Local Markdown can participate in a Git workflow, but neither the format nor
Parser supplies commits, conflict resolution or a backup policy. Avoid calling
version control “perfect.” Obsidian's core File Recovery keeps local snapshots;
optional Sync provides remote version history. File Recovery explicitly is not
a complete backup solution.
[Storage/Git guidance](https://obsidian.md/help/data-storage),
[File Recovery](https://obsidian.md/help/plugins/file-recovery),
[Sync history](https://obsidian.md/help/Obsidian%2BSync/Version%2Bhistory).

The app is currently free to use, including commercial use; Sync and Publish are
optional paid services, and commercial-support licenses are optional. Consult
current terms rather than fixing prices in this README or treating optional
services as mandatory. This is a product-policy observation, not legal advice.
[Current pricing and FAQ](https://obsidian.md/pricing).

### 9. AI capability must be described by an integration contract

It is not meaningful to score a file format “low AI” and an app or parser
“high AI” without a workload and measurements. Parser's specific contribution
is retaining Logseq outline/identity context for consumers, including optional
lineage-aware LangChain exports. Model selection, embeddings, retrieval quality,
network use and write authority remain consumer decisions.
[Support matrix](CONFORMANCE_SUPPORT_MATRIX.md#optional-integration-matrix),
[agent action contract](AGENT_ACTION_CONTRACT.md).

Obsidian's APIs and plugins make integrations possible; that does not establish
one uniform AI, privacy or retrieval guarantee. No comparative AI-quality,
performance, memory or reliability benchmark was run for this study.

## Obsidian export is not a native Obsidian input contract

The maintained CLI can write derived Obsidian-compatible Markdown, including
YAML frontmatter and block anchors, to a caller-selected destination. Python
exporter classes remain experimental. See the
[export implementation](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/0f357160be3dd9c15ccd3600f112e60ae201b987/src/logseq_matryca_parser/kinetic_export.py#L99-L131),
[usage examples](../../README.md#usage) and [API stability](API_STABILITY.md).

That does **not** establish:

- a documented native Obsidian-vault loader or support for every Obsidian extension;
- `.base`, `.canvas`, community-plugin data or settings migration;
- lossless bidirectional Obsidian–Logseq conversion or synchronization;
- identical behavior after moving tasks, queries, embeds, properties or assets.

Conversely, “no native vault contract” does not mean all Obsidian Markdown is
unparseable: an existing
[frontmatter regression](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/0f357160be3dd9c15ccd3600f112e60ae201b987/tests/test_logos_parser.py#L550-L557)
accepts Obsidian-style YAML. Supported fragments are not whole-ecosystem conformance.
Work on a copy and verify syntax, identity, links and assets for a real migration.

## Logseq DB and Tana context

Logseq DB documents nodes, typed properties, queries, desktop SQLite storage,
CLI and scripting. Official exports include SQLite and EDN, while standard
Markdown export does not retain all properties/timestamps. Parser does not
currently claim native DB loading; exported text must be assessed on its actual
semantics, not its extension.
[DB documentation](https://github.com/logseq/docs/blob/master/db-version.md),
[official CLI contract](https://github.com/logseq/logseq/blob/master/docs/cli/logseq-cli.md).

Here “Tana” means **Tana Outliner**, not every product under the brand. Its docs
describe outline/node references, fields, supertags, search nodes and integrations.
Its privacy overview identifies hosted Google Cloud storage. Markdown and JSON
exports are available; the Markdown ZIP excludes media, which requires separate
retrieval. This supports a storage/portability distinction, not “no export” or
an unsupported assertion that history/offline operation never exists.
[Getting started](https://outliner.tana.inc/help/getting-started),
[export limits](https://outliner.tana.inc/help/import-and-export),
[storage overview](https://outliner.tana.inc/pages/terms-privacy-security).

## Workflow implications — synthesis, not a product ranking

- For interactive Markdown notes, native links, views and an existing plugin
  ecosystem, evaluate Obsidian on those application features; Parser is not a
  substitute for that UI.
- For Python processing of a **Logseq OG Markdown** graph where enclosing blocks,
  explicit UUID references and inherited metadata matter, Parser offers the
  specific integration surface documented here.
- For a DB-backed or hosted workspace, assess native features and export fidelity
  directly. A text export is a starting point for conversion, not proof of parity.
- For cross-app use, identify the required subset first. Keep original files,
  compare semantic projections, and qualify actual output rather than assuming
  that a shared `.md` extension makes applications interchangeable.

The [313-document Logseq report](../quality/OFFICIAL_LOGSEQ_MARKDOWN_COMPATIBILITY_2026-10-10.md)
concerns its selected Logseq snapshot and stated checks. It is not Obsidian,
Logseq DB or Tana compatibility evidence, nor proof of arbitrary Markdown support.
The experimental private Org reader does not change this boundary.

## Maintenance and unverified scope

Recheck CLI/Headless lifecycle, native/plugin status, export behavior and optional
service policy before extending this comparison or after product changes.
No apps or plugins were installed, no external vaults were imported, and no
cross-app conversion was executed by this research. Product behavior is described
from cited official documentation; implementation-specific observations are
limited to the pinned Parser source. Publication and runtime qualification of
future integrations require separate evidence and authority.
