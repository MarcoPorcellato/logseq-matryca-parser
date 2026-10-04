---
type: ImplementationRecord
title: Composite valid Markdown property assurance
description: Approved scope, execution limits, independent expectations, and qualification evidence for mixed Markdown generation.
status: draft
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-04
verified: 2026-10-04
stale_after: 2026-11-03
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Composite valid Markdown property assurance

## Composite checkpoint and current follow-up status

The approved finite broad campaign passed 119 recipes representing 117 distinct
Markdown source digests. Independent validation returned VALIDATED; independent
phase review returned PASS_WITH_NOTES. The earlier composite quality aggregate
passed 1,202 tests with five native-platform skips and 89.83% coverage, plus Ruff,
mypy, documentation and vendor-name checks. Source and test bytes were preserved.

The earlier pre-publication offline local package cycle passed wheel/sdist construction,
wheel contract, Twine 6.2.0, isolated wheel-installed strict typing with Mypy
1.20.2, and bounded archive inspection. Independent Sol High review returned
PASS_WITH_NOTES without blocking findings. At that checkpoint, the inspected
runtime source matched the candidate, but the later documentary completion
update changed the sdist snapshot. Exact submitted-commit hosted package
qualification was still required; its subsequent result is recorded below.
Earlier failed and incomplete attempts remain historical, not retroactively
successful. The ledger below preserves their chronological states.

The subsequent [PR #234](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/234)
passed its hosted checks and was squash-merged as
`a26370a73d0c1ec99eb186e0131044a23e4acb00` on 2026-10-04.
Its [post-merge CI](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/37185041499)
passed quality, package and dependency checks and all six native combinations:
Ubuntu 24.04, macOS 15 and Windows 2025 with Python 3.12 and 3.13.
Separate security checks also passed. [PR #237](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/237)
then aligned the README and release documentation; it was merged as
`f7b720ba7427da8a042e41bdc9c8f5d6fd3ee8eb` with successful
[post-merge CI](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/37191353787).
These are exact-commit hosted results, not a release or universal correctness
claim. The composite change remains unreleased; #104 remains open. Historical
entries below retain the gates that were pending at their respective checkpoints.

The next approved local-only slice checks closed inline code, HTML comments,
single-dollar math and double-dollar math against repeated visible references.
It is separate from composite schema 3 and does not change the parser, serializer,
dependencies or execution protocol. Qualification of that new test file is
recorded separately below; the preceding CI results do not qualify new bytes.

## Follow-up: closed inline shielding and occurrence order

The maintainer approved a separate, local-only test slice on 2026-10-04 against
`bf9bb1dcfa137b7837ec6826e238c23ee4b2f34f`. It adds one pytest file,
`tests/test_parser_shielding_properties.py`, without changing production code,
dependencies, existing composite schema 3 or its runner.

Four fully rendered, hand-checked anchors cover matched inline backticks,
closed HTML comments, `$…$` and `$$…$$`. Each contains hidden-only tokens and
tokens repeated both inside and outside its literal region. The visible
skeleton places a tag before its links and repeats both links and tags. This
distinguishes ordered occurrence lists from stable reference deduplication,
which visits all wikilinks before tags.

Finite generated variations use one single-line root block, delimiter-free
synthetic target/tag values, simple space-separated tags and LF/CRLF endings.
The source limit is 2 KiB of UTF-8. Collection retains all four anchors first,
deduplicates candidates and caps the selected list at twenty before parsing.
Hypothesis runs only generation, without a database or parser calls. The
ordinary parser loop checks independent facts on the first result before a
second parse, then compares `exact_parse_v1` projections for determinism.
At most forty parses occur in that loop; the cap is not a wall-clock guarantee
or a limit on the complete repository suite.

Independent expectations cover visible link/tag multiplicity and order,
node/page reference order, exact page input and node content, one root without
children, and the source interval `(1, 1)`. Existing tree invariants remain in
use. Parser-free controls check collector saturation and corrupt copied
observations while leaving expectations unchanged. An unexpected parser
failure must stop the selected loop without retry or oracle weakening.

Escaping, nested or malformed regions, delimiter adjacency, multiline/fenced
states, query blocks, bracketed tags, metadata, graph/filesystem behavior and
serializer round trips are excluded. Finite synthetic recipe context may
appear in pytest failures; this is not a source-free logging guarantee.
Local implementation now passes fifteen focused tests. The observed focused
selection contained the four anchors and sixteen distinct generated recipes,
with forty parser calls across all four families and no parser failure.
Generation is explicitly limited to `Phase.generate`. A hand-written
observation baseline and copied corruption controls include both hidden-link
and hidden-tag leakage, root-count and nonempty-child errors. The initial
collector and baseline controls have RED/GREEN evidence.

The first full gate stopped before pytest on a type-inference error in the new
test's heterogeneous mutation map. A bounded test-only repair replaced it with
typed copied observations; no type suppression or production change was used.
The failed outcome remains preserved. The fresh complete local gate then
passed 1,217 tests with five native-platform skips and 89.83% coverage, plus
Ruff, full Mypy, documentation and vendor-name checks. Source/test bytes were
unchanged during that successful run. Final documentary reconciliation is
checked separately after recording these results. Independent GPT-6.1 Sol
Medium implementation review returned PASS_WITH_NOTES, with no test or oracle
blockers. Its documentary note was addressed by explicitly labeling the older
composite/pre-publication checkpoint as historical without changing its numbers.
This is local evidence, not new hosted qualification.
This tranche does not authorize commit, push, PR, merge,
release or tracker mutation, and does not close #104.

## Scope, baseline, and authority

The maintainer approved this bounded, test-only implementation on 2026-10-03.
It contributes to [#104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104),
which remains open. The approved baseline is
`0e2b0187ddc54abd92f6a50e7dbde5166e474ffd`, the controlled squash merge of
[PR #233](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/233).
Its [post-merge CI](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/37112297184)
passed all nine jobs, including Ubuntu 24.04, macOS 15, and Windows 2025 with
Python 3.12 and 3.13. That baseline result does not qualify this new increment.

The initial authorization covered local tests, documentation, independent review,
and quality gates in the existing checkout. It did not cover commit, push,
pull-request creation, merge, tag, release, package publication, or tracker
changes. Production code was unchanged during that initial test-only phase.
The later bounded serializer authorization and its evidence are recorded below;
dependencies, workflows, public APIs, the Org reader, and consumer integrations
remain unchanged. GitHub is the canonical backlog;
no Beads import, synchronization, or task mutation belongs to this increment.

## Why this increment

The existing generated valid-outline suite uses simple alphanumeric text and
a small property/link extension. Fixed compatibility tests cover many richer
features individually. This increment targets interactions between those
existing contracts rather than treating a larger random string count as a
correctness argument.

One valid-only recipe family combines nested and sibling blocks, task status
and priority, supported schedule/deadline dates, a nonempty literal block
property, continuation lines, visible wikilinks/tags, finite Unicode tokens,
and LF/CRLF. The source is entirely synthetic. Input bounds are at most
32 blocks, maximum depth eight with root depth zero, and 16 KiB of UTF-8.

Metadata follows its block opener before prose continuations. Finite supported
task and priority tokens and fixed valid dates have independent expectations.
References appear in ordinary block text, not special reference properties.
Empty or list-valued properties, reserved property keys, blank lines, drawers,
repeaters, date ranges, explicit UUIDs, lexical shielding, arbitrary text or
paths, graph mutation, filesystem attacks, and concurrency are excluded.
Larger depth/width/line stress and malformed/shielding interactions remain
separate future slices, not coverage claimed by this work.

## Independent correctness oracle

The synthetic recipe and logical-line ledger define expected tree shape,
block count and order, owned source intervals, task/priority fields, literal
and timing properties, UTC timestamps, and reference order/deduplication before
the parser runs. Expectations must not reuse production extractors or derive
expected values from parsed output. A small hand-checked literal case qualifies
the renderer and model, not merely a comparison between their own outputs.

Each node's original source span covers its own opener, property, and
continuation lines, not its entire subtree. LF and CRLF use one-based logical
lines. The original AST must satisfy these independent expectations and the
existing parent/left/path/outline and UUID-uniqueness invariants.

Only afterward does serialization/reparsing compare the existing
`semantic_roundtrip_v1` projection with recomputed synthetic UUIDs, absent
source UUIDs, and outline-path relations. This projection does not preserve
source line spans, so serialized line locations are not compared with the
original-source ledger. Round-trip equality alone is not the correctness
oracle. A typed parser error is a failure for this valid-input family.

The existing adversarial worker checks structural invariants and round-trip
parity, but not this independent model. Minimal new test-only worker/envelope
plumbing must therefore reconstruct validated finite recipe expectations in
the child. Existing runner defaults and behavior remain unchanged.

## Execution, diversity, and replay

Recipes are collected before parser subprocesses are launched. Smoke execution
is capped independently at four children total, including explicit edge
recipes. The opt-in broad campaign is capped at 120 children total across
fixed seeds 104, 417, and 911, or one explicitly recorded exploratory seed.
Duplicates are removed before execution; actual selected and executed counts
must be recorded rather than inferred from generation settings.

Each selected recipe receives one fresh child and the existing three-second
timeout, including startup, oracle checks, and serialization. The campaign
stops at the first unexpected result, without parser retries, shrinking, or
automatic minimization. Exact recipe replay executes only that recipe.
Generation limits and per-child timeouts do not establish a hard timeout for
the entire parent command. No new scheduled workflow is introduced.

Selected receipts contain finite recipe/schema information, original-source
digest and byte count, campaign seed, implementation and revision evidence,
runtime versions, classification, and explicit oracle/round-trip check flags.
Acceptance must validate receipt identity, types, digest, and required flags.
Receipts exclude rendered source, raw child output, exception messages, local
paths, environment values, and user data. This is not a privacy guarantee for
all pytest tracebacks.

Seeded generation supports repeatable exploration, but exact finite recipe
replay is the durable failure evidence. Hypothesis replay blobs are version
bound, and generation settings are not an independent execution-count cap;
see the official [API reference](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.seed)
and [execution-count explanation](https://hypothesis.readthedocs.io/en/latest/explanation/test-case-count.html).
Implementation qualification must distinguish the baseline revision from
uncommitted test bytes and describe any replay-validation limits explicitly.

## Review and qualification ledger

- Read-only Luna discovery identified mixed task/property/reference behavior,
  lexical boundaries, and Unicode source spans as useful coverage gaps.
- Read-only GPT-6.1 Sol design review returned `PASS_WITH_NOTES`. The property
  placement, date expectations, original-source span rules, identity policy,
  worker limitation, and total campaign budgets above incorporate its notes.
- The initial test-only draft has reached a blocking finding. The worker
  reported nineteen focused harness tests passing after an initial missing-
  module RED. This is reported focused evidence, not full qualification;
  assertion-mutation sensitivity and the full suite have not been completed.
  Controller static checks subsequently found six Ruff findings and twenty-
  three mypy errors in the two draft test files. The documentation gate and
  whitespace check passed; the source/test gates did not. No full quality,
  package, or hosted qualification is claimed.

### First smoke finding and stop boundary

Smoke selected four recipes but executed only the first child before stopping.
The parent classified its result as `runner_failure` / `InvalidWorkerEnvelope`.
The parent validator rejects a failed round-trip result whose original model
check has succeeded, so it cannot preserve that legitimate partial-stage
failure. The CLI then raises `KeyError` by reading the classification at the
wrapper level rather than inside the nested result. These are draft harness
defects, not evidence that the production parser raised a raw exception.

While investigating that reporting failure, the worker performed one additional
in-process diagnostic case attempt despite the no-rerun instruction. This is
a procedural deviation, not an authorized retry or qualification. Its observed
envelope reported `model_checked=true`, `roundtrip_checked=false`, and
`semantic_roundtrip_failure` / `SemanticRoundtripMismatch`. The exact first
child envelope was not retained separately; it must not be represented as an
independently preserved copy of the diagnostic envelope. Each round-trip case
attempt may include more than one parser call, and the earlier focused tests
also invoked the parser; the two campaign/diagnostic attempts are not a count
of all parser calls.

No broad campaign, automatic minimization, further parser execution, or
production repair followed the stop. The exact synthetic recipe is:

```json
{
  "seed": 104,
  "shape": "root-child-sibling",
  "task": "TODO",
  "priority": "A",
  "scheduled": "2026-04-30 Thu",
  "deadline": "2026-05-01 Fri",
  "literal": "kept",
  "reference": "Target",
  "tag": "topic",
  "unicode": "caffè",
  "newline": "lf"
}
```

Recipe schema: 1. Source size: 329 UTF-8 bytes. Source SHA-256:
`5ce0ba81caa920ed9ea1d1e245d078d942d91d3a1b18b3cea86a35a97c1597c3`.
Draft module SHA-256:
`66863d4482e0414b5297104dde0e85e839d6c8d85853905164590c5b15e96ac1`.
Draft harness-test SHA-256:
`e7d048731c61a52d6339731c8af6cb3ded8a1a0b9b7f46c7f59995505af87e64`.
Runtime: macOS ARM64, Python 3.12.13, Hypothesis 6.168.1. Both baseline and
current revision were `0e2b0187ddc54abd92f6a50e7dbde5166e474ffd`; the draft
test bytes were uncommitted and are identified separately by their hashes.

The diagnostic did not preserve a field-level projection difference. A source
inspection suggests that emitting block properties after continuation text
conflicts with the parser's existing rule that post-continuation property-like
lines are literal. That is a hypothesis until reviewed and bound to the exact
runtime difference. Read-only GPT-6.1 Sol diagnosis returned `BLOCKED`: the
corruption controls remove an unmodified second root before checking the
corrupted field, so root-count failure can falsely satisfy every control.
They do not establish sensitivity to the intended task/property/reference/
span/parent assertions. The review also identified an existing serializer test
that explicitly expects continuation lines before an `id::` property line;
changing that layout is a production correction decision, not a test-only
assumption repair. Neither this hypothesis
nor the observed mismatch authorizes a production serializer change or another
campaign. This increment remains unqualified and unpublished.

### Final implementation review

The completed read-only GPT-6.1 Sol High review returned `BLOCKED`. No parser
execution or tests were performed by the reviewer. It confirmed the following
draft defects and assurance gaps:

- Legitimate partial-stage failures are rejected by the envelope validator.
  Success must still require both checks; failed results must preserve which
  stages completed without being accepted as success.
- The CLI reads result fields from the wrong nesting level. Parser-free CLI
  tests must cover successful, failed, and malformed campaign results.
- All five corruption controls drop the second root, so an unrelated root-
  count assertion satisfies them. Controls must preserve the complete tree,
  establish a passing baseline, and identify the intended rejecting assertion.
- The literal fixture checks rendered source but does not independently freeze
  the expected model. Its expected fields need hand-checked literal evidence.
- The family does not repeat visible references within a block. Ordered fields
  are modeled, but actual per-block deduplication coverage is not established.
- The advertised single-seed broad mode requests a collection limit that the
  collector rejects. Every advertised mode needs parser-free budget checks.
- Replay binds only the two draft files, not the relevant production and shared
  test implementation or revision. Exact replay and authorized cross-revision
  comparison must be distinguished; nested receipt identity also needs checking.
- Static checks, assertion-sensitivity restoration, regressions, campaign
  execution, and complete quality gates remain incomplete or failing.

The reviewer considered the finite input and independent model approach valid
for this limited family. Source inspection strongly supports the property-
ordering explanation, but does not recover the missing runtime field delta.
The existing serializer layout test and the parser's misplaced-property test
must be reconciled explicitly before any production correction.

### Diagnostic authorization and execution boundary

After the blocking review, the maintainer approved test-only harness repairs
followed by one bounded diagnostic on 2026-10-03. Production code remains
unchanged. The controller owns the sole diagnostic invocation; the repair
worker may run only parser-free validation and static checks. Independent
review and fresh source/hash checks precede that invocation. All direct parser
calls and real child launches are denied during the harness test session.

The authorization stops after the diagnostic result and evidence preservation.
It does not authorize a smoke or broad campaign, full parser suite, retry,
serializer correction, commit, push, or external publication. Per-block visible
reference deduplication expansion remains deferred rather than silently added
to this repair. The single authorized diagnostic has now completed with a
semantic round-trip failure; no retry followed.

Controller verification of the repaired checkpoint passed 35 guarded harness
tests, Ruff, and mypy for the two new test files. The guards denied parsing and
real process launches throughout the test session; no diagnostic attempt was
consumed. A hand-checked literal expected model replaces the former self-derived
fixture. Corruption controls retain all roots and identify the intended failed
assertion. An in-memory task-assertion mutation demonstrated sensitivity, then
restoration returned the same corruption to rejection without changing source
bytes. The worker's earlier RED included two teardown errors from a blocked
platform-metadata process attempt; that fixture now supplies metadata without
launching a process. Sol High repair review returned `PASS_WITH_NOTES` for the
one exact diagnostic only, not for overall harness or campaign qualification.

### Exact diagnostic result and preserved evidence

Fresh preflight verified the same source revision, the reviewed repaired-file
hashes, the recorded 329-byte source digest, Python 3.12.13, Hypothesis 6.168.1,
macOS 15.7.3 ARM64, disabled interpreter optimization, and unused output targets.
The complete tracked production/import source, dependency, and workflow diff
against HEAD was empty. Selected dirty state remained exactly two test and
three documentation files; no concurrent edits occurred during the diagnostic.

One fresh worker was launched with a three-second timeout covering startup,
original parse, model assertions, serialization, and reparse. The parent exited
1 with a valid receipt, not a runner or CLI reporting error. Its independently
preserved sanitized worker envelope records:

- Schema 2 and case ID
  `composite-v2-c9c61bd11731b60d8c76e7c8805ad34eced2dbdbe0c67657f7efec8b27e91a26`.
- `classification=semantic_roundtrip_failure` and
  `exception_type=SemanticRoundtripMismatch`.
- `model_checked=true` and `roundtrip_checked=false`.
- Twelve field differences: `clean_text`, `content`, `properties`, and
  `properties_order` at each outline coordinate `[1]`, `[1, 1]`, and `[2]`.
  No field values or Markdown source were emitted.

The runtime comparison now confirms a round-trip defect for this exact finite
case and identifies the affected fields. The source-supported explanation is
that serialization moves genuine metadata behind prose continuation, where
the unchanged parser treats it as literal text. This evidence is not a
production-fix verification, a claim about every metadata shape, or proof of
drawer/list-property behavior. The schema-1 historical finding remains separate;
the recipe and source digest are unchanged, but the schema-2 case ID is new.

Repaired module SHA-256:
`34a032cdf9a6e550b9345e8bf13c7709587f00b3e73f50c0bf9ddeb98822a8ac`.
Repaired harness-test SHA-256:
`8c8cc40c4d27c5e54a8fae91e41ab2c82f943d9608f83a22f5898f66504457ac`.
Preserved diagnostic receipt SHA-256:
`e1bb066e8a5d0de34696db7e79b09b0797d0eb6d1d557bd6d180f6d25d63ef35`.
Separate sanitized worker-envelope SHA-256:
`5a2309b61582c6e907a2d09fa97c5c084a3f9927e75a05c28ee2b2bbbf0afcd4`.
Separate evidence-context SHA-256:
`88c5e99653793bce25341e2a6b15e155a96fc7c0e87c163a441e8fd1b416abbe`.
The separate envelope was verified JSON-equal to the envelope in the receipt.
Post-checks verified unchanged HEAD, repaired hashes, dirty-state ownership,
and empty production/dependency/workflow diff. One worker evaluation includes
original parse and reparse; this is not a claim of only one parser call.

The receipt manifest is selected-file evidence, not a complete import/runtime
attestation. It omits the path helper and package initialization/eager-import
closure, and does not bind installed dependency or interpreter bytes. Exact
runtime replay is therefore not qualified. The controller's fresh complete
tracked-source checks provide the additional binding for this particular local
diagnostic; they do not repair generic replay. Revision sentinel handling,
nested replay validation, and process-exit exception-name consistency also
remain review notes for a later repair before generic replay qualification.

The authorization is consumed. No additional parser execution, campaign,
minimization, production edit, commit, push, or tracker mutation occurred.
Documentation validation, vendor-name validation, and whitespace checks passed
after recording the result. These parser-free gates do not qualify the full
project suite or resolve the round-trip defect.

### Production correction approval and impact gate

The maintainer subsequently approved a narrow serializer correction and
regression testing. Before any source edit, read-only audit code reported
CRITICAL upstream impact for `_serialize_logseq_node_lines`: one direct caller,
nine affected symbols, and five affected flow entries in its historical index.
The graph is attached to an older checkout at
`cf11de2fa7573b10d2555391676da3c3fbbe9f30`, ten committed revisions behind the
selected source; its zero-cycle result is historical, not a fresh current-source
cycle qualification. The targeted serializer/parser source has no committed
diff against that anchor. Nevertheless, no current dependency completeness or
safe-mutation decision is inferred from an old index.

Repository policy requires explicit maintainer acceptance of a HIGH/CRITICAL
impact warning. Production changes paused at this additional gate until the
maintainer explicitly accepted it. No source/test edits or further parser
evaluations occurred during that preparation phase. A read-only Luna proposal and the
[bounded correction plan](../superpowers/plans/2026-10-03-scalar-metadata-serialization.md)
preserve eligibility, exclusions, literal regressions, and the no-publication
boundary. Independent Sol High design review returned PASS_WITH_NOTES. Its
material conditions are incorporated into the canonical plan: exclude emitted
scalars that become empty under existing whitespace/quote normalization, use
an explicit scalar-type allowlist, and restrict eligibility conservatively to
normal prose. Empty-value and complex-layout fixtures must preserve exact
legacy output without asserting round-trip correctness for excluded layouts.
This verdict covers the design only; it does not qualify implementation.

### Bounded scalar correction execution

The maintainer explicitly accepted the CRITICAL impact warning and approved the
canonical plan, independent Sol review, and complete local regression gates.
Fresh admission verified the same selected HEAD and preserved all pre-existing
dirty work in the existing feature checkout. No commit or push is authorized.

The focused actual-parse regression first failed in all four LF/CRLF and
two/four-space combinations because the reparsed root lost its genuine scalar
property. A separate derived-key suppression ordering regression also failed.
Twenty-five exact legacy-output fixtures passed against unchanged production
source after correcting a missing required field in the fixture construction.

The local correction changes only a private eligibility predicate and ordering
inside `_serialize_logseq_node_lines`. Eligible nodes have ordinary prose and
at least one emitted nonempty single-line built-in scalar value. The content
heuristic requires every line to start with an alphanumeric character after
removing its existing continuation alignment and rejects selected fence,
query/macro, and logbook markers. Empty lines and retained extra indentation
also fail admission. Empty normalized values, containers, arbitrary objects,
malformed property keys, and the specifically excluded/characterized layouts
retain legacy placement. This is not an exhaustive complex-layout classifier:
alphanumeric-starting constructs such as `1) item` may still be admitted.
Derived keys remain suppressed. Genuine metadata moves before continuations;
late property-like content is not promoted to metadata. Parser, indentation,
child order, property formatting, and write policy remain unchanged.

After correction, 312 focused serializer, pre-release round-trip, compatibility
corpus, and parser regressions passed. The new actual-parse assertions verify
literal values, late literal text, explicit child source UUID, tree invariants,
and the unchanged semantic projection. The alignment test retains its whitespace
assertions but now expects genuine UUID metadata before continuation text.
Ruff and mypy passed for the edited source/test files. This focused result is
not a composite campaign, replay, hosted, package, or release qualification.

Independent GPT-6.1 Sol High implementation review returned PASS_WITH_NOTES for
this bounded local correction and progression to complete regression gates.
No blocking or important new defect was established. It verified the source
and focused-test hashes and inspected the actual diff without running tests.
Its nonblocking eligibility-precision note is recorded above; expanding the
heuristic to recognize every complex layout remains deferred.

### Bounded correction local completion

The controller-owned complete quality gate passed on the reviewed uncommitted
source: repository-wide Ruff, mypy on 103 files, documentation validation,
vendor-name validation, and 1,153 pytest tests passed. Five native-platform tests
were skipped on macOS: the Linux filesystem ABI test and four Windows leaf/
reparse-point tests. Coverage was 89.83%, above the unchanged 80% floor; pytest
completed in 356.64 seconds. No test failure or warning summary was reported.
The final documentation/vendor/whitespace checks followed the evidence update.

Implementation SHA-256:
`f2c01c46e8f3ccac33ff7f8f9eedbf65afedc33de28c3ece37a6a895f37c6dcd`.
Focused test SHA-256:
`d9b02a9ba165a2a551e858f6825c96040abf7f4890f7119860e7c13ee96fdded`.
Independent implementation review SHA-256:
`dcc42dbda36cac6f64c33567154eedaecb66cf47d526b111200e0c75bc71f7b7`.
Complete quality log SHA-256:
`bcabbd6f2cffaaf12109d27f5bf78cb865787a51c80646701e5a5d038e16f6a6`.

Final checks verified unchanged HEAD, unchanged reviewed source/test bytes,
and preserved pre-existing composite harness hashes. Only the reviewed private
serializer source changed in production; no dependency, workflow, parser,
projection, or invariant-helper change occurred. All work remains uncommitted
in the selected existing checkout. The review, full log, and execution ledger
are preserved in the plan-owned ignored workspace on persistent local storage;
no temporary-file-only evidence is required to resume this correction.

This completes the bounded local scalar correction, not the entire composite
assurance increment. Generic replay/import/runtime binding and deduplication
coverage remain unfinished; the smoke/broad campaign and consumed diagnostic
entry point were not invoked. Current whole-repository cycle/dependency topology
was not newly certified from the historical graph, and no new import was added.
No hosted matrix, package publication, release, issue closure, or private-vault
incidence is established. No commit, push, PR, merge, tag, tracker mutation, or
cleanup followed.

### Replay qualification preparation

The maintainer requested continuation after bounded scalar correction completion.
Fresh read-only checks reconfirmed the selected HEAD, eight-file dirty ownership,
and all four reviewed production/test hashes. No implementation, parser run,
replay, campaign, installation, commit, or external mutation occurred during
this preparation phase.

Static source inspection identified remaining draft replay defects:

- The manifest omits `logseq_paths`, package initialization and eager-imported
  source, test package initialization, and the dependency lock. Its claim to
  hash every relevant implementation file is too broad.
- Comparing revisions for equality can accept the sentinel `unavailable` on
  both sides. A real exact forty-character lowercase hexadecimal revision
  must be required before any replay launch.
- Nested result numbers are compared for equality rather than requiring exact
  integer types, and nested key sets are not fully constrained. Numeric coercion
  and unexpected fields must not satisfy receipt identity.
- Nonzero process exit strings such as `exit-1` are incompatible with the
  existing exception-identifier validator; process failures need one consistent
  sanitized representation.

The bounded design under review is developmental source-qualified replay:
complete repository-local source/declaration hashing, strict receipt identity,
runtime compatibility metadata, explicit local import/cwd checks, and matching
child acknowledgment, with fail-closed preflight and pre/post source checks.
Historical receipts remain historical; none is silently upgraded or re-executed.
Real child launches and smoke/broad campaigns remain separate execution gates.

This is not an interpreter/dependency-byte attestation or immutable runtime
snapshot. Python's official [distribution metadata documentation](https://docs.python.org/3.12/library/importlib.metadata.html)
provides installed version and file metadata and notes that distribution names
do not necessarily map one-to-one to imported packages. Version metadata alone
therefore must not be presented as proof of actual executable dependency bytes.
The proposed guarantee and exact test-only correction scope require the
maintainer's bounded design approval before implementation.

Independent GPT-6.1 Sol High design review returned PASS_WITH_NOTES for that
practical contract, not for the existing replay implementation. The selected
proposal modifies only the two composite harness/test files and this evidence
record. Its required acceptance conditions are:

1. A sorted inventory of all repository-local package and assurance Python
   sources, test initialization, the harness test, `pyproject.toml`, and
   `uv.lock`; inventory additions/removals and changed bytes affect identity.
   Locally selected paths only, with regular-file/root/symlink checks.
2. A bounded root-bound Git revision probe, exact new schema and qualification
   label, strict nested keys/types, finite recipes, sanitized field values,
   and canonical `ChildProcessExit` for nonzero positive or negative exits.
   Historical schema-2 receipts are not silently upgraded.
3. An exact selected compatibility descriptor for Python implementation/full
   version, disabled optimization, OS family/release/architecture, Hypothesis,
   Pydantic/Pydantic-core, and optional eager LangChain presence/version.
   Unknown required metadata fails closed. This list does not attest all
   transitive dependency bytes or establish that installed bytes match the lock.
4. Preflight and pre/post source/runtime checks, repository-local module origins
   and child working directory, and sanitized matching child provenance
   acknowledgment. Parser-stage success requires worker evidence. Drift denies
   qualification and stops without retry, retaining any attempted outcome as
   unqualified evidence rather than replacing its context with later hashes.
5. Parser-free RED/GREEN controls for malformed/mismatched receipts, unavailable
   revisions on both sides, missing/added/removed/symlinked sources, bool/float
   integer equivalents, runtime/origin mismatch, positive/negative process
   exits, missing worker evidence, and pre/post drift. Rejected preflight must
   prove zero worker launches; post-run drift must prove one attempt and no
   following launch. Existing finite recipes, oracle controls, child budgets,
   three-second timeout, fail-first behavior, and privacy controls stay intact.

The design assumes a fresh trusted process in an explicitly selected checkout
without concurrent edits. Parent/child pre/post acknowledgment does not prove
resistance to edit-and-restore races, stale bytecode, import hooks, monkeypatches,
or previously loaded parent code. Eager imports occur before the worker gate;
the gate is not an import-time sandbox. Stronger guarantees require a separately
approved immutable-runtime design, not an implicit expansion of this repair.

No source or test edits, parser execution, replay, campaign, full-suite rerun,
installation, commit, push, or tracker change occurred in design preparation.
Documentation, vendor-name, and whitespace checks passed. Owner approval of
this bounded guarantee precedes implementation; actual replay and campaign
execution remain separate gates.

### Approved replay repair execution

The maintainer subsequently approved the bounded test-only repair. Fresh
checks confirmed the same selected revision, eight dirty paths, and unchanged
scalar source and regression-test hashes. One Luna implementation worker owns
only the two composite harness/test files; the controller owns this record.
The new protocol uses schema 3 and the qualification label
`source-qualified-developmental-v1`. Historical schema-2 receipts remain
historical and must not be promoted to the new qualification level.

Implementation verification is limited to guarded parser-free tests and static
and documentation checks. Real parser calls and process launches are denied
inside the test session; bounded Git/runtime and child-transport doubles support
the provenance controls. A separate Sol High review must evaluate the completed
protocol diff before a passing repair claim. This authority does not revive
the consumed diagnostic or authorize a replay, smoke/broad campaign, full parser
suite, commit, push, release, installation, or tracker mutation.

The earlier full quality result applies to the scalar correction checkpoint,
not to these subsequently modified harness bytes. Repair execution and review
results will be recorded separately. Source and selected runtime compatibility
are the intended guarantee, not dependency-byte or immutable-runtime attestation.

The first repair checkpoint passed 49 guarded parser-free tests and focused
Ruff/mypy checks. Independent Sol High implementation review nevertheless
returned BLOCKED on five unmodeled paths: the executing module's `__main__`
identity under module-mode launch; loss of attempted evidence when a post-child probe
is unavailable; inconsistent launch-error subclass classification on replay;
silently incomplete directory enumeration; and acceptance of unknown runtime
metadata. These are harness/provenance defects, not newly observed production
parser failures. Passing modeled tests did not qualify those missing paths.
One bounded Luna repair wave and the same reviewer's rereview address them
under the existing parser-free scope; no actual child launch is authorized.

That repair wave first reproduced the missing contracts with twenty expected
failures and fifty-six passing controls. The controller independently verified
the subsequent checkpoint: 79 guarded parser-free tests passed, and focused
Ruff/mypy passed. The same Sol High reviewer then inspected the repaired paths.
The protected scalar serializer and its regression-test hashes remain unchanged.
No successful runtime replay or campaign is inferred from the simulated controls.

Final disposition: Sol High rereview confirmed all five findings addressed and
returned PASS_WITH_NOTES. Its sole minor note concerned a parsed branch that
did not explicitly assert preservation of the sanitized worker envelope. That
assertion was strengthened; scoped final review returned PASS. The controller
then verified 79 guarded tests passing in 1.92 seconds, clean focused Ruff/mypy,
and unchanged selected HEAD. These are repair-plumbing results only.

Final harness SHA-256:
`7263a0711457a3aebf28948202cf35e849c454d4b6e32f5b65707c83dfe04e94`.
Final harness-test SHA-256:
`0cc5594aa86ab486371df7229bfb5fedf9db3266521560da92a42e44956dea28`.
Scalar source and regression-test hashes remain those of the previously
reviewed correction. Initial and repaired source projections, RED/GREEN reports,
review reports and the execution ledger are preserved on persistent local
storage. Historical receipts were neither rewritten nor promoted.

The bounded parser-free repair is complete locally and remains uncommitted.
At that parser-free repair checkpoint, actual worker startup, smoke/broad
outcomes, replay, the subsequently modified full-suite checkpoint,
native-platform/package/hosted qualification and release readiness remained
unexecuted. Within-block visible-reference deduplication expansion
remains deferred. The next proposed gate is one separately authorized bounded
smoke execution, after fresh anchors and runtime preflight, with at most four
children, three seconds per child, fail-first and no retry. No broad run follows
automatically. No commit, push, PR, merge, release or tracker mutation occurred.

### Subsequently authorized single smoke

The maintainer then authorized one smoke execution with at most four fresh
children, three seconds per child, fail-first and no retry. Fresh checks matched
the selected HEAD, eight dirty paths and all four reviewed source/test hashes.
Actual read-only preflight passed the complete local inventory, selected runtime
compatibility and repository-local module-origin checks. This new authority
covered the smoke, not a retry of the historical diagnostic entry point.

The sole smoke invocation returned exit code 1 and stopped after two children:

- The three-block LF literal case passed the independent original-input model
  and semantic round-trip. Its 329-byte source is the previously failing
  synthetic source, exercised now under the new smoke authority. The earlier
  failure receipt remains unchanged; this is new evidence for the selected
  corrected source, not an upgrade or reinterpretation of that historical run.
- The nine-block nested CRLF case returned `invariant_failure` /
  `AssertionError`, with both check flags false. Its independent model check did
  not complete, so serialization/reparsing was not reached. Source size is
  1,169 UTF-8 bytes; source SHA-256 is
  `9ec34042268d960d32cf43e86efbb80d27dfd11222ac548bdedc25b75da9b2cd`.

The failing finite recipe is:

```json
{
  "seed": 104,
  "shape": "nested",
  "task": "NOW",
  "priority": "C",
  "scheduled": "2026-08-20 Thu",
  "deadline": "2026-08-22 Sat",
  "literal": "plain-value",
  "reference": "Résumé",
  "tag": "caffè",
  "unicode": "🙂",
  "newline": "crlf"
}
```

Schema-3 receipt SHA-256:
`72d88fc53bb31bf03776d288fecc98355baa95634446ae75206dec49033b0958`.
Pre/post provenance SHA-256:
`c5bbf1902c555cb102b6a9ee93e50c25057c2bbd1008c4f4cc281ea920d24578`.
Independent receipt inspection, without replay, passed source/recipe/worker/
stage identity checks and confirmed the failed campaign. Both worker
acknowledgments match the selected context. The receipt's provenance
qualification status is `qualified`; this does not mean the campaign passed.
Selected source and test bytes, HEAD and dirty ownership remained unchanged.

Runtime: CPython 3.12.13, macOS ARM64, Hypothesis 6.168.1, Pydantic 2.13.3,
Pydantic-core 2.46.3 and optional LangChain-core 1.3.3 present. This is selected
runtime compatibility evidence, not dependency-byte attestation or native
Linux/Windows qualification.

The receipt, preflight and outcome records are preserved on persistent local
storage. No retry, remaining child, broad profile, diagnostic entry-point run,
full-suite rerun, correction, commit, publication or tracker mutation followed.
The receipt records two executed children and a cap of four; it does not
establish coverage of any unexecuted recipe.

The precise rejected assertion is not preserved in this source-free envelope.
The failure could reflect an oracle assumption or parser behavior; it is not
yet a confirmed production defect, security incident or data-loss finding.
The next proposed step is bounded read-only source/receipt diagnosis to select
the smallest discriminating check. Any real diagnostic, replay, repair or new
campaign requires separately selected authority. The composite increment
remains unqualified and unpublished.

### Subsequent read-only oracle diagnosis

The maintainer authorized source/receipt diagnosis only. GPT-6 Luna High
investigated; independent GPT-6.1 Sol High assessment returned
**PASS_WITH_NOTES** for the diagnosis and a proposed separately authorized
test-only repair. Neither agent executed the parser, tests, a worker, replay,
diagnostic, or campaign. Independent standard-library UTC arithmetic and
source inspection establish two incorrect expectation literals:

| Supported date | Stored oracle epoch | Correct UTC-midnight epoch | Error |
|---|---:|---:|---:|
| `2026-08-20 Thu` | `1_787_212_800` | `1_787_184_000` | +28,800 seconds |
| `2026-08-22 Sat` | `1_787_385_600` | `1_787_356_800` | +28,800 seconds |

The April/May literals are correct. The failed recipe uses both August dates.
The production date extractor explicitly assigns UTC before calculating epoch
seconds; existing date tests support this date-only UTC-midnight contract.
Changing production to match the erroneous eight-hour offset is not justified.

This is an important assurance defect: the oracle can falsely reject correct
output for affected combinations. It is not demonstrated production corruption,
data loss, or a security vulnerability. The precise historical assertion remains
unknown. If the earlier root sibling-count, content, indentation, source-span,
task, priority, and property checks all pass and the parser follows its UTC
contract, the root scheduled timestamp must reject the August expectation.
That conditional reasoning does not recover the actual runtime assertion or
prove that no other defect exists. Structural checks are interspersed with
recursive comparisons; only the final aggregate invariant helper runs last.
The preserved smoke remains failed, and serialization was not reached in its
second child. No source/test bytes or historical receipts were changed.

The proposed next gate is a separately authorized parser-free repair in the
two composite harness/test files: independent fixed-literal coverage for all
four supported dates, a focused RED observation, then correction of only the
two August integer literals. Exact comparisons, corruption controls, recipe
bounds, protocol, provenance, and execution budgets must remain unchanged.
Focused guarded tests, static checks, and review would qualify that repair only.
Assertion-identifier instrumentation is a separate design decision, not part
of the proposed repair.

A subsequent runtime discriminator would need new explicit authority and
fresh hashes: one bounded evaluation of the exact failed finite recipe, one
child, the existing three-second timeout, no retry, and an evidence-preservation
stop. It would be a cross-source diagnostic evaluation, not exact replay of the
historical receipt. Consumed smoke authority and its unused cap are not reusable.
No correction or new execution occurred during that diagnosis gate.

### Subsequently approved parser-free epoch repair

The maintainer then approved the bounded repair above. Luna added independent
fixed UTC expectations for both schedule and both deadline choices. Four
finite-case controls inspect the generated root epoch fields; a fifth control
pins the supported date sets to the independent expectations. These controls
exercise `build_case`, not production parser helpers or parser output.

Focused RED produced exactly two expected August failures, three passes and
79 deselections. April, May and supported-set coverage passed. The harness
correction then changed only the two erroneous August integer literals.
Focused GREEN passed five controls; the complete guarded harness file passed
84 tests. Controller verification independently passed 84 tests in 1.86 seconds,
focused Ruff and mypy, and whitespace checks. Existing autouse parser/process
denial guards remained active; no production parser or real child was executed.

Independent GPT-6.1 Sol High review returned **PASS**, with no findings, for
requirements and code quality. Exact task-only snapshot comparison confirmed
that model assertions, date properties, independent fixtures, corruption
controls, protocol/schema, provenance, recipe bounds and execution budgets were
unchanged. No assertion instrumentation was added. Final SHA-256:

- Harness: `ce28311e39a5336c53003c3149814329f4ca609ef02563fba975ec09b798dccd`.
- Harness tests: `cbe60f8de31621fd496ff51834e59d05ea9186c2f4818352088618e1c5393890`.

The scalar serializer and its tests, repository HEAD, dirty ownership and
historical smoke receipt remain unchanged. This gate establishes corrected
finite-model expectations, not runtime/parser correctness or Cartesian date
interaction coverage. The historical smoke remains **FAIL**; its exact
assertion remains unidentified. The changed harness has a new source identity,
so its successful parser-free checks cannot upgrade or replay the old receipt
against new bytes. A fresh one-child runtime discriminator, full quality gates,
campaign, commit, push and publication remained separate authorization gates
at that parser-free checkpoint.

### Subsequently authorized single August runtime evaluation

The maintainer next authorized one fresh child evaluation of the previously
failing finite August recipe, with the existing three-second timeout and no
retry. Fresh source/runtime/origin admission passed under the reviewed current
harness/test hashes. The first read-only preflight probe had a controller
manifest-membership error before any child; the corrected probe independently
hashed the protected regression test outside the selected manifest. Neither
the selected manifest contract nor any source/test file was changed.

The controller invoked the existing source-bound single-case worker once.
The old literal-only CLI diagnostic route and strict historical replay gate
were not changed or reused. The private supplemental record explicitly labels
this evaluation cross-source diagnosis, not historical replay or a canonical
smoke campaign. No assertion instrumentation was added.

The sole invocation returned exit 0. Its one child returned `parsed`,
`model_checked=true`, `roundtrip_checked=true`, no exception and no semantic
differences. The recipe is unchanged: seed 104, nested nine-block outline,
NOW/C, August 20 schedule, August 22 deadline, plain-value, Résumé, caffè, 🙂,
and CRLF. Nine blocks constitute one evaluated recipe, not nine independent
cases. The 1169-byte synthetic input SHA-256 remains
`9ec34042268d960d32cf43e86efbb80d27dfd11222ac548bdedc25b75da9b2cd`.
The worker acknowledgement, selected runtime, complete 38-file manifest,
repository-local origins and parent pre/post context match. New context SHA-256:
`fe79237a9c9280968e38fe765a4b823fbe9182684b82e26f3c92e998bd1b99fb`.
Supplemental receipt SHA-256:
`fe795652ec553cbac543730f8d3703286bf06b3f7f0d0cbbc35798a368103772`.

Luna independently validated the receipt through standard-library-only identity,
JSON and hash checks, including all 38 live regular-file manifest entries and
reconstructed synthetic input. Independent Sol High interpretation review
returned **PASS_WITH_NOTES**, with no blocking finding. No parser, worker,
replay or campaign was executed during either review. The post-run host sample
found no matching direct worker; that sample is not universal process-cleanup
attestation. Source/test hashes, HEAD and the same dirty ownership are unchanged.

This result strongly supports the corrected-oracle explanation: the same input
passes after the two reviewed expectation corrections, with unchanged production
sources and selected runtime metadata. It cannot recover the old assertion or
establish exclusive causality. The historical smoke receipt remains unchanged
and **FAIL**. Its unused budget is not reusable, and the new pass does not
qualify unexecuted recipes, broader syntax, a complete campaign, full suite,
coverage, another platform, hosted CI, package or release. Source-qualified
developmental provenance is not interpreter/dependency-byte attestation.

The smallest next proposal is a separately authorized fresh smoke on the current
source identity: cap four children, existing three-second timeout, fail-first,
no retry, a new receipt, and a terminal stop. Broad randomized qualification
and current full-project gates follow only under their own approved scope.
No additional child, correction, suite/campaign execution, commit, push,
publication or tracker mutation followed this single-case evaluation.

### Subsequently authorized fresh smoke after the epoch repair

After returning this activity exclusively to the Parser, the maintainer
authorized the checkpoint's next bounded gate: one fresh smoke, cap four,
three seconds per child, fail-first and no retry. Fresh preflight matched the
same HEAD, eight dirty paths, four protected source/test hashes, complete
38-file context, selected runtime and local module origins.

The sole invocation exited 0. Three recorded recipes completed successfully:
the three-block LF literal input (329 bytes), nine-block nested August CRLF
input (1169 bytes), and mixed thirty-two-block CRLF input (3672 bytes).
Each passed the independent original-input model and semantic round-trip,
with no exception or semantic differences. These are three recipes, not
three parser calls or four distinct generated cases. Four is a maximum;
selection deduplicates before launch. The receipt does not preserve the
collected/skipped candidate list, so its exact discarded identity is not
independently established. No extra child was launched to fill unused capacity.

New smoke receipt SHA-256:
`f320aba4c11f63a4f245841fe609416cd0b2e22424865bd6404dc4c675e8da92`.
Context SHA-256 remains
`fe79237a9c9280968e38fe765a4b823fbe9182684b82e26f3c92e998bd1b99fb`.
The independent post-context and local-origin checks both passed; exit 0
alone does not imply those checks. Controller readback confirmed unchanged
production/test bytes, HEAD and dirty ownership.

Luna's standard-library-only validation independently reconstructed all
three synthetic sources and checked strict receipt identities, stage fields,
canonical recipe/provenance digests and all 38 live manifest hashes.
Its verdict was VALIDATED. Independent GPT-6.1 Sol High phase review returned
PASS_WITH_NOTES, with no blocking finding for this bounded smoke. Neither
review ran project code, a parser, worker, replay, test or campaign.

The historical smoke remains byte-identical and FAIL; its precise assertion
and exclusive causality remain unknown. This new result qualifies only these
three recorded cases under developmental source/runtime compatibility, not
dependency bytes, immutable execution, universal process cleanup, another
platform, broad randomized coverage, the current full suite, package or release.

The authorized smoke is consumed. No further child, retry, broad campaign,
full suite, source correction, commit, publication or tracker change followed.
The next proposal is a separately authorized run of the existing broad
profile: fixed seeds 104, 417 and 911, at most 120 children total, three seconds
per child, fail-first, no retry or minimization, fresh context and receipt,
then a terminal stop. Generation and per-child limits do not provide a hard
overall parent timeout. Current complete quality and package gates remain later
separate steps; this increment and issue #104 are not complete.

### Subsequently authorized broad finite campaign

The next maintainer GO accepted one existing broad profile and, on PASS, current
complete quality and offline local package gates. Fresh admission matched the
selected HEAD, eight existing dirty paths, four protected source/test hashes,
38-file context, selected runtime and local origins. The profile ran once with
fixed seeds 104, 417 and 911, at most 120 children, three seconds per child,
fail-first and no retry or minimization. No extra child filled unused capacity.

The sole invocation exited 0: 119 distinct recipes and case IDs, representing
117 distinct original-source SHA-256 digests. Each completed its independent
original-input model and semantic round-trip without exception or semantic
difference. Seed counts were 41, 39 and 39. The literal baseline appeared under
three recipe seeds but had one source digest. Counts are recipe attempts, not
total parser calls or a proof of uniform independent sampling.

Recorded shapes were root-child-sibling (35), siblings (28), nested (28),
mixed-8 (27) and the fixed mixed-32 edge (1). No wide-32 case was recorded.
All finite field choices appeared somewhere, not every Cartesian combination
or all Markdown syntax. The receipt omits the complete candidate/skip list;
exact skip provenance is therefore not recovered. Existing syntax, security,
filesystem, stress and concurrency exclusions remain unchanged.

Broad receipt SHA-256:
`aadec8bd68f5471f9bbcb989bf0479f56401714ee5c2199151169f9472ec2789`.
Context SHA-256:
`fe79237a9c9280968e38fe765a4b823fbe9182684b82e26f3c92e998bd1b99fb`.
The driver also required matching final context and local origins for success.
Luna independently reconstructed all inputs and validated strict identities,
schemas, hashes and all 38 live manifest files without project execution.
Its verdict was VALIDATED. GPT-6.1 Sol High returned PASS_WITH_NOTES, with no
blocker to the already authorized subsequent gates. Both historical smoke
receipts remained unchanged; the first remains FAIL. The broad authority is
consumed, with no retry or new campaign implied by either review.

### Current complete quality and partial local package qualification

One offline, no-sync complete quality aggregate exited 0. Repository-wide Ruff,
mypy on 103 files, maintained-document and vendor-name checks passed. All 1,202
executed pytest tests passed; five Linux/Windows native filesystem tests were
skipped on macOS. Coverage was 89.83%, above the unchanged 80% floor. Pytest
completed in 348.67 seconds. No failure/error heading was present. A separate
vendor-name check also passed. HEAD, dirty ownership and four protected hashes
matched before and after the complete aggregate.

Complete quality log SHA-256:
`6b126a19f089572095b272751cb6559cfdd6fc2058b2dcf0933336df6afeff94`.

The local offline build used pinned Hatchling 1.30.1 and produced both formats,
including a wheel built from the new sdist. The wheel contract passed version,
METADATA/RECORD, PEP 561 and excluded-dependency checks. Wheel SHA-256:
`6c0a90c48614222cacbfa11030b1817d8147f7d214c40cdbee3836b144dca892`;
sdist SHA-256:
`20867b30b660d3f128bbc1f2fcafd8ff001902499e1d6703492bfe80beeeb25e`.
These are local development artifacts retaining source version 1.11.0, not
the already published release or a newly published distribution.

One offline Twine 6.2.0 tool-resolution attempt stopped because required cache
metadata was unavailable. Twine itself never executed, so this is neither a
distribution-metadata failure nor a passing check. No download or retry occurred;
isolated wheel-installed strict Mypy 1.20.2 remains unexecuted. Qualification
stopped rather than silently replacing these gates with checkout-based typing.

Read-only archive inspection found 36 non-directory wheel entries and 313 regular
sdist members, with no selected forbidden cache/private directories, traversal
members or five exact local-marker matches. Supplemental member-type readback
found no encoded ZIP symlink/unexpected types and no non-regular TAR entries.
Six ZIP entries do not encode a filesystem type; the original helper had assumed
all non-directory wheel entries were regular and did not inspect ZIP link
attributes. That helper limitation is retained, not presented as proof of member
types. This bounded check is not
complete secret detection or a universal privacy guarantee. An initial readback
cardinality assertion stopped before archive inspection because the build output
also contained its generated ignore file; the corrected member selection and
original helper failure were retained. Exact artifacts and private evidence were
preserved in persistent ignored storage. The artifacts precede this terminal
documentation update; future final-distribution qualification must rebuild and
check the final documentation-bearing sdist rather than reuse this fingerprint.

Current quality is PASS; complete package qualification is INCOMPLETE. Hosted
native matrices, release evidence, issue closure and broader #104 work remain
separate. No source repair, dependency/workflow change, commit, push, PR, merge,
release or tracker mutation followed. Obtaining missing metadata and resuming
package execution require a new scoped decision.

Independent GPT-6.1 Sol High terminal review returned PASS_WITH_NOTES for
evidence interpretation, not package or publication readiness. It verified the
quality log and preserved artifact fingerprints and confirmed the three pending
package gates: pinned isolated prerequisites, actual wheel-installed typing,
and a fresh final-documentation build with complete artifact checks.

### Subsequently authorized isolated prerequisite preparation

The maintainer authorized only isolated Twine 6.2.0 and Mypy 1.20.2 preparation
from PyPI, including their necessary dependencies, without changing the project
environment. Live source/test and ownership anchors matched the checkpoint.
An offline isolated environment was created and one registry resolution produced
27 exact package pins with distribution hashes. Requirements SHA-256:
`32861ecbddf6a8a85bcd8a0f6d0dad45fdcfb92a3b30b4243167faefe91963d8`.
These hashes are registry integrity evidence, not signatures or independent
publisher verification.

The sole installer invocation stopped during argument parsing because it
combined mutually exclusive wheel-only and no-build options. No installation
began; independent metadata readback confirmed an empty isolated environment.
No automatic retry occurred. Tool version probes, actual metadata validation,
installed-wheel typing and the final package rebuild remain unexecuted.
The original invocation, resolver output and failure are preserved separately;
historical successful and failed gates remain unchanged. Project source,
lock/configuration and environment metadata matched before and after.

Prerequisite preparation is INCOMPLETE. The smallest next decision is one
corrected install using the already frozen requirements, without repeating
resolution, followed only by metadata/version probes. Package qualification,
commit, publication and tracker mutations remain separate decisions.

### Subsequently authorized corrected prerequisite installation

The maintainer separately approved one corrected isolated installation, reusing
the exact 27-package hash-pinned requirements without another compilation or
new version selection. The installer validated the frozen set, installed those
exact versions, and completed with exit 0. Independent metadata readback matched
all pins; Twine 6.2.0 and Mypy 1.20.2 version commands both exited 0. No actual
artifact check, downstream typing, build or Parser test/campaign ran.

Corrected outcome SHA-256:
`5996ffb4abf93ca1422d310e22848964a5da36f314c7d3587153bbf3cab0a3e7`.
Installed inventory SHA-256:
`506edb2136f6ff941f653a5df3a336b93ef5d0d2ee02fc7670c61b2993dc4582`.
Project source/test, configuration/lock and environment metadata matched before
and after. The original failed installer outcome remains unchanged. Tools,
isolated cache, requirements and both outcomes are retained in persistent ignored
storage. Registry hashes are integrity data, not publisher signatures or complete
interpreter/dependency byte attestation.

Prerequisite provisioning is PASS for these two tools only; complete package
qualification remains INCOMPLETE. Remaining backend/base-package availability
must be established for the next isolated offline gate. No commit, push, PR,
release, publication, tracker mutation or automatic package execution follows.
Independent GPT-6.1 Sol High read-only review returned PASS_WITH_NOTES for this
bounded provisioning evidence. It confirmed the sole invocation correction,
exact inventory, three successful commands and preserved original failure;
it did not qualify the remaining package gates or grant execution authority.

### Final offline local package qualification and publication boundary

One separately authorized offline cycle completed once, without retry. All nine
external stages exited 0: documentation/vendor checks, build, wheel contract,
Twine, fresh typing environment, hash-pinned tool installation, wheel/base
installation, installed-package origin, and strict public API typing. Archive
inspection was a separate in-process check. The typing probe resolved the
installed wheel outside the checkout; it did not execute the API sample or
import Parser at runtime.

The cycle preserved all 312 frozen source files, the four protected source/test
hashes, source revision, dirty ownership and recorded project environment
metadata. The exact inspected artifacts were developmental version 1.11.0,
not a replacement for the published release:

- Wheel, 105,695 bytes, SHA-256
  `6c0a90c48614222cacbfa11030b1817d8147f7d214c40cdbee3836b144dca892`.
- Sdist, 1,287,442 bytes, SHA-256
  `dc11e3bd3730a1fc0e0b200690a33f8ef9820990e34435032e72900602905620`.
- Terminal outcome SHA-256
  `669cb42a79a9cbcc333f4dffd908b593709e8fa001d6d62f7dfac95edeb6622c`.

Inspection reproduced 36 wheel entries, including six without an encoded file
type, and 313 regular sdist entries. All 342 source-bearing member comparisons
matched the frozen bytes. Encoded types, selected forbidden paths and five exact
local privacy markers were checked; this is not universal archive safety or
secret detection. The helper's size check occurs after reading member data and
is not an adversarial pre-allocation boundary. It is used only for these locally
generated artifacts. Cached base dependencies were recorded separately and are
not an exact reproduction of the project lock or hosted runtime. Optional
extras and a fresh sdist consumer installation were not exercised in this cycle.

Independent GPT-6.1 Sol High review returned PASS_WITH_NOTES for this local
cycle. Original failed receipts and earlier incomplete package attempts remain
preserved. This final public completion entry was added after that frozen build;
the preceding sdist fingerprint is historical, not the artifact of this updated
documentary tree. The draft PR's hosted package job must rebuild from its exact
commit. Publication of a branch or draft PR is not a merge or release decision.

### Severity assessment

The confirmed production defect is high-priority semantic correctness for the
tested round-trip combination: genuine metadata and multiline prose. Original
parsing passed the independent model; serialization/reparsing changed metadata
and content. If a caller overwrites a source file with that serialized result,
the semantic change can become persistent. The observed synthetic diagnostic
did not overwrite any user file, and does not establish a security vulnerability,
arbitrary code execution, or lost source bytes. Actual incidence in user vaults
and effects on metadata types excluded from the recipe are unknown.

The twelve differences are four fields at three outline positions, not twelve
independent bugs. The proposed explanation is one misplaced-metadata ordering
mechanism. The focused scalar regression separately verifies explicit child
UUID preservation; the diagnostic family did not contain explicit UUIDs.

The partial-stage validator and nested CLI bugs were medium-priority harness
reliability defects: they hid/misreported the diagnostic but did not alter the
published production parser. False-positive negative controls were a high-
priority assurance defect because they could create unwarranted confidence in
the oracle. Both categories have parser-free repair evidence, not complete
project qualification. Static errors in the draft were development-quality
blockers and are now cleared for the two test files. Generic replay/import/
runtime binding has the bounded parser-free repair evidence above, but its
actual execution remains unqualified. No runtime-exact replay claim or generic
campaign is permitted without separate authorization and executed evidence. These priorities are
qualitative engineering judgments, not CVSS scores or incident measurements.

The approved candidate emits genuine ordinary scalar block metadata before
prose continuation on eligible nodes, preserving the rule that property-like
text already occurring after a soft break stays literal. Drawer and list-
property interactions remain excluded rather than being globally reordered.
The maintainer accepted the impact gate and confirmed the reviewed plan before
implementation. No commit, push, campaign, or tracker mutation follows from the
design review or local correction authorization.

The initial local-completion requirements were that corruption controls establish a passing baseline
and then reject wrong task, property, reference, span, and parent observations.
Protocol controls must reject missing/false check flags and malformed or
misidentified receipts, and exercise timeout and fail-first execution budgets.
Focused regressions, the broad campaign, full quality gates, and independent
implementation review were required; their subsequent evidence is recorded
above. At that pre-publication checkpoint, exact-commit hosted package and
native-platform qualification remained pending; the bounded offline local package cycle passed on its frozen
pre-publication documentary snapshot. A discovered production defect is reported separately
rather than hidden by loosening expectations.

This increment does not complete #104, prove every Logseq Markdown construct,
qualify an unexecuted platform, or establish a performance/security guarantee.
