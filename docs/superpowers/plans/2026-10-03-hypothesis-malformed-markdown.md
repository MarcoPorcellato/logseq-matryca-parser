# Bounded malformed Markdown properties — local implementation record

## Approved scope

Extend [issue #104](https://github.com/MarcoPorcellato/logseq-matryca-parser/issues/104)
with test-only, synthetic malformed Markdown generation. The source base is
`5d577631e68e695071a0badd440c7b374ea8931d` (v1.11.0). The existing valid-outline
and semantic round-trip properties remain unchanged.

No production parser, dependency, public API, workflow, graph loader, Org reader,
writer, or consumer integration changes belong to this tranche. A discovered
parser defect requires a separate correction decision; it must not be hidden by
weakening the oracle. Stop before commit, push, pull request, or release.
GitHub issue/project writes and Beads writes or synchronization are outside the
authorization.

## Implementation and acceptance gates

1. Verify the clean source and create a local branch in the existing checkout.
2. Write harness tests first and verify their initial failure. Implement only
   the minimum generation/replay support under `tests/parser_assurance/`.
3. Generate recipes with the existing locked development-only Hypothesis
   6.168.1. Use a finite vocabulary and bounded integer fields, not external
   source text. Reuse the existing adversarial subprocess runner.
4. Run focused regressions and the explicit fast/broad profiles. Stop at the
   first unexpected classification without retries or automatic minimization.
5. Run `make all`, `make vendor-name-check`, wheel/source-distribution metadata
   and downstream typing gates. Inspect the exact artifacts for local material.
6. Obtain independent read-only Sol review. Record proven progress in the
   roadmap/log, leaving #104 open. Preserve any unexecuted-platform limits.

## Generator contract

| Dimension | Bound or policy |
|---|---|
| Families | Incomplete wikilink, open code fence, unresolved strict block reference, broken property-like syntax, unmatched delimiter run |
| Synthetic text | Fixed ASCII/Unicode tokens; LF or CRLF |
| Outline | At most four spine levels, three leaves per spine node, sixteen blocks total; deepest block indentation is eight spaces |
| Properties | Zero to four incomplete property values; at most ten spaces of continuation indentation |
| Delimiter run | One to sixteen backticks |
| Source | At most 16 KiB of UTF-8 |
| Fast profile | At most four distinct recipes per family, twenty parser children total |
| Broad profile | At most twelve distinct recipes per family, sixty parser children total |
| Child execution | Existing parent-enforced three-second timeout, one fresh subprocess per recipe |
| Collection | `derandomize=True`, `database=None`, `deadline=None`, generation phase only; explicit output cap independent of Hypothesis call count |
| Failure handling | Source-free recipe/result receipt and nonzero exit; stop at the first unexpected result; no shrinking or rerun of parser children |

Hypothesis collects bounded recipes before parser execution. Its example setting
is a generation target, not a hard invocation or wall-clock bound. The collector
caps distinct output independently; replay or shrinking cannot multiply parser
children. This is a bounded subprocess-execution budget, not a hard timeout for
the parent command or proof of universal no-hang behavior. No new expensive CI
job is introduced. Ordinary pytest checks the harness and one real case from
each family; the larger generated execution profiles are explicit opt-in runs.

Malformed syntax is deliberately defined as stress input, not an authoritative
Logseq rejection grammar. Most families may parse permissively or raise a typed
parser error. The unresolved, syntactically valid UUID family requires the
existing strict-reference error. Raw exceptions, invariant failures, semantic
round-trip failures, timeouts, and runner failures are never successful results.
The existing worker checks UUID uniqueness, parent/left pointers, UUID paths,
and outline paths for parsed cases. It does not newly check source ranges or
task semantics. Malformed cases do not claim semantic round-trip equivalence;
the valid-input suite remains the authority for its recorded projection policy.

## Running and replaying

From the repository's locked environment:

```sh
uv run --locked python -m tests.parser_assurance.malformed_properties --profile fast
uv run --locked python -m tests.parser_assurance.malformed_properties --profile broad
```

The JSON output contains the recipe schema version, Hypothesis version, child
timeout, exact recipe fields, and the existing source-free classification result
(including source size and SHA-256). It never emits the rendered source or raw
worker output. To replay one case, pass its `recipe` object as JSON to `--recipe`
instead of `--profile`. No generated source file or Hypothesis database is
required. Replay validates finite vocabulary, exact fields, and numeric bounds;
it cannot accept arbitrary source text or parser options. Preserve the source
revision and schema version with a receipt. Replaying the recorded recipe does
not depend on Hypothesis's generated sequence; regenerating an entire sequence
does require the same locked version and generator revision.

## Evidence ledger

- Local runtime: macOS, Python 3.12.13, uv 0.12.16, and locked Hypothesis
  6.168.1. Hosted CI pins uv 0.11.7; this local run does not qualify that tool
  version or the unexecuted Linux/Windows/Python 3.13 matrix.
- Initial harness tests failed because the new support module did not exist.
- Early harness checks exposed two modeling assumptions: arbitrary non-UUID
  reference text is literal, and property continuation lines are deeper than
  block lines. The synthetic fixtures/bound checks were corrected using the
  existing strict-reference contract; no parser change was made.
- Focused new/valid/adversarial/corpus/deep-refresh suite: 103 tests passed.
- Broad profile: 60 isolated cases passed (48 parsed, 12 expected parser errors),
  largest generated source 404 bytes, Hypothesis 6.168.1 and Python 3.12.13.
- Initial `make all`: 1059 tests passed, five native-platform tests skipped,
  89.79% coverage against the unchanged 80% floor. This run preceded the
  review-driven oracle repair and is not the final qualification.
- Independent GPT-6.1 Sol review: initially blocked by acceptance of the wrong
  typed strict-reference error. Negative controls reproduced the gap before
  repair; the local oracle now requires `BlockReferenceError`. Re-review: PASS.
  Collector-overcall and broad-budget controls were added; all thirty-two
  focused harness tests pass. The reviewer inspected files read-only and did
  not independently execute the full quality/package gates.
- Final post-review `make all`: 1064 tests passed, five native-platform tests
  skipped, 89.79% coverage against the unchanged 80% floor; local elapsed time
  231.81 seconds. Ruff, mypy, vendor-name policy, and maintained-document gates
  also passed. The focused Markdown/harness/corpus/deep-refresh/work-growth
  set passed 119 tests. A second broad run after oracle repair passed all sixty
  cases; all twelve typed errors were `BlockReferenceError`.
- The wheel contract, pinned Twine 6.2.0 checks, and isolated downstream strict
  typing with mypy 1.20.2 passed on the rebuilt distributions. Artifact names
  exclude local caches, tracker state, generated distributions, and maintainer
  state. The source archive contains the exact five tranche files; their bytes
  match the checkout and were scanned for local paths, usernames, and token
  markers. Tests and documentation are absent from the wheel. This bounded
  inspection does not claim to audit every historical document for secrets.
- Repeated builds into an in-checkout output folder were found to include
  earlier distributions in the source archive. Those generated outputs were
  conservatively preserved outside the checkout. Qualification used isolated
  build output, not a packaging-policy change. The final archive has no nested
  distributions. The build and pinned metadata checks can use the qualified
  local cache offline after dependency preparation; sandbox cache/network
  failures were not interpreted as product failures or passing evidence.
- Final harness SHA-256:
  `9369c27f24c53fc8b8a91e1e7251204e2cd7a0dd8c72a8da389b73f7e75407b7`;
  harness-test SHA-256:
  `82224fdd0874f76207a32cf82ff6200d98f6755ddd10532f5ed19771a92a9217`.

Local qualification is complete. The final evidence-only documentation update
is checked separately by the maintained-document gate. No commit, push, pull
request, release, GitHub backlog mutation, or Beads mutation was performed.

These are local results for the source base plus the uncommitted tranche, not
hosted CI, released artifacts, or completion of #104. Graph/filesystem and
concurrency properties remain outside this increment. The benefit to Trama is
stronger Parser assurance through the accepted Parser → Plumber → Trama/Brain
boundary, not a direct Trama dependency or integration.

## Primary references

- [Hypothesis settings and phases](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings)
- [Hypothesis execution-count caveats](https://hypothesis.readthedocs.io/en/latest/explanation/test-case-count.html)
- Existing runner: `tests/parser_assurance/adversarial.py`.
- Existing valid properties: `tests/test_parser_properties.py`.
- [Accepted product boundary](../../decisions/ADR-0004-PARSER-PLUMBER-BOUNDARY.md).
