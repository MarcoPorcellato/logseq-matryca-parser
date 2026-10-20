---
type: ImplementationRecord
title: Logseq Markdown dataset candidates
description: Research-backed public sources that may broaden file-graph Markdown compatibility evidence, with provenance and reuse limits.
status: stable
classification: active
audience: integrators
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-10
verified: 2026-10-10
stale_after: 2027-01-08
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Logseq Markdown dataset candidates

**Evidence date:** 2026-10-10

**State:** Research shortlist only; no new source files were admitted, downloaded, copied, generated, or parsed.

**Purpose:** Identify sources that could add meaningful syntax and graph diversity to the bounded compatibility evidence in the [official Logseq Markdown report](OFFICIAL_LOGSEQ_MARKDOWN_COMPATIBILITY_2026-10-10.md).

## Recommendation

Keep the tested [`logseq/docs` snapshot](https://github.com/logseq/docs/tree/08f855f24d66e4509b7ea808554c13b4649e6ee1) as the baseline and deduplication control: the completed campaign records 313 selected Markdown files totaling 542,495 bytes at that exact revision. The best next *fixture-design* source is Logseq’s pinned OG-import test generator, not a ready-to-admit corpus. Its source describes nine Markdown paths per seed; this count is inferred from the generator and was not confirmed by running it. For a compact human-authored trial, prioritize the [Second Brain Template](https://github.com/fhjgch/logseq-second-brain-template), subject to the revision and rights checks below.

The [FashionOnt knowledge base](https://github.com/jjohare/fashionOnt) is an additional specialized option: its README claims 147 Logseq-format Markdown nodes and states that its own additions are CC BY 4.0 while upstream ontology sources retain their respective licenses. It may add dense property values and domain identifiers, but only an origin-by-file selection can make it a safe candidate. The workshop and demo graphs may provide useful teaching combinations, yet rights, version, and file inventory remain unresolved. Treat `mldoc` as a bounded syntax-parser reference and Logseq Handbooks as ordinary-Markdown smoke material, not whole-graph evidence.

This shortlist supports careful expansion, not a universal compatibility claim or approval to reuse any candidate.

## Candidate register

| Source and location | What is evidenced; what remains unknown | License and oracle assessment | Priority |
|---|---|---|---|
| **Official importer generator:** [`exporter_test.cljs`](https://github.com/logseq/logseq/blob/be800f171172c259d4dd942346e4d247a0783738/deps/graph-parser/test/logseq/graph_parser/exporter_test.cljs) and [`og_import_graph_cases.md`](https://github.com/logseq/logseq/blob/be800f171172c259d4dd942346e4d247a0783738/docs/og_import_graph_cases.md), pinned to `be800f171172c259d4dd942346e4d247a0783738` | Source-level generator describes 9 Markdown paths per seed (6 pages, 2 journals, `assets/generated.md`) and varies graph/block shape. **Not run:** 9 is an inferred template-path count, not a generated inventory; no byte count is claimed. | The `logseq/logseq` repository identifies AGPL-3.0. No separate fixture-data notice was established. Treat the license text and file scope as applying according to their terms; review notices and generated-string provenance before extracting output. Tests assert selected OG-to-DB importer effects, not a canonical standalone parser AST. | **1 — design fixtures from it.** Highest-value pinned official source, but not an admitted dataset or golden parser oracle. |
| **Community template:** [`fhjgch/logseq-second-brain-template`](https://github.com/fhjgch/logseq-second-brain-template), README and `pages/`, `journals/`, `logseq/` | README describes an OG-style file graph and names 3 dated journal plus 5 page Markdown paths (8 claimed paths, not independently counted); bytes, exact SHA, Logseq version, and actual syntax occurrences were not verified. | README says “MIT — use this however you like,” a direct reuse statement, not merely a repository badge. Preserve it and review any exceptions, third-party passages, or separately licensed assets at the exact revision. README examples offer human intent, not expected parse trees. | **2 — conditional compact graph.** Likely good coverage per file: task states/priorities, block-adjacent properties, namespace naming, and query/table examples. |
| **Specialized knowledge base:** [`jjohare/fashionOnt`](https://github.com/jjohare/fashionOnt), `markdown/` | README claims 147 Logseq-format node files, one per ontology term, in a flat directory. It documents typed property pairs and identifiers. Count and bytes are README claims only; no pinned SHA, file inspection, or line-ending inventory was completed. This is not a conventional `pages/` + `journals/` graph. | README says source ontologies retain original licenses and unified additions are CC BY 4.0 unless noted. Good provenance intent, but individual imported or adapted nodes must be mapped to their source and license before selection. Ontology meaning may support human semantic review, but there are no parser AST goldens. | **3 — selective, source-mapped sample.** Adds property-heavy, Unicode/domain-vocabulary variety unlike tutorial prose. Do not ingest the whole tree by default. |
| **Researcher workshop:** [`cecibaldoni/PKM-workshop`](https://github.com/cecibaldoni/PKM-workshop), `2024/Logseq.zip` as described in README | README identifies a preconfigured Logseq graph for a workshop. Archive internals, graph format/version, Markdown count, and bytes are unknown. | README says the repository is MIT and artwork is CC BY 4.0, while GitHub’s repository license panel identifies CC-BY-SA-4.0. The conflict is unresolved; the archive has no separately reviewed notice. No parser oracle. | **4 — rights clarification first.** Intentional teaching graph, but not usable until the applicable grant and exceptions are resolved. |
| **Tutorial demo:** [`candideu/Logseq-Demo-Graph`](https://github.com/candideu/Logseq-Demo-Graph), root, `pages/`, `journals/`, `logseq/`, `assets/`, `draws/`, `whiteboards/` | README advertises pages, references, tasks, queries/tables, media, drawings, and other tutorial features. Total files/bytes, exact commit, product version, and actual syntax mix are unknown. | No graph-content license surfaced in the reviewed root listing. README/site descriptions are not a semantic oracle. | **5 — rights blocked.** Potential breadth only; resolve graph terms before any acquisition. |
| **Parser reference:** [`logseq/mldoc`](https://github.com/logseq/mldoc), [`test/test_markdown.ml`](https://github.com/logseq/mldoc/blob/master/test/test_markdown.ml), [`examples/syntax.md`](https://github.com/logseq/mldoc/blob/master/examples/syntax.md) | Logseq describes `mldoc` as its Org/Markdown parser. GitHub’s mutable `master` file page reports 1,063 lines and 35.9 KB for `test_markdown.ml`; these are page metadata, not a graph count or pinned corpus size. Exact current SHA was not resolved. | Repository advertises AGPL-3.0. Selected tests contain bounded input/expected parser-result cases and can inform syntax comparisons after pinning. Their AST is a parser-level oracle, not page resolution, graph identity, or whole-vault behavior. | **Reference only.** Prefer independently specified local fixtures where copying test text is unnecessary. |
| **Official handbook:** [`logseq/handbooks`](https://github.com/logseq/handbooks), [`docs/`](https://github.com/logseq/handbooks/tree/master/docs) and [sample article](https://github.com/logseq/handbooks/blob/master/docs/1.Getting-Started/2.the-only-features-you-need-to-start.md) | Repository describes article Markdown organized with EDN topic/category metadata and build configuration. Exact SHA and Markdown count/bytes were not verified. This is a handbook site, not a confirmed OG graph. | Repository lists MIT; check the selected content and any exceptions at the pinned revision. Tutorial rendering and prose supply neither graph identity nor parser AST goldens. | **Smoke only.** Small ordinary-Markdown compatibility checks if useful and rights-cleared; do not count as Logseq graph coverage. |

“README claims” above means a repository description was visible but source blobs were not independently counted or examined. “Unknown” is deliberate: no estimate should be treated as a corpus measurement. The pinned official importer source is the only new candidate here with a full SHA; branch-based links are discovery references, not immutable source identities.

Two additional narrow leads remain deferred. The [`twaugh/logsqueak` sample graph](https://github.com/twaugh/logsqueak/tree/main/test-graph) is described as a realistic journal-oriented Logseq example, but its file count, revision, and content rights are unknown; the repository’s GPL-3.0 label does not settle graph-file scope, and personal/work content has not been ruled out. The [OG issue #4 attachment](https://github.com/logseq/og/issues/4) is a user-submitted `id::` / query-result reproducer for Logseq 0.11.0, but its archive was not inspected and its size, hash, and reuse terms are unknown. Both are leads for rights/privacy triage, not corpus entries; a small synthetic reproduction may be preferable.

## What these sources could add

The existing official-documentation campaign is a valuable real-document baseline, but the next tranche should target combinations rather than reproduce more documentation. The Second Brain README suggests tasks with block properties, namespaces, and query/table examples in journals. Its actual source bytes remain unexamined: this is a compact workflow lead, not verified feature coverage. The importer generator source is a more controlled route to combinations involving aliases/tags, page and block references, IDs and malformed/missing identity cases, scheduled/deadline values, nested blocks, tables, code fences, namespaces, and missing pages/assets. Its generated files would still represent importer inputs and outcomes, not a tested independent parser specification.

FashionOnt could provide property-dense pages with stable identifiers and domain vocabulary, but its flat layout and ontology-specific content make it a complementary stress sample rather than a general-user graph; actual non-ASCII variety is unknown. The Demo Graph and workshop descriptions suggest assets and tutorial-oriented examples, but syntax, app version, and counts need blob-level verification. No reviewed source establishes reliable coverage of every requested family—especially aliases in actual files, UUID/block-reference edge cases, query macros, math, fenced-code variants, Unicode normalization, and CRLF. Keep those gaps explicit and use small human-reviewed fixtures where an open, rights-cleared graph does not supply them.

Keep oracle classes separate:

1. **Syntax parser:** `mldoc` tests have expected low-level parse results for bounded inputs.
2. **Importer behavior:** the official generator/test cases assert selected downstream import results and graph validity.
3. **Human-authored graph:** a licensed template can show realistic feature co-occurrence but usually has no expected AST.
4. **Tutorial smoke:** handbook articles can exercise ordinary Markdown; the handbook’s generated pages are not a graph-parser oracle.

Passing one class does not imply passing another. A second parser or application renderer is useful comparative evidence only when its version and output projection are specified; it is not automatically ground truth.

## Rights, graph format, and privacy

Public visibility allows inspection but is not a blanket content-use grant. GitHub’s [licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains that absent a license, default copyright applies and that displayed repository-license metadata can be incomplete when a repository has multiple licenses or added complexity. Conversely, a repository-level license is not automatically irrelevant to Markdown: its actual text and scope may cover materials throughout the repository. For every selected graph, record the exact grant, its stated scope, and file-specific or third-party exceptions; do not infer coverage solely from a badge, and do not categorically exclude content merely because the grant is called a software license.

Before future intake, pin a complete commit and record the selected paths, per-file Git blob identity, byte length, and SHA-256. Confirm which inputs are OG file-graph Markdown, database-app importer fixtures, parser tests, or tutorial Markdown. Exclude Database EDN templates from this Markdown corpus: for example, [`C0ntr0lledCha0s/logseq-template-graph`](https://github.com/C0ntr0lledCha0s/logseq-template-graph) is described as an EDN-imported Database graph, so its schema counts are not Markdown page counts. Likewise, do not use public personal/work vaults as default test material; privacy, consent, and third-party content remain concerns even when files are visible. Do not inspect note bodies further unless a candidate has passed rights and scope triage.

No graph reviewed here provides a broad independent AST golden set. If a candidate is later cleared, retain its original bytes unchanged and document provenance and any review decisions. Build small, human-checked semantic projections—page metadata and order, root/block counts, parent/left pointers, source ranges, references, tasks/properties, identity, and round-trip behavior—rather than treating “loaded” or “rendered” as semantic equivalence.

## Deduplication and holdout design

Maintain two distinct forms of grouping:

- **Exact-byte identity:** hash raw files as received. If identical bytes occur at multiple paths or sources, execute one copy only when appropriate, but list every original source path, hash, and disposition. Never silently drop a duplicate origin.
- **Content-family identity:** separately group copied tutorial pages, shared templates, or near-identical snippets with a documented family key. This is for sampling and leakage control, not rewriting parser inputs. Preserve exact original bytes, including line endings, Unicode form, whitespace, indentation, filenames, and identifiers.

Account for every discovered Markdown file as selected, exact duplicate of a retained file, deferred for a named rights/version/privacy reason, or excluded with a reason. Publish totals for each disposition and reconcile them to the pinned file inventory. If a source is too large, record a deterministic selection rule, seed, strata, and omissions; stratify by graph, page/journal role, file-size band, and observed syntax families while retaining every safe rare-feature challenge file. Do not split related templates or sibling snippets across development and evaluation. Hold out whole repositories or whole content families, and report a small number of independent graphs as exploratory evidence rather than broad population coverage.

Any admitted tranche should state its frozen source revision, product generation, raw hashes, license evidence, privacy review, per-family counts, oracle type, exact exclusions, and parser-result coverage. The aim is a broad, meaningful compatibility sample—not a universal correctness claim.

## Research limits and source links

This review used public repository, README, file-listing, and documentation pages. It did not fetch graph archives, enumerate complete trees, inspect candidate note bodies, run generators, or test any parser against new inputs. Apart from the pinned Logseq importer source and the already-tested `logseq/docs` baseline, candidate branch heads and complete corpus quantities remain unresolved. Counts and byte sizes are included only when tied to the stated campaign or explicitly identified as README/GitHub-page claims.

Primary sources: [`logseq/docs` tested revision](https://github.com/logseq/docs/tree/08f855f24d66e4509b7ea808554c13b4649e6ee1); [`logseq/logseq` pinned importer test](https://github.com/logseq/logseq/blob/be800f171172c259d4dd942346e4d247a0783738/deps/graph-parser/test/logseq/graph_parser/exporter_test.cljs) and [import cases](https://github.com/logseq/logseq/blob/be800f171172c259d4dd942346e4d247a0783738/docs/og_import_graph_cases.md); [Second Brain Template](https://github.com/fhjgch/logseq-second-brain-template); [FashionOnt](https://github.com/jjohare/fashionOnt); [PKM workshop](https://github.com/cecibaldoni/PKM-workshop); [Demo Graph](https://github.com/candideu/Logseq-Demo-Graph); [`mldoc` tests](https://github.com/logseq/mldoc/blob/master/test/test_markdown.ml); [Logseq Handbooks](https://github.com/logseq/handbooks); and [Logseq’s DB-format guide](https://github.com/logseq/docs/blob/master/db-version.md).
