---
type: Document
title: Experimental Logseq Org parser implementation status
description: Internal evidence and support boundary for the unreleased, read-only Org subset parser.
status: draft
classification: active
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-10-01
verified: 2026-10-01
stale_after: 2026-10-30
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Experimental Logseq Org parser implementation status

> Internal and unreleased experimental work. This page is not a stable API,
> compatibility promise, product support statement, or Logseq Org conformance
> claim. No package-root export or public support-matrix entry is authorized.

## Scope and API boundary

The work implements an explicitly selected, read-only Org file/text parser for
a bounded Logseq OG-oriented subset. The entrypoints live in the private
`logseq_matryca_parser._org_parser` module:
`parse_org_text(text, *, page_title=...)` and
`parse_org_file(path, *, page_title=...)`. They return a source-preserving
private IR and Org-local diagnostics. The caller must supply a non-empty page
title; identity is not derived from the file path, a headline, or `#+TITLE`.
The file path is not included in the parse result or diagnostics.

The parser does not provide graph loading, whole-vault discovery, page or
backlink resolution, a writer or round-trip serializer, watcher integration,
Logseq DB support, or full Org-mode conformance. It is not integrated with
`LogseqGraph.load_directory()`. It adds no package-root export. All recognized
or unrecognized executable-looking Org content remains inert: source/query/
dynamic/macro constructs are not executed or expanded. Links and embeds are
not resolved, and formulas are not evaluated. The explicit file entrypoint
reads only the selected source file through the private source boundary.

## Implemented subset

The implementation follows the finite grammar in the
[approved design](../superpowers/specs/2026-09-29-logseq-org-parser-design.md):

- Source-ordered headings with levels 1–128, literal `TODO`/`DONE`/`WAITING`
  markers, optional A–Z priority, and final tag spans. These are source facts,
  not workflow-state semantics.
- Generic `#+KEY: value` directives; inert source, query, dynamic, and named
  blocks; and opaque macro directives. Blocks do not nest. Only the exact
  matching closer closes an active block. Source/query/dynamic openers and
  macro directives produce bounded warnings; their bodies are never run.
- `:PROPERTIES:` drawers attach to a heading only when immediately following
  it, with ordered key/value spans; unowned drawers remain opaque. An unclosed
  drawer remains opaque through EOF and produces one error at its opener.
- Unordered `- ` lists with ASCII-space indentation in two-space increments.
  A candidate without an active parent is a paragraph, not a list item.
- Date-only `SCHEDULED:` and `DEADLINE:` values in the exact Gregorian
  `<YYYY-MM-DD Ddd>` form. `CLOSED:` and `CLOCK:` are opaque timestamps; ranges,
  repeaters, timezone conversion, and time-tracking behavior are not modeled.
- Paragraph-only `[[target]]` and `[[target][label]]` references. Internal page
  targets remain unresolved; external targets are preserved; `file:` targets
  are marked never-resolved. No target is opened or fetched.
- LF/CRLF line boundaries, one optional initial BOM for recognition, source
  spans over the original unnormalized text, and ASCII space/tab blank-line
  rules. Other unsupported syntax remains source text or an opaque element.

This subset does not establish Logseq's graph identity rules, property
inheritance, configured TODO workflows, block references, embeds, table/media
semantics, macro expansion, or equivalence to Logseq's complete parser.

## Input, resource, and work bounds

Limits are inclusive; crossing a limit returns no document with a fixed
Org-local error. The file reader accepts one absolute caller-selected `.org`
path, capped at 32,767 path code points, and at most 8,388,608 source bytes.
File bytes are size-checked before strict UTF-8 decoding; invalid or truncated
UTF-8 returns `ORG_INVALID_UTF8`. The caller-supplied title is required and is
limited to 1,024 UTF-8 bytes. Title validation scans left-to-right and checks
at most 1,025 code points (4,100 charged title-work units): a surrogate
encountered before byte overflow returns `ORG_INVALID_UNICODE`; the first
valid scalar that pushes the byte count over 1,024 returns
`ORG_PAGE_TITLE_TOO_LARGE` immediately, without inspecting the suffix. Only a
complete in-limit scan classifies an empty or Unicode-whitespace-only title
as `ORG_PAGE_TITLE_REQUIRED`. This validation precedes all file I/O. The
parser allows at most 250,000 logical lines,
100,000 source occurrences, nesting depth 128, and 256 total diagnostics.
Source occurrences include top-level elements, one list node per run, every
list item, property entry, inline link annotation, and heading-tag occurrence.
The 256th diagnostic slot is reserved for a truncation marker if ordinary
diagnostics would exceed 255.

The audited abstract scanner budget is
`W <= 64 * (B + N + T + E + L + 1)`, where `B` is source UTF-8 bytes, `N` and
`T` are source/title code points, `E` is counted source occurrences, and `L` is
indexed logical lines. Its phase ceilings are `8B` file read/decode allowance,
`4N` source scalar/UTF-8 validation, at most `4 * 1,025` title-validation
work units (and no more than `4T`), `4N+L` line
indexing, `16N+2L` recognition/scanning, and `48E+4L+16` allocation/fixed
allowance. This is an abstract charged-work contract, not a CPU-time,
I/O-latency, or wall-clock guarantee. The text entrypoint does not use the
`8B` file allowance.

## File-reader boundary and accepted residuals

The design profile is Linux x86-64 on ext-family filesystems, macOS arm64 on
APFS, and Windows x64 on NTFS, with component-at-a-time no-follow handling,
same-handle checks, a raw path grammar, fixed path-free diagnostics, and
fail-closed behavior outside the profile. This is a qualification target, not
a claim that every release, architecture, filesystem, provider, or mounted
volume is supported.

POSIX paths must be absolute, have a lower-case `.org` leaf suffix, and
contain no empty, `.` or `..` component. Windows also requires a lower-case
`.org` leaf suffix, accepts only drive-rooted backslash paths, rejects
namespaces, ADS, reserved device names and other invalid components, and caps
each component at 255 UTF-16 code units (also respecting the selected
volume's reported maximum component length).

The accepted contract does not promise that rejection has no prior OS/provider
effects; a selected remote-backed path can trigger provider I/O. It does not
prove physical locality, immutable contents while another writer changes the
file, exclusive hard-link provenance, or a hard wall-clock I/O deadline. The
byte cap bounds bytes consumed, not read duration. These residuals do not
authorize broader path access: only the caller-selected source is read.

## Verification and open gates

Evidence below describes the local implementation review only. It does not
imply native platform qualification, stable API status, or a release.

The focused local Org test run before the later filesystem-transition
regressions reported 199 passed and one platform-specific skip.

The final review identified a gap in per-component transition coverage. Two
test-only additions now verify each held POSIX component before proceeding and
define native Windows regular-file, directory, parent-reparse, and leaf-reparse
checks. The focused POSIX/Windows reader tests pass 53 tests and skip five
platform-specific checks on this macOS host. These additions do not qualify
native Windows behavior.

The earlier full-suite skip was the native Linux x86-64 `fstatfs` ABI test,
which cannot qualify Linux behavior on this macOS arm64 host. Final full-suite
evidence after the test-only review repairs and evidence-note edits is recorded
below.

The new `tests/test_org_source_imports.py` regression passed and checks for
static import cycles among the Org source-reader modules. A refreshed local
source audit over the current worktree also returned zero import cycles. This
supersedes the earlier statement that only the base-`HEAD` index had been
checked. The test is a repository regression gate; the audit result is a
current local observation, not hosted CI evidence.

An sdist built from a dirty worktree included maintainer-only data. A separate
clean-source snapshot passed the wheel contract, Twine validation, and
downstream typing checks. This evidence applies only to those exact sanitized
artifacts and does not establish that arbitrary dirty-worktree builds are safe.

### Package-source hygiene diagnosis

The unsafe sdist came from building a dirty maintainer worktree, not from the
tag-triggered release workflow. The repository's ordinary clean-tree check
does not report ignored files. Hatch documents VCS-based sdist selection and
explicit include/exclude controls ([build configuration](https://hatch.pypa.io/1.13/config/build/),
[sdist builder](https://hatch.pypa.io/1.16/plugins/builder/sdist/)).

The current tag workflow runs its pre-flight and artifact build from fresh
checkouts of the exact tag; the build then creates and verifies one immutable
bundle before PyPI publication. The local dirty-build finding therefore does
not demonstrate leakage through that hosted path. Until a separately reviewed
sdist-selection policy and regression gate exist, do not treat arbitrary local
dirty-worktree artifacts as publishable; the sanitized artifact result above
applies only to those exact files. No packaging configuration or release
workflow was changed in this Org-parser tranche.

The initial whole-branch Sol review returned `BLOCKED` for incomplete
held-component transition coverage and a dirty-worktree sdist that included
maintainer-local files. Test-only coverage was added, and a separate clean
source snapshot passed the wheel contract, Twine, and downstream typing checks.
A later review found that the nine-document privacy sanitizer had also changed
historical command wrappers and environment semantics. That documentation
regression is corrected: `rtk`, `UV_NO_SYNC=1`, and command structure are
preserved; only machine-specific path values are replaced with portable
temporary paths. Fresh whole-branch Sol review returned `PASS_WITH_NOTES`; at
that pre-merge point, its remaining note was that native Linux x86-64 and
Windows x64 qualification still needed CI evidence. That evidence is recorded
below. Fresh local diff inventory and a bounded privacy scan found
only intended Org changes and the nine authorized document sanitizations, with
no machine-local path or identifier matches in those nine documents. Minor
inertness-test suggestions remain deferred; source review found no executable
Org constructs.

The final local quality gate passed on Python 3.12.13/macOS arm64 after the
sanitizer correction: Ruff, Mypy across 98 source files,
maintained-documentation and vendor-name checks; 1,032 tests passed, five
platform-specific tests skipped, no warnings, 89.79% coverage, 226.94 seconds.
Test caches and coverage output were isolated outside the checkout. Skips
include Linux `fstatfs` ABI and native Windows reader checks; this is not Linux
or Windows qualification.

A fresh clean-source wheel/sdist gate passed on 2026-10-01 after the latest
status and plan checkpoint correction: wheel contract, Twine 6.2.0, strict
downstream typing on the installed wheel, and artifact privacy review all
passed. The 303-entry sdist contained each of the 16 scoped Markdown documents
exactly once and excluded the local restart handoff plus cache/build artifacts.
The scoped scan found no machine-specific user, home, temporary-directory,
worktree, or cache values; portable `${TMPDIR}` examples in historical plans
remain intentional. These local gates do not qualify native Linux or Windows
execution.

**Native qualification completed (2026-10-01):** PR [#229](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/229) was squash-merged at `09df7069dca553005123162fd24cd847d1b3456c`; its tested head was `2d5ef3b30e3d515841539be58a8dce0a34d5b1aa`. All 14 GitHub check runs completed successfully. The native test matrix passed on `ubuntu-24.04`, `macos-15`, and `windows-2025`, each with Python 3.12 and 3.13; Quality, CodeQL, production dependency audit, wheel/source-distribution contract, dependency review, and static analyses also passed. These results qualify only that exact PR head and matrix, not every OS version, filesystem/provider, or full GNU Org/Logseq conformance. The Linux-native `fstatfs` and Windows checks skipped by the local macOS arm64 run remain skipped in that local run; the hosted native results are separate evidence.

The refreshed local source audit and `tests/test_org_source_imports.py` both report zero Org source-reader import cycles. The D1 full-suite receipt predates this parser and is not current evidence. An earlier default-cache limitation in a documentation check was handled with an isolated environment/cache; maintained-docs, vendor-name, and diff checks passed.

**Remaining scope:** this remains an experimental, unreleased, read-only Org subset parser, not a stable API or full Org compatibility claim. D3 graph loading—including mixed `.md`/`.org` selection, page identity/collisions, namespace and journal paths, aliases/backlinks, indexing, and refresh behavior—requires a separate reviewed design before implementation. Watchers, writing/round-trip, and Logseq DB support remain deferred. PR #229 is merged; no release or package publication is implied by its CI qualification.
