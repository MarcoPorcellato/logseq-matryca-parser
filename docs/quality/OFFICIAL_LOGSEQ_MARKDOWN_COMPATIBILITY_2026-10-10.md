---
type: ImplementationRecord
title: Official Logseq Markdown compatibility report
description: Bounded structural and semantic evidence from a pinned selection of official Logseq Markdown documentation.
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

# Official Logseq Markdown compatibility report

**Evidence date:** 2026-10-10

**State:** Local quality gate and independent review completed; prepared for publication. Hosted qualification and publication of this new diff remain separate.

**Scope:** A frozen selection from the official file-based Logseq documentation repository, plus separate existing synthetic tests.

## Executive outcome

The parser successfully processed **313 of 313 selected Markdown files** from one immutable official documentation snapshot in a completed local campaign. Every result row passed the campaign's raw-source-retention and node-tree invariant checks. The completed run recorded **5,424 nodes and 688 root nodes**, with no missing or duplicate inputs, parser exceptions, rejections, timeouts, or invariant failures. An independent file-only verifier reconciled the selected inputs, hashes, batches, result chunks, and terminal outcome. This is substantial, corpus-bounded compatibility evidence.

This is not evidence that every Logseq Markdown construct was semantically interpreted correctly. In particular, 60 non-empty inputs had zero returned nodes. A subsequent static inspection found that all 60 contain only leading page-property lines, so zero block roots are expected for their shape. The corpus campaign did not record or compare their parsed property maps, key order, or page references. Those details must not be inferred from the run's structural PASS.

The concise claim supported by the evidence is:

> In a hash-bound local campaign against 313 selected Markdown documents from an immutable official Logseq documentation snapshot, Logseq Matryca Parser processed every selected input without a reported execution or structural failure, preserved each exact source string, and satisfied the selected node identity and tree-linkage invariants, producing 5,424 nodes across 688 roots. This is corpus-bounded structural evidence, not complete Logseq semantic conformance.

For integrations and future Trama work, the result offers a reproducible real-document baseline for parser stability and a clear boundary around page metadata versus block trees. It can inform read-only ingestion and future differential testing; it does not qualify a Trama integration, Logseq database support, or a release.

## Corpus provenance, selection, and license

The source is [`logseq/docs`](https://github.com/logseq/docs), whose repository describes itself as Logseq's official reference documentation. The frozen source revision was commit [`08f855f24d66e4509b7ea808554c13b4649e6ee1`](https://github.com/logseq/docs/tree/08f855f24d66e4509b7ea808554c13b4649e6ee1), tree `3309b25a2a603036a1a56b51d6e38d206c8106a6`. The source repository identifies its license as MIT; see the [`LICENSE.md` at the pinned revision](https://github.com/logseq/docs/blob/08f855f24d66e4509b7ea808554c13b4649e6ee1/LICENSE.md). The corpus itself is not copied into this report. The accompanying inventory exposes selected source paths, sizes, and hashes rather than document bodies; anyone reusing upstream material should retain the upstream notice and check any file-specific terms.

The frozen selection contains **313 files totaling 542,495 bytes**. Its SHA-256 is `f7bd6a4dea937cee48d69670f11a1c7673feb54d333b67c95f51acf4033153ff`. The [machine-readable corpus ledger](official_logseq_corpus_2026-10-10.json) is the row-level index for source path, ordinal, byte size, and digest. These figures describe the named selection only. They do not mean that every Markdown file in the repository, every official Logseq sample, every user's graph, or every Logseq storage format was tested.

The ledger also makes the corpus composition visible:

| Source role | Documents | Input bytes | Parsed nodes | Root nodes | Zero-node documents |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pages | 238 | 540,030 | 5,347 | 611 | 60 |
| Journals | 75 | 2,465 | 77 | 77 | 0 |
| Total | 313 | 542,495 | 5,424 | 688 | 60 |

This distribution matters: most source bytes are in pages, while the journals are small. A future corpus should add substantial journal workflows and independent graph families rather than assuming that 313 files represent 313 equally complex examples.

The pinned official pages are useful scope references, not a semantic oracle: [Markdown](https://github.com/logseq/docs/blob/08f855f24d66e4509b7ea808554c13b4649e6ee1/pages/Markdown.md) and [Properties](https://github.com/logseq/docs/blob/08f855f24d66e4509b7ea808554c13b4649e6ee1/pages/Properties.md). They document a file-based Markdown surface at this historical revision. They do not make the selected documents a complete specification of Logseq behavior.

## Parser revision and campaign conditions

The campaign ran against Parser candidate commit `e5e9845fef510d0f5a2123beed8803f554757cb9`, tree `43f34bbf82d8108303caf960c5b88151cf5a3fbf`. Git comparison verified that the entire `src/` tree matched the primary repository commit [`bda44e60a36cfa73d086159fa7dabea8f29dd519`](https://github.com/MarcoPorcellato/logseq-matryca-parser/tree/bda44e60a36cfa73d086159fa7dabea8f29dd519). The recorded SHA-256 of the individual `logos_parser.py` file was `5f3c1cf7aa19d06c2928a5509019da0b2132791298ecdba64138979959352b31`; this is not a digest of the entire source tree. These are distinct revisions: the campaign result belongs to candidate `e5e9845…`; source-byte equality with `bda44e6…` is not a claim that the corpus campaign ran on the primary commit or on any later local bytes.

The worker used `StackMachineParser(tab_size=2, strict_refs=False)`. Parsing ran in an OrbStack/Docker Linux ARM64 environment with portable CPython 3.12.13, four CPUs, 4 GiB memory, a 512-process limit, and a three-second per-document worker limit. Network access was disconnected for the parsing phase. Seven batches completed in the sequence 50, 50, 50, 50, 50, 50, and 13 files; 25 durable result chunks were reconciled. There was no retry, resume, or fallback.

The terminal result was `COMPLETE_NO_FINDINGS` with exit code 0. The first 50 files also appeared in a separately preserved earlier partial campaign, but this completed campaign parsed them again; no result from the partial attempt was imported or used to fill a gap. This matters because the 313/313 count belongs to one internally reconciled run, rather than a stitched total whose rows might have different runtime or parser provenance.

The **142.223758-second** elapsed time is the whole campaign duration, including preparation, infrastructure, and evidence handling. It is not a parser-only benchmark, a latency guarantee, or a comparison with another implementation.

For each input, the executed assertions retained the exact input in `page.raw_content` and checked structural invariants over returned nodes: unique node UUIDs; correct parent and previous-sibling (`left`) pointers; and consistent node and outline paths. Counts of parsed nodes and roots were recorded. These assertions did not compare every page's properties, ordered property keys, references, tasks, dates, assets, macro expansion, or serializer output to an independent expected result.

## Interpreting the 60 zero-node inputs

The run's 60 non-empty files with zero returned nodes total **7,033 bytes and 196 property lines**. Static inspection of all 60 inputs found only leading `key:: value` page properties: no bullets, Markdown headings, blank preambles, fenced blocks, or non-property continuation lines. Their zero block roots are consistent with the parser's page model: leading page properties are stored on the page and do not synthesize a block node. This is an explanation from source shape and code inspection, not a corpus-wide executed property oracle.

The static audit counted 14 source key spellings representing 12 lowercase-normalized names, with no duplicate normalized key within a file. The most frequent names were `type` (53 lines), `description` (37), `url` (27), and `alias` (24). The remaining names were `domainincludes`, `meta`, `parent`, `platforms`, `rangeincludes`, `sameas`, `supports`, and `unique`. These are source-occurrence counts, not assertions about the returned runtime values. Mixed-case spellings such as `Alias` and `domainIncludes` explain why normalization and first-seen order are useful explicit regression targets.

The parser's two file-reading methods serve different consumers. A consumer that needs page metadata should use the page-returning form:

```python
parser = StackMachineParser(tab_size=2)
page = parser.parse_page_file(source_path)
page.properties        # page metadata
page.properties_order  # first-seen property-key order
page.refs              # page-level references
page.root_nodes        # [] for a property-only page
```

`parse_file()` is a compatibility reader that returns only the root-node list:

```python
block_roots = parser.parse_file(source_path)  # [] for the same property-only page
```

An empty `parse_file()` result therefore does not establish that the source page is empty. Prefer `parse_page_file()` when page title, properties, references, or raw source are part of the integration contract. The implementation and return shapes are visible in the pinned [`logos_parser.py`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/src/logseq_matryca_parser/logos_parser.py#L1092-L1097) and [`LogseqPage` model](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/src/logseq_matryca_parser/logos_core.py).

Three focused synthetic metadata-only cases have since passed locally: LF input, CRLF input, and a real temporary-file check of both page-returning and root-list readers. Their assertions cover normalized page-property keys, exact values and order, unchanged raw text, property-derived references, and zero roots. See the [focused metadata-only regression tests](../../tests/test_parser_metadata_only.py). This is a separate small test result; it was not part of the 313-file campaign. They also passed in the complete native test suite described below. A hosted result for these new bytes remains pending; local qualification is not publicly immutable exact-commit evidence.

## Capability and evidence matrix

The following tests are concrete, checked-in examples of bounded behavior. Except for the metadata-only cases explicitly labeled above, they are **coverage references**, not a statement that each test was re-executed as part of the official corpus campaign.

| Capability | Representative evidence | Boundary of the evidence |
| --- | --- | --- |
| Ordered outline structure and independent tree expectations | [`test_valid_generated_outlines_match_independent_recursive_model`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_parser_properties.py); deep-chain and sibling/left-pointer checks in [`test_parser_deep_refresh.py`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_parser_deep_refresh.py) | The generated recursive model is bounded (maximum depth 5 with root depth 0, up to six node levels, and at most 16 nodes); the deep-chain tests are focused structural stress cases, not a complete grammar oracle. |
| Page and block properties, source order, and references | [`test_frontmatter_properties_are_stored_at_page_level`, `test_page_properties_order_preserves_source_sequence`, and `test_page_properties_yield_page_refs`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_logos_parser.py); generated block-property/link round trips in [`test_parser_properties.py`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_parser_properties.py) | These fixtures establish selected cases. Before the new metadata-only tests, the cited page-property cases included a root block or used YAML frontmatter; they did not by themselves establish the zero-root boundary. The 313-file campaign did not capture parsed property maps. |
| Repeated parse determinism, exact fixture projection, and selected serialization round trips | [`test_exact_parse_snapshot_and_same_input_determinism` and `test_semantic_roundtrip_profile`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_compat_corpus.py) plus the versioned [compatibility fixture manifest](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/fixtures/compat/v1/manifest.json) | A curated, project-authored fixture set is not the same source as the official 313-file corpus, and round-trip equivalence is defined by explicit semantic projections and identity policies. |
| Tasks, priorities, and selected scheduled/deadline/repeater fields | The `m1a-task-timing` fixture and exact snapshot listed in the [compatibility manifest](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/fixtures/compat/v1/manifest.json) | Covers the fields encoded in that fixture; does not prove every date form, task transition, or upstream application behavior. |
| Graph loading, aliases, backlinks, and page identity | [`test_load_directory_bulk_parse_and_uuid_lookup`, `test_page_aliases_and_backlink_resolution`, and `test_graph_backlink_resolution_cross_page`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_graph.py) | These exercise bounded synthetic graphs and graph APIs, not all 313 selected documents as one loaded vault or every graph feature in the official application. |
| Seeded adversarial generation and bounded malformed-input handling | [`test_generated_cases_are_bounded_and_order_independent`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_parser_adversarial.py) and [`test_parser_malformed_properties.py`](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/tests/test_parser_malformed_properties.py) | Fixed seeds, bounded recipes, and explicit replay improve repeatability; generated cases are not a sample of every valid Logseq syntax or user graph. |
| Metadata-only file semantics | Three focused local cases in the [new test file](../../tests/test_parser_metadata_only.py) | Focused result: 3 passed, also included in the passing full native suite. Hosted qualification of the new bytes remains pending; these tests do not retroactively alter what the corpus campaign asserted. |

## Local qualification of the report and regressions

The following checks completed on 2026-10-10 in the existing macOS ARM64 working snapshot with CPython 3.12.13. The snapshot includes pre-existing, uncommitted assurance tests that were preserved unchanged. These results therefore describe the complete local working snapshot, not just the new test file or an immutable published commit.

| Check | Observed result |
| --- | --- |
| Focused metadata-only regressions | 3 passed |
| Complete native test suite | 1,273 passed; 5 skipped; no failures |
| Total statement coverage | 89.83%, above the unchanged 80% minimum |
| Ruff lint | PASS |
| Mypy type checks | PASS across 106 source files |
| Maintained-document metadata and links | PASS |
| Public-document vendor-name policy | PASS |
| Independent data-only ledger reconciliation | All 313 rows, 25 result chunks and seven batch summaries matched the frozen evidence |
| Production source and historical evidence preservation | Unchanged |
| Independent review of this combined local phase | PASS_WITH_NOTES; no outstanding blocking findings |

The native suite duration was 227.31 seconds, which is a test-suite duration, not a parser benchmark. The five skips are not counted as passing tests. No dependencies were installed or changed, and no production parser code was modified for these regressions. The local quality gate does not execute the official corpus again or qualify additional researched datasets.

The independent read-only review reconciled the complete ledger and checked the test expectations, source bindings, documentation claims, and scoped privacy boundaries. Its notes preserve the evidence limits: the retained native-suite capture contains initial and terminal segments rather than a complete raw log, and some pinned upstream source bodies were unavailable through the reviewer's web reader. A separate fresh metadata lookup confirmed the pinned importer files exist; this does not establish generated-output quantities or generator execution. These notes do not change the recorded 313-document result.

## Keep the assurance lanes distinct

This report combines context from three different evidence lanes, which answer different questions:

1. **Frozen real-document campaign.** The 313-file selection was fixed and hash-bound; it was not randomly sampled. It exercises complete inputs from one official documentation revision, but the campaign's runtime oracle was structural and raw-content based.
2. **Deterministic fixtures and generated tests.** The checked-in compatibility corpus has literal source/snapshot hashes, exact parse snapshots, repeated-parse comparisons, and selected semantic round-trip projections. Property-based tests generate bounded models; for example, outline/property tests use derandomized generation with a ceiling of 40 examples per profile. Other adversarial test recipes use explicit seeds and bounded families. “Generated” or “seeded” describes how test inputs are constructed; it does not make the 313-source selection a statistical sample.
3. **Hosted CI.** The primary repository commit `bda44e60a36cfa73d086159fa7dabea8f29dd519` has a separate [post-merge hosted CI result](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/37202912593), after [PR #238](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/238). That receipt concerns its exact merged snapshot and named jobs. The corpus campaign was a local run against distinct candidate `e5e9845…`; the hosted receipt is not the campaign result and does not qualify later local report, ledger, or metadata-test bytes. No hosted result for those later bytes is claimed here.

The project [CI assurance map](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/docs/CI_ASSURANCE.md) describes the repository's separate exact-revision CI and release boundaries. Local corpus observations, source-level equivalence, fixture tests, and hosted jobs should remain separately labeled in downstream reports.

## Limits on the compatibility claim

The corpus consists of official documentation files at one source revision. That is valuable because the source is attributable and immutable, but it is not a representative random sample of personal knowledge graphs. Documentation pages can over- or under-represent syntax compared with working journals, exported vaults, custom templates, and hand-authored notes. The selection also covers the file-based Markdown surface only; it does not load these files as one Logseq graph and does not exercise UI behavior, application migrations, synchronization, or database-mode storage.

The runtime result is Linux ARM64 only. The separate hosted CI receipt listed above contains a native platform matrix for its own exact merged snapshot, but it is not a cross-platform execution of this 313-file corpus campaign. Similarly, this campaign used non-strict reference mode and did not establish behavior for every unresolved or ambiguous link. It did not reserialize every official source and compare the result to an independent canonical representation. These omissions do not contradict the bounded structural result; they define what that result means.

The project's maintained [support matrix](https://github.com/MarcoPorcellato/logseq-matryca-parser/blob/bda44e60a36cfa73d086159fa7dabea8f29dd519/docs/reference/CONFORMANCE_SUPPORT_MATRIX.md) describes Markdown parsing as a deterministic AST surface with hierarchy, UUID handling, properties, references, tasks, timestamps, assets, and documented round trips, while explicitly disclaiming complete upstream conformance. This report narrows observed evidence further: some of those areas have separate focused tests, but the official corpus run asserted only raw-source equality, tree structure, and counts. A feature mentioned in project documentation should not be read as an assertion that every instance of that feature occurred in the 313 selected files or passed an independent per-file semantic oracle.

Nor does the successful run provide a performance ranking. Its wall time includes setup and evidence collection, and there is no controlled comparison implementation, repeated timing distribution, or parser-only measurement here. It also does not demonstrate behavior at a later parser commit, on another CPU architecture or operating system, under different parser options, or on future contents of the official repository. Each of those would need evidence bound to the exact new inputs and runtime.

## Reproducibility and future expansion

The minimum reproduction record is the immutable official source commit/tree, the frozen selection digest and per-file inventory, the exact Parser candidate/tree and recorded parser-file digest, parser settings, runtime envelope, batch boundaries, per-file result rows, result-chunk digests, and the independent reconciliation result. The [public corpus ledger](official_logseq_corpus_2026-10-10.json) preserves the row-level source identity; the repository's documented quality gates are linked from [CI assurance](../CI_ASSURANCE.md). Repeating the campaign would be a new execution and is not implied by this report.

A reviewer should be able to confirm that the 313 ledger entries are unique, retain the original order, and bind to the frozen selection digest; that every row points to the pinned official tree and expected byte length; that batch boundaries total exactly 313; and that all emitted result chunks match their recorded byte lengths and SHA-256 digests and account for those same inputs. The campaign's independent verifier performed those file-only consistency checks after execution. Such reconciliation makes the result auditable, but it cannot strengthen the runtime oracle: verifying hashes proves which files and result records were considered, not that an unasserted page property was semantically correct.

The next useful corpus step is evidence-led expansion, not a larger unreviewed download. Candidate sources should be classified by provenance, license, Logseq edition/storage model, Markdown feature coverage, deduplication, file count/size, and whether independently reviewable semantic expectations can be made. Do not mix official docs, community vaults, generated fixtures, and database exports without retaining those distinctions. The separate [dataset candidate assessment](LOGSEQ_MARKDOWN_DATASET_CANDIDATES_2026-10-10.md) records research into official generators, demo graphs, community templates, and workshop material. No additional candidate source has been downloaded or tested for this report.

For a future broader semantic corpus tranche, the recommended additions are:

- define the exact compatibility target (for example, a named file-based Logseq parser/version) and explicitly exclude DB and Org modes unless assessed independently;
- retain a complete, licensed, hash-pinned inventory and publish a selection rule that can be independently recomputed;
- add per-file semantic projections or adjudicated expectations for page metadata, property order/value types, page/block references, aliases, tasks, timestamps, source spans, assets, and relevant macro/embed behavior;
- compare against a pinned upstream implementation where feasible, preserving both sides' versions and classifying intentional divergences rather than treating one parser as an unquestioned oracle;
- include parse/serialize/parse checks only for constructs with a defined supported round-trip contract, plus explicit negative controls showing that the oracle detects representative wrong values and relationships;
- report unsupported or unknown syntax, missing expected values, and execution failures separately; never let a raw-content match or empty tree stand in for semantic correctness;
- qualify new test and corpus bytes on the exact source revision through the repository's local gate and, when required, an exact-commit hosted CI receipt.

Until that work exists, use phrases such as **“bounded compatibility evidence on a pinned official Markdown selection”** or **“all selected corpus files passed the recorded structural checks.”** Avoid “fully Logseq-compatible,” “complete Markdown support,” “certified by Logseq,” or implications of Logseq DB / Org equivalence.

## Contributor guidance

When adding a report or regression from a corpus finding, preserve the historical run as-is; do not retrofit semantic claims into its result rows. Add small synthetic tests with literal expected values when they isolate a behavior, and keep any newly executed regression, full local gate, hosted CI, and publication as separate evidence states. If a zero-node or metadata-only page is involved, check the page-returning API before interpreting an empty root list. Keep official source paths and hashes in the ledger, but avoid copying upstream prose or exposing private runtime receipts.

The repository's normal review workflow remains applicable: update only evidence actually checked and link the immutable source and test references. This record completed its local gate and independent review; any later publication or changed source snapshot needs its own qualification. This report is a compatibility evidence record, not an upstream certification or an expansion of the Parser's supported contract.
