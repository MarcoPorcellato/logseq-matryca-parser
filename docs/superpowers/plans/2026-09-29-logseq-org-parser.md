# Logseq Org Parser Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this plan after its gates pass. Steps use `- [ ]` checkboxes for tracking.

**Goal:** Deliver and locally qualify an evidence-gated, experimental, read-only Logseq OG Org page parser for text and one explicit absolute `.org` path, without changing Markdown behavior. D1 and Sol XHigh design gates are closed; keep native platform limits explicit.

**Architecture:** Keep text parsing and OS-specific file acquisition separate, with private Org IR and source spans. Map only corpus-backed Logseq semantics. The file reader follows the owner-selected three-platform contract below and fails closed outside its exact matrix. Keep Markdown parsing, graph loading, serializers, and watchers unchanged; do not assume an Org-to-`LogseqPage` mapping before corpus evidence.

**Tech Stack:** Python 3.12 and 3.13; pytest; Python standard library only, including POSIX `dir_fd` calls and a Windows `ctypes` binding to `NtCreateFile`. No new runtime dependency.

**Spec:** [`docs/superpowers/specs/2026-09-29-logseq-org-parser-design.md`](../specs/2026-09-29-logseq-org-parser-design.md), with current owner decisions recorded through 2026-10-01.

## Live checkpoint — 2026-10-01

**Authoritative current decision:** at `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`, current design SHA-256 `60a8456ec5c4d2d20662421a7205313756d7931dba800ff74d6b7f6aad985e34`, the maintainer selected one absolute caller-supplied `.org` path, accepted the bounded Linux/macOS/Windows reader policy and its named residuals, and selected the Linux/macOS/Windows profiles, per-handle checks, path grammar, and fixed file diagnostic map. D1 is closed by the recorded owner decision, final-tree checks, and Sol XHigh review. This supersedes every older “choice pending,” text-only, POSIX-only, root-relative, or conditional-reader statement below. The integrated Sol security review passed with notes. The initial whole-branch Sol quality review found two Important issues: held-component transition coverage and a dirty-worktree sdist containing maintainer-local data; test additions and a clean-source package/type gate address those findings. A later review blocked the diff because sanitization had removed `rtk` and `UV_NO_SYNC=1`; the nine-document correction now preserves those wrappers and command semantics while substituting only machine-specific path values. A subsequent whole-branch Sol quality review returned `PASS_WITH_NOTES`; its remaining note is that native Linux x86-64 and Windows x64 qualification must still come from CI. Fresh local diff inventory and the bounded privacy scan found only intended Org changes, the nine authorized documentation sanitizations, and no machine-local path or identifier matches in those nine documents. The final `make all` rerun passed on Python 3.12.13/macOS arm64: Ruff, Mypy across 98 source files, documentation and vendor-name checks; 1,032 passed, 5 skipped, 89.79% coverage, no warnings. A fresh clean-source wheel/sdist gate passed: wheel contract, Twine 6.2.0, strict downstream typing, and privacy review of all 16 affected/current Org Markdown documents. The 303-entry sdist excludes the local restart handoff and cache/build artifacts. The exact source/package gates were repeated after the latest checkpoint update. At this pre-commit checkpoint, the worktree remains detached and uncommitted. Native Linux x86-64 and Windows x64 qualification remain open. A refreshed local source audit and the source-reader regression report zero import cycles.

The contract to implement is: Linux ext-family `f_type == 0xEF53` with `O_PATH` parent descriptors; macOS APFS `f_fstypename == "apfs"` with descriptor-relative `O_NOFOLLOW` walk; Windows x64 drive-root bootstrap and one-component `NtCreateFile` calls using `FILE_OPEN`, shared read/write/delete, synchronous no-alert I/O, and `FILE_OPEN_REPARSE_POINT`. Windows deliberately sets neither `FILE_DIRECTORY_FILE` nor `FILE_NON_DIRECTORY_FILE`; same-handle metadata checks determine directory status, NTFS membership, and the operational leaf predicate `non-directory + non-reparse + FILE_TYPE_DISK`. Windows components are limited to 255 UTF-16 code units and the handle-reported volume limit. CI targets are `ubuntu-24.04` x64, `macos-15` arm64, and `windows-2025` x64, each with Python 3.12 and 3.13. Path cap is 32,767 Unicode code points. Full spelling, access/share masks, ABI, failure map, and tests are specified in Task 5 below and must stay aligned with the design spec.

**D2 implementation checkpoint (2026-09-30):** the experimental parser, source reader, and adversarial corpus tests are present in the selected worktree. A whole-branch Sol review returned `BLOCKED` (no Critical findings): it identified gaps in per-held-component transition coverage and an sdist built from a dirty worktree that included maintainer-local data. Test-only POSIX and native-Windows cases were added for the coverage gap; a separate clean-source snapshot passed the wheel contract and Twine validation, and the same wheel passed fresh strict downstream typing. These repairs had not yet been re-reviewed at that checkpoint. Focused POSIX/Windows reader tests passed 53 and skipped five platform-specific cases on the macOS host. The full quality gate passed on Python 3.12.13/macOS arm64: Ruff, Mypy across 98 files, maintained-docs and vendor-name checks; 1,027 passed, 5 skipped, no warnings, 89.78% coverage. Native Linux x86-64 and Windows x64 remained unqualified.

**Package-source follow-up diagnosis (2026-09-30):** the unsafe sdist was built from the dirty local worktree. Read-only `git check-ignore -v` checks traced observed maintainer-local paths to checkout-local and nested ignore rules, not an explicit tracked sdist allowlist; `make verify-clean` only checks normal `git status --porcelain` output, which omits ignored files. Hatch documents VCS-based default source selection, project/parent `.gitignore` or `.hgignore` discovery, and explicit `include`/`exclude` controls ([build configuration](https://hatch.pypa.io/1.13/config/build/), [sdist builder](https://hatch.pypa.io/1.16/plugins/builder/sdist/)). The tag workflow's pre-flight and build jobs each check out the exact tag afresh, so the local dirty-build leak does not demonstrate a leak through that hosted release path. No package-selection or workflow change was made; arbitrary dirty-worktree builds remain non-publishable, and any durable sdist-selection policy needs separate review.

**Current bounded-input corrections (2026-10-01):** after the Sol High security review, the maintainer approved a bounded, left-to-right title scan. A surrogate encountered before the first valid scalar that takes UTF-8 length above 1,024 bytes returns `ORG_INVALID_UNICODE`; the first valid scalar crossing the limit returns `ORG_PAGE_TITLE_TOO_LARGE` immediately, and the suffix is not inspected. A complete in-limit scan then classifies empty/Unicode-whitespace-only titles as `ORG_PAGE_TITLE_REQUIRED`. The scan is capped at 1,025 scalar checks / 4,100 charged title-work units and still runs before file I/O. A separate regression now maps a POSIX-style absolute spelling such as `/tmp/page.org` to `ORG_FILE_PATH_INVALID` when the selected platform is Windows. Both changes have focused red→green tests; 15 focused cases passed. The final macOS arm64 full-suite and clean-source package gates now pass on this checkpoint; native GitHub Actions qualification remains pending. The macOS-only result is not Linux or Windows qualification.

**Parser-source review record:** parser implementation followed the reviewed D2 design and includes an active ancestor stack, paragraph fallback before depth checking, fatal heading-shaped runs at 129+ stars, ASCII-space/tab-only blank lines, charged lookahead/fallback and temporary allocations, monotone scan cursors, and one-time tuple freezing. Focused tests cover those rules, adversarial limits, side-effect isolation, diagnostics, and file-reader parity. The local abstract work-bound tests pass; do not extend that claim to CPU-time, I/O latency, hard deadlines, provider behavior, or unqualified native platforms.

**D1 closure record:** owner choices are frozen in the spec and this plan, including required non-empty caller `page_title`, no path-derived identity, no source path in results, and accepted no-locality/no-snapshot/no-deadline/provider-effect residuals. D1 closure criteria were satisfied by the final-tree gates and final Sol XHigh review recorded in `docs/log.md`. `parser-0pc` is the selected Org Beads task; only evidence-based updates for this task are in scope. GitHub issue/project writes remain out of scope; the separate CI-only draft-PR authorization is recorded in the current D2 execution sequence.

### Historical decision and verification record — non-normative

The dated notes below preserve how the design evolved. They are historical evidence only. Any statement that an owner choice, reader contract, grammar, residual, or API detail is pending is superseded by the authoritative current decision above and the accepted design spec. Historical review verdicts remain evidence of those earlier snapshots, not approval of the current plan. Current D1/D2 gates are stated in Task 4, Task 5, and the D2 execution sequence.

**Latest owner clarification and independent architecture review (2026-09-29):** the maintainer reconfirmed that the source path must not appear in `OrgDocument` or the parse result. This is distinct from the input-path shape and closes no reader-safety decision. Luna's official macOS review found `O_NOFOLLOW_ANY` rejects symlinks in every supplied path component, while `getattrlistat(FSOPT_NOFOLLOW_ANY)` is only a race-prone precheck; macOS has no reviewed `O_PATH` equivalent. A candidate can retain an all-components-no-follow descriptor, require `fstat` regular-file status before reading, then bound reads from that descriptor. It cannot claim that a special object was never opened or that provider effects are absent. Oldest supported macOS/API availability is unverified. Astra's read-only gate is **BLOCKED for D1**: the path input boundary, supported OS/filesystem/capability matrix, platform bootstrap and leaf predicate, special-object open-side-effect requirement, residual acceptance, and native-binding qualification still need a single explicit contract. Astra recommends one absolute caller-selected path for this one-file/no-vault-containment scope; that is advice, not an owner decision. No code is authorized.

- Managed worktree: `the selected managed worktree`; detached `HEAD` at `cf11de2fa7573b10d2555391676da3c3fbbe9f30`. Primary checkout is separate, dirty/divergent, and untouched.
- At the read-only API decision review, the design SHA-256 was `29db9d6d97cc33f75e8ee0520fca8602f196ee432442e403a86b461622d8fb74` and the plan SHA-256 was `a5a779869d883d47fcf1da111bcb90e40a4deb3b0bdd487abac2a6c9f5b21fb6`. The design was then reconciled against the review; rehash both documents before the final D2 plan review.
- After reconciliation, the design SHA-256 is `cabb97b23d871e5a30cef967f2ee33eedfddcd0ded9e665a6dc09b8a0965802e`; the plan SHA-256 immediately before this verification-evidence update was `9bd04ddeefefa091a04ff48f4106f38a368d0ad19cf411da94f18256dff1e79e`.
- Preserve the existing modified `docs/README.md`, design, plan, six synthetic corpus fixtures, manifest validator, and tests. No primary-checkout file was edited.
- D1 evidence/corpus work is substantially complete: pinned Logseq OG sources, six synthetic fixtures, exact and semantic expectations, provenance/license manifest, and a test-only validator. Independent review found all six fixtures internally consistent; it also confirmed several expectations are Matryca source-only choices, not claims of Logseq output parity.
- Test-only manifest security review: `PASS_WITH_NOTES`. A path-check/read race and manifest-parent symlink hardening remain nonblocking only under the assumption that this checked-in corpus is stable and trusted. Do not reuse this validator as a production file-opening guard.
- Luna's initial read-only corpus check found no semantic contradiction and flagged diagnostic-contract clarity. The live design/checklist now freeze Org-local codes, severity, optional line, privacy limits, and overflow behavior. A follow-up audit at the current design/plan hashes found no remaining diagnostic gap; `ORG_INVALID_UTF8` correctly remains conditional on the input API.
- Fresh full verification (2026-09-29, isolated Python 3.12.13 environment/cache under `isolated temporary storage`): `uv sync --locked --all-extras` — passed; `make all` — passed (Ruff, Mypy across 89 files, vendor-name check, documentation checker, 876 tests, 91.15% coverage); `git diff --check` — passed. The read-only structural cycle check reports zero cycles on the index at this exact `HEAD` (`cf11de2`); `src/` has no dirty changes. This is pre-final-plan verification, not D1 completion.
- Beads was rechecked read-only at the Parser repository's shared `.git/beads-local` tracker after narrow sandbox access: 33 ready tasks, 33 open tasks, zero in-progress, and zero blocked; no Org-specific task matched. No GitHub pull-only sync was run, so remote issue freshness remains unknown. No Beads task was changed.
- The design now specifies inclusive bounds: 8,388,608 UTF-8 source bytes, 1,024 title bytes, 250,000 logical lines, 100,000 non-root IR elements, nesting depth 128, and 256 diagnostics including a terminal truncation marker. It also freezes an Org-local diagnostic schema/code map, UTF-8 counting, BOM/line-ending behavior, source-offset policy, no copied payloads, and fail-closed overflow. Luna's read-only resource and corpus-consistency checks found these contracts defensible if D2 follows the allocation constraints; they remain Org parser proposals, not existing Parser guarantees.
- Official filesystem review confirms no uniform Python standard-library no-follow path API across supported operating systems. Python `dir_fd` is Unix-only; `O_NOFOLLOW_ANY` is macOS-only; Apple/Linux `O_NOFOLLOW` alone protects only the final path component. Byte caps do not guarantee a stable snapshot under concurrent writes.
- **Luna read-only platform-reader study (2026-09-29):** proposed POSIX descriptor-relative component walking for Linux/macOS and a Windows user-mode `NtCreateFile` handle-relative component walker using `RootDirectory` and `FILE_OPEN_REPARSE_POINT`. Microsoft Learn supports those underlying primitives; it does not qualify a Python `ctypes` implementation. The Windows option needs an ABI/threat-model review, Windows adversarial tests, and Sol security review. Neither candidate is implemented or qualified. Residuals include no immutable snapshot under concurrent writes, no portable wall-clock timeout, post-open type checks cannot prevent every special-file open side effect, and unusual or remote-backed filesystem behavior. The study is evidence, not platform/API approval.
- **Maintainer API choice (2026-09-29):** require non-empty caller-supplied `page_title` for both text and explicit `.org` file entrypoints; never derive identity from path, `#+TITLE`, or a headline. Exact type/whitespace/Unicode/byte-limit validation precedence remains to be specified in the final API plan. The result omits source-path provenance.
- Repository evidence confirms OS-independent package metadata and CI across Ubuntu, macOS, and Windows, each on Python 3.12/3.13. POSIX-only path input would remove direct file convenience on Windows.
- Sol XHigh's strict-fidelity follow-up supersedes its earlier text-only recommendation: the approved D2 target includes text and one `.org` path. Text-only or POSIX-only input would narrow that approved capability/platform surface and requires explicit maintainer approval. The existing local-assurance reader is bounded but not a strict cross-platform no-follow drop-in. Luna's later read-only study proposes a cross-platform design but does not select or qualify it. This was a decision memo, not the final D2-plan review or implementation authorization.
- The spec was briefly edited to optionalize the file entrypoint; Sol XHigh identified that as an unapproved capability reduction. The approved text-plus-file target has been restored. Graph-derived page identity remains a separate, deferred decision; this does not remove file input.
- Luna's read-only D2-plan audit found that the test-only manifest validator lacked nested exact/semantic projection validation and source-text agreement. Task 3 below now closes that bounded corpus-schema gap without defining production IR/API types.
- D1 remains open on the exact normative file-reader contract. The maintainer selected cross-platform text plus one explicit `.org` path, the non-empty caller-title rule, and omission of source-path provenance. No Windows mechanism is accepted and no code is authorized. Do not begin parser implementation until root/bootstrap/locality, raw path grammar, object predicate, residuals, title-validation precedence, and API-specific D2 plan pass review.
- Post-reconciliation focused corpus validation: `uv run --no-sync pytest -p no:cacheprovider tests/test_org_assurance.py -q` — 49 passed. Final `make all` on the current D1 tree — Ruff passed, Mypy passed across 89 source files, vendor-name and docs checks passed, 876 tests passed, coverage 91.15%, exit 0. Caches and coverage output were redirected under `isolated temporary storage`; Hypothesis used its in-memory database because the worktree cache was not writable. The initial `make all` attempt had 876 passing tests but failed when coverage could not write under the worktree; the isolated-output rerun passed.
- **D1 remains open.** The maintainer's current scope direction preserves cross-platform text and one explicit `.org` path; it is not acceptance of a reader mechanism. The non-empty caller-supplied `page_title` rule is selected with no path/Org-content derivation, and source path is omitted from `OrgDocument`/result. The remaining D1 blocker is the exact file-acquisition contract, including Windows root/bootstrap/locality, raw path grammar, object predicate, and residual acceptance. Exact title-validation precedence remains a D2 API detail. Do not freeze an API-specific D2 plan or implement parser code before that contract and review gates pass.
- **Sol XHigh conditional-plan review (2026-09-29): BLOCKED for final D2 approval.** Reviewed design SHA-256 `5f09c9e761a90d4f4cacabda458f77efa05fbb2deb052f9541b5e50f3b766eb2` and plan SHA-256 `22d91081fc3a03fcf58d5ba82a2727ba1e038f466da70692dfd663ce5708438b`. Sol found the conditional decision framework sound, but required D1/D2 sequencing to separate a frozen reader contract from D2 implementation qualification; remote-backed path opens to be distinguished from parser-initiated network calls; exact fixed file failure outputs and precedence; and precise `page_title` validation. These corrections are recorded below/in the design. This was read-only advice, not final plan approval or implementation authorization.
- No D2 parser implementation, commit, push, PR, or GitHub mutation has been made.
- Corpus interpretation now explicitly distinguishes caller-supplied `page_title`, source-only unresolved references, ISO timestamp values, malformed-drawer recovery, and deferred Org block-reference syntax from verified Logseq OG behavior.
- **Latest D1 schema tranche (2026-09-29):** Luna read-only review found no fixture inconsistency and confirmed the proposed exact-v1 schemas and cross-record checks. Task 3 now validates fixture-derived exact element and semantic record variants, strict UTF-8 source-text equality, text-mode title agreement, ordered positive spans within source lines, contiguous heading ordinals, prior-parent references, heading-property scopes, ISO dates, and the design's Org-local diagnostic severity map. No production parser or result type was added. TDD evidence: 16 targeted tests failed for the intended missing checks before implementation; focused suite then passed (66 tests). `make all` passed on the code/test tree: Ruff, Mypy (89 files), vendor-name check, documentation check, 893 tests, 91.15% coverage. The first full run exposed one Mypy narrowing issue; the corrected full run passed. Hypothesis used its in-memory database because worktree cache writes are denied. `uv sync --locked --all-extras` passed in the isolated environment. The full suite result predates this checkpoint-only plan edit; after the edit, the documentation checker, vendor-name check, and `git diff --check` were rerun and passed. Read-only structural cycle check at indexed commit `cf11de2fa7573b10d2555391676da3c3fbbe9f30`: 0 cycles. Beads read-only: 33 ready/open, 0 in-progress, 0 blocked; no Org-specific task selected or changed. D1 remains open because file acquisition and title-input decisions still need maintainer resolution.
- **Sol XHigh correction-only follow-up (2026-09-29): PASS.** At `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`, design SHA-256 `0d57a253393ec2e82e09074c3c55df6fca86e42f2f413b8946df5548604070ad`, and plan SHA-256 `f51cda91f15043d43aa7bb6dd68433006250a93db11a23d93bd49e8bba5d7fcc`, Sol verified the corrected phrase “selected and approved normative no-follow acquisition contract” and found no new D1 contradiction. This was a wording-correction review only, not D1 acceptance, final D2 plan review, or implementation authorization. Final D2 review remains blocked on maintainer file-reader and title choices, exact API/title failure precedence, frozen result/IR/API schema, concrete TDD slices, and final D1 gates.
- **Luna read-only API audit (2026-09-29):** found that a required `page_title` Python parameter conflicts with the proposed `ORG_PAGE_TITLE_REQUIRED` diagnostic for an omitted argument; the concrete signature must allow omission at runtime or the diagnostic contract must change. Proposed, not selected: map omitted/`None`/wrong type/empty to the required-title diagnostic, then scan Unicode scalars without creating an encoded copy, returning `ORG_INVALID_UNICODE` if a surrogate occurs before the UTF-8 byte ceiling is crossed, otherwise `ORG_PAGE_TITLE_TOO_LARGE` once the ceiling is crossed, and only then classify whitespace-only input. The exact whitespace set and title policy remain pending maintainer choice; do not encode this proposal as a frozen contract yet.
- **Latest full verification (2026-09-29):** at the same `HEAD`, the complete `make all` gate passed using the existing isolated Python 3.12.13 environment and caches under `isolated temporary storage`: Ruff, Mypy (89 files), vendor-name check, documentation checker, 904 tests, 91.15% coverage, exit 0. Hypothesis used its in-memory database because the managed worktree cache path is not writable. The initial default-cache attempt stopped at a sandbox `Operation not permitted`; it was rerun successfully with the isolated environment. `git diff --check` and a trailing-whitespace scan of the untracked design, plan, and corpus-test source also passed. This verifies the D1 evidence tree only; no parser source was added, and D1 remains open pending the maintainer's two choices.
- **Latest full verification — D1 worktree only (2026-09-29):** exact `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`; plan SHA-256 at run start `580265f905a5a479edd15160980b8ebb1ce54e8f6f81742100f62c6999f791af`; command `make all`; Python 3.12.13; Ruff PASS; Mypy across 89 files PASS; vendor-name-check PASS; documentation checker PASS; 904 tests PASS; 91.15% coverage; Hypothesis used its in-memory database fallback; test phase 46.52s; process exit 0. Isolated environment, dependency/cache, and `coverage output` paths were under `isolated temporary storage`. This verifies the D1 worktree at that exact run state only; it does not close D1 or authorize parser code.

- **Luna final D1 evidence audit (2026-09-29):** at `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`, design SHA-256 `0d57a253393ec2e82e09074c3c55df6fca86e42f2f413b8946df5548604070ad`, plan SHA-256 before that audit correction `64214f66a1dc10e989ec7308d5d6fde7ee251ead53229239133748104faa3eff`, and manifest SHA-256 `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`, Luna verified all six source-fixture hashes, strict UTF-8 exact-source agreement, text-fixture title agreement, project-authored/Apache-2.0 provenance against repository metadata, and fixture coverage for every in-scope matrix row. No independent fixture licensing, provenance, or schema issue was found in that audit. This does not establish parser resource-boundary behavior: the current 100,000-element accounting and depth formula remain unapproved D2 mechanical proposals. The twelve exact/semantic expectation files have no separate manifest digests and are currently untracked, so Git does not yet provide committed history for them; their shapes are covered by strict projection-schema tests, and exact-projection `source_text` is checked against its source fixture. The test-only legacy `file` mode currently sets `page_title=None` and does not infer identity from the fixture path or expectation. After maintainer reader/title choices, decide whether to retain that mode as test-only or adapt it; no path-inference fix is indicated. These findings do not close owner decisions or the final D1 gate.

- **Astra architecture gate (2026-09-29, read-only):** at `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`, design SHA-256 `0d57a253393ec2e82e09074c3c55df6fca86e42f2f413b8946df5548604070ad`, and plan SHA-256 `e4f4da92668b9bca7104d84a08005f71948ea3977262e2d8c7af23992f7c5c67`, Astra concluded the agent must not select Windows NTFS-only, POSIX-only, or text-only scope, nor infer approval of a native Windows filesystem boundary; `page_title` is also a maintainer-owned API decision. These choices materially affect platform behavior and trust assumptions. Astra recommends asking the maintainer whether to approve the existing Windows NTFS-only bounded candidate plus required caller-supplied title, or select another documented boundary. That selection only closes the D1 design decision; it does not authorize implementation, which still requires D1 gates and Sol XHigh plan PASS/PASS_WITH_NOTES without unresolved blockers. Windows implementation would additionally require real Windows adversarial tests and Sol security review.

- **Live checkpoint (2026-09-29):** exact `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`; plan SHA-256 at checkpoint start `4036201728c299c3afc053b73d5c703ebb3161afeee2682e4d30eddad96d314f`; design SHA-256 `f678209e1d8d34ee1dc9e29cf9ad7b6846e52dad87cd674da90724c49d3d0b2d`. Worktree remains detached and dirty: modified `docs/README.md`; untracked canonical plan/design, Org fixtures, assurance directory, and `tests/test_org_assurance.py`. Current `make all`: Ruff, Mypy, vendor-name-check, and documentation checker PASS; 904 tests PASS; 91.15% coverage. This verifies the D1 worktree only; D1 remains open and parser code is not authorized. Read-only Beads now reports `parser-0pc` blocked on maintainer choices; no Beads or GitHub mutation occurred.
- **Post-Astra verification (2026-09-29):** after recording the architecture gate, `make all` passed at the same `HEAD`: Ruff, Mypy (89 files), vendor-name check, documentation checker, 904 tests, 91.15% coverage, exit 0. Hypothesis used its in-memory database because worktree cache writes are denied. Final `git diff --check` and the trailing-whitespace scan passed. No parser source changed; D1 still awaits the maintainer's file-reader and title choices.

## Global Constraints

- Keep persisted documentation, fixture notes, and maintainer-facing text in English.
- Scope the future parser to Logseq OG `.org` files. Do not claim Logseq DB support or full GNU Org conformance.
- Preserve existing Markdown behavior, package-root API, graph discovery/loading, serializers, and watcher contract.
- The selected D2 scope includes text and one explicit absolute `.org` path. Apply the exact Linux/macOS/Windows path, filesystem, handle, leaf, and error policy in Task 5. Never crawl, follow symlinks/reparse points, resolve links, open neighbors, or call network APIs. A caller-selected provider-backed path may itself cause OS/provider I/O. Graph-derived identity, journals, namespaces, and whole-graph containment remain deferred.
- Freeze these experimental parser ceilings in D2: UTF-8 source ≤8,388,608 bytes; page title ≤1,024 UTF-8 bytes; logical lines ≤250,000; non-root IR elements ≤100,000; structural nesting ≤128; diagnostics ≤256 total, with any truncation marker included in that count. No partial document on source/title/line/element/depth overflow; no silent omission; retain source/title once and store spans instead of copied payloads.
- All Org content is untrusted data. Never evaluate Babel, Lisp, shell, macros, queries, dynamic blocks, or embedded commands.
- Do not copy private vaults, upstream fixtures, parser code, or expected outputs. Record SPDX license and project-authored provenance for every owned fixture. Do not add `mldoc` or another parser as a runtime/test dependency. Any automated use of the AGPL-3.0 `mldoc` reference requires separate legal and maintenance review.
- Do not add a generic `source_format` field, stable API claim, GitHub issue/milestone change, release note, graph-loader behavior, or dependency as part of this plan.
- Keep exact-source and semantic projections independently versioned under an Org-only profile. Do not reuse Markdown snapshots or assume Markdown UUID behavior.
- Reverify selected base, full `HEAD`, and working-tree state before each later gate. Historical review anchors are evidence for their recorded revisions, not current runtime or CI qualification.
- This plan does not change Beads. Any Beads update remains limited to the selected `parser-0pc` Org task and must use verified evidence. The current maintainer authorization permits only the sanitized Org change, its local commit, branch push, and a draft CI-qualification PR; it excludes issue/project writes, merge, tag, release, and package publication.

## Review Focus

1. Path/root spoofing and link races — `test_parse_org_file_rejects_path_grammar_and_symlink_components` and `test_parse_org_file_validates_pathlib_fspath_spelling`; exercise POSIX `..`, repeats still present in `os.fspath`, NUL, wrong-case suffix, Windows UNC/device/ADS/reserved/trailing-dot cases, and POSIX-rooted spelling on Windows; assert invalid grammar maps to `ORG_FILE_PATH_INVALID` before any open and no full-path precheck occurs.
2. Cross-device/filesystem transitions — `test_parse_org_file_rejects_non_allowlisted_component_filesystem`; instrument each held handle and prove Linux `0xEF53`, macOS `apfs`, Windows `NTFS` accepted only at every component.
3. Windows ABI/native-boundary errors — `test_org_source_windows_ctypes_layout_matches_abi` plus real-Windows parent/leaf reparse and operational leaf-predicate tests; assert fail-closed unsupported on ABI mismatch.
4. Title/input precedence and limits — `test_org_title_validation_precedes_file_io`; combine wrong type, surrogate, oversized and blank title cases; verify left-to-right precedence, the 1,025-scalar work ceiling, ignored suffix after byte overflow, and no filesystem call on title failure.
5. Untrusted or malformed Org syntax — `test_parse_org_text_keeps_executable_content_inert`; assert no subprocess, eval/exec, network, link resolution, neighbor open, or source mutation for malformed drawers and executable-looking constructs.

POSIX ABI qualification is owned by `test_org_source_posix_fstatfs_layout_matches_abi` on both selected POSIX runners. It verifies only the platform-specific `fstatfs` structure fields actually read by the implementation against the native ABI; no copied cross-platform `struct statfs` layout is allowed. ABI or capability mismatch fails closed.

## Files and ownership

| File or path | Responsibility |
|---|---|
| `tests/fixtures/org/` | Small synthetic `.org` source fixtures, authored for this repository. |
| `tests/org_assurance/manifest.json` | Fixture IDs, hashes, provenance, SPDX license, parser entry mode, and expected projection references. |
| `tests/org_assurance/manifest.py` | Test-only validator API: `load_corpus_manifest(repo_root: Path) -> tuple[OrgFixtureCase, ...]`; raises `CorpusManifestError` with a stable reason code. |
| `tests/org_assurance/exact_v1/` | Versioned source/element structure expectations independent of semantic mapping. |
| `tests/org_assurance/logseq_org_semantic_v1/` | Versioned Logseq-specific semantic expectations and diagnostics. |
| `tests/test_org_assurance.py` | Manifest schema, provenance, hash, profile-version, and path-containment tests; no production parser import. |
| `src/logseq_matryca_parser/_org_parser.py` / `tests/test_org_parser.py` | Private IR, exact `parse_org_text(text, *, page_title=...)` and `parse_org_file(path, *, page_title=...)` entrypoints, text semantics, limits, diagnostics, and inert-content tests. |
| `src/logseq_matryca_parser/_org_source.py` | Private platform dispatcher; accept one `str | Path`, return bounded source bytes or a fixed internal failure code, never path/OS detail. |
| `src/logseq_matryca_parser/_org_source_posix.py` / `tests/test_org_source_posix.py` | Linux/macOS one-component held-dirfd implementation and platform-selected filesystem/path/read/cleanup qualification. |
| `src/logseq_matryca_parser/_org_source_windows.py` / `tests/test_org_source_windows.py` | Windows drive-root bootstrap and one-component `NtCreateFile` implementation; ctypes ABI, filesystem, reparse, leaf predicate, read, and cleanup qualification on real Windows. |
| `docs/superpowers/specs/2026-09-29-logseq-org-parser-design.md` | Record pinned evidence, D1 decisions, included/deferred semantics, API/output boundary, resource contract, and unresolved risks. |
| `docs/superpowers/plans/2026-09-29-logseq-org-parser.md` | Canonical execution plan: D1 evidence, selected API, concrete D2 tasks, reviewer verdict, and final gate receipts. |
| `docs/README.md` | Link the approved design and canonical execution plan. |
| `docs/log.md` | Dated completion note only after D1 validation passes; never imply parser implementation. |

The D1 evidence tranche above did not edit production parser/model/graph code, `pyproject.toml`, `uv.lock`, serializers, or CI workflows. The D2 source files listed here remain blocked until D1 and Sol XHigh plan review gates pass.

## Task 1 — Reverify the base and pin relevant behavior evidence

**Files:** `docs/superpowers/specs/2026-09-29-logseq-org-parser-design.md`

- [x] Capture current branch/ref, full `HEAD`, and dirty state; preserve all unrelated changes. Do not fetch, reset, switch, stash, or overwrite the selected worktree.
- [x] Recheck only primary Logseq OG/Org sources relevant to candidate semantics. Replace mutable source links with full revisions and/or content hashes before treating them as evidence.
- [x] Inspect current path helpers and filesystem contracts. Specifically note that page-title helpers call `Path.resolve()` and that writer/local-assurance limits do not automatically govern a standalone parser.
- [x] Add an evidence ledger distinguishing official Logseq behavior, generic Org syntax, current Parser behavior, and open questions.
- [x] Do not freeze a result type, projection, supported subset, diagnostic schema, or file-reader API before Task 2's corpus evidence exists; the evidence gate preceded these D1 decisions.

**Check:** `git status --short --branch` and `git rev-parse HEAD`; record complete output in the plan notes. Source review is a human evidence gate, not a test pass.

## Task 2 — Build the independent corpus, then complete the D1 gate

**Files:** `tests/fixtures/org/`, `tests/org_assurance/manifest.json`, `tests/org_assurance/exact_v1/`, `tests/org_assurance/logseq_org_semantic_v1/`, `tests/test_org_assurance.py`, the design spec.

- [x] Author minimal synthetic fixtures for evidenced headings, sections, lists, TODO/priority, tags, internal page references, directives/drawers, timestamps, malformed syntax, and inert executable-looking content. Block-reference recognition is explicitly deferred because pinned sources do not prove Org-mode parser acceptance.
- [x] Put unsupported but important constructs in explicit opaque/diagnostic cases; preserve all source bytes/text in expectations. Do not silently omit candidate matrix rows.
- [x] Record each fixture's ID, relative path, SHA-256, `project-authored` provenance, `Apache-2.0` SPDX license, expected exact projection, expected semantic projection, diagnostics, and protected invariant.
- [x] Freeze the exact manifest contract: top-level keys `schema_version` (exact integer `1`), `exact_profile` (`org_exact_v1`), `semantic_profile` (`logseq_org_semantic_v1`), and `fixtures`; each fixture has exactly `id`, `source_path`, `source_sha256`, `provenance`, `license`, `parse`, `exact_expectation`, `semantic_expectation`, and `protected_invariant`.
- [x] Define path bases: `source_path` is repo-relative under `tests/fixtures/org/`; `exact_expectation` is relative under `tests/org_assurance/exact_v1/`; `semantic_expectation` is relative under `tests/org_assurance/logseq_org_semantic_v1/`. All three must be regular, non-symlink files of the expected suffix.
- [x] Reconcile the test-manifest boundary after the owner-selected required-title rule: the initial legacy `file` mode had no manifest-supplied title, returned `page_title=None`, and did not infer identity from the fixture path or semantic expectation. That mode was adapted after the API decision; both entrypoints now require an explicit non-empty fixture `page_title`, and regression tests reject missing or mismatched semantic titles. The helper remains test-only and does not define the production API.
- [x] Define `OrgFixtureCase` as a frozen dataclass with `id`, repo-relative `source_path`, lowercase 64-hex `source_sha256`, `entrypoint` (`text` or `file`), required non-empty `page_title`, repo-relative exact/semantic expectation paths, and nonempty `protected_invariant`. Define `CorpusManifestError(ValueError)` with `.code` limited to the codes listed in the following tests.
- [x] Define only test-helper types and `load_corpus_manifest(repo_root: Path) -> tuple[OrgFixtureCase, ...]`; keep production parser types out of the validator.
- [x] Add named schema, provenance, license, hash, parse-mode, and containment tests; assert exact `CorpusManifestError.code` values.
- [x] Run the focused suite; 49 tests pass. The original red-stage output was not retained, so no RED result is claimed.
- [x] Implement the smallest standard-library JSON validator that makes those tests green. Enforce `.org` sources and JSON expectation files under their respective roots; reject escaping paths and any symlink component.
- [x] Keep tests independent of production parser code and use only pytest temporary directories for malformed-manifest probes; do not mutate checked-in fixtures during negative tests.
- [x] Resolve each current design-matrix row as `in scope`, `opaque with required diagnostic`, or `deferred`; every in-scope claim links to pinned evidence and a fixture.
- [x] Freeze and validate the nested version-1 exact and semantic projection shapes; verify exact `source_text` agrees with its synthetic UTF-8 source fixture. Keep this test-only corpus contract distinct from the production Org IR. Completed and independently recorded in Task 3.
- [x] Record the selected D2 entrypoints, result shape, title-validation precedence, exact file-acquisition policy, failure map, residuals, and qualification tests in the approved design and this plan. This records the owner decision; it does not close D1, qualify implementation, or authorize source edits.
- [x] Freeze resource ceilings and text normalization in the design: source 8,388,608 UTF-8 bytes, title 1,024 UTF-8 bytes, 250,000 logical lines, 100,000 IR elements, nesting depth 128, at most 256 diagnostics, LF/CRLF only, preserved source/title, bounded byte counting, one retained copy, offset spans, and explicit-stack scanning. Generated D2 tests must exercise every cap at −1/limit/+1.
- [x] Freeze the file-source policy in the design and Task 5: absolute path grammar, per-platform root/handle walk and filesystem/leaf predicates, bounded read, fixed no-document outcomes, and qualification gates. Accepted residuals are pre-rejection OS/provider effects, possible provider/network I/O, no physical-locality promise, no immutable snapshot during concurrent writes, and no hard wall-clock deadline. The fixture manifest's legacy `file` mode remains test-only; it does not define the production API or derive page identity.
- [x] Freeze the encoding/line policy for text: UTF-8 byte ceiling, one leading BOM recognized as scanner metadata but retained, no Unicode normalization, lone surrogates rejected, LF/CRLF line breaks, 1-based inclusive lines, empty source has zero lines, and final newline adds no phantom line. The approved file-path entrypoint must bound actual bytes before strict UTF-8 decoding and report invalid or truncated UTF-8 through the fixed Org-local diagnostic contract.
- [x] Freeze diagnostic expectations: records contain only `code`, `severity`, and optional 1-based `line`; use the fixed Org-local code map in the design, no free-form message/context/path/source payload, and no change to the stable diagnostic registry. Overflow reserves slot 256 for `ORG_DIAGNOSTICS_TRUNCATED` and returns no document.

**Checks:** `uv run pytest tests/test_org_assurance.py --collect-only` exits 0; with the stub, `uv run pytest tests/test_org_assurance.py -q` fails at the expected red assertions; after validator implementation, the same command exits 0 and every negative case reports its specified reason code.

**Task 2 exit:** project-owned corpus content and projections are prepared; Task 3 has validated the nested schemas. The owner-selected file-source contract is frozen in the spec and Task 5. D1 remains open until Task 4 passes final quality/evidence gates and the required review accepts the final tree. No parser code may start before D1 is accepted.

**Gate sequencing clarification from Sol XHigh (2026-09-29):** D1 must freeze
the normative file-acquisition contract, trust assumptions, deterministic
failure outcomes, and D2 qualification tests. It must not require the production
reader to already exist or pass those tests; reader implementation and platform
qualification belong to D2. This avoids a circular D1 gate.

## Task 3 — Validate the versioned corpus projection schemas

**Files:** `tests/org_assurance/manifest.py`, `tests/test_org_assurance.py`, and the six versioned expectation JSON files only if a confirmed schema inconsistency requires correction.

- [x] Freeze strict `org_exact_v1` element variants from the project-authored fixtures: exact per-kind keys, field types, positive ordered line spans, and recursive list-item shape. Reject unknown kinds, missing fields, extra fields, booleans where integers are required, and malformed nested values.
- [x] Freeze strict `logseq_org_semantic_v1` record variants for blocks, page properties, references, timestamps, opaque records, and diagnostics. Validate exact allowed keys, field types, line/ordinal relationships, and the fixed diagnostic code/severity contract from the design.
- [x] Verify each exact projection's `source_text` equals the corresponding fixture's bytes decoded as strict UTF-8. For text-mode fixtures, verify the semantic page title agrees with the explicit manifest title; do not decide the production file-entrypoint title rule here.
- [x] Add focused negative tests for distinct schema failure classes; use literal malformed fixtures and run each test red before changing `manifest.py`.
- [x] Keep this helper test-only. Do not import it from production code, define production parser result types here, alter source fixtures, or weaken path/symlink checks.
- [x] Run the focused suite and retain pristine output; report its exact test count: 77 passed after the diagnostics-contract correction.

**Check:** malformed nested expectations fail with stable `projection_path_invalid`; all six checked-in fixture pairs load successfully and preserve their independently versioned content. The independent schema review found that no-document input/resource diagnostics and diagnostic overflow were accepted inside a document projection. The validator now allows only the two diagnostics that can accompany a document (`ORG_OPAQUE_EXECUTABLE_SYNTAX` and `ORG_UNCLOSED_DRAWER`) and rejects more than 255 ordinary diagnostics. TDD evidence: 10 focused regressions failed against the old validator, then all 77 focused tests passed. The reviewer rechecked the correction and confirmed the schema gap is closed; its only note was the stale count, now reconciled here.

## Task 4 — Close D1 with final quality and evidence gates

**Files:** all D1 corpus/manifest files, design spec, D2 plan, `docs/README.md`, and (only after green checks) `docs/log.md`.

- [x] Finish the D1 contract/spec and concrete D2 plan before final D1 review. D1 remains open until its final-tree gates and required review pass; no parser implementation starts before D1 closes.
- [x] Run `uv sync --locked --all-extras` and `uv run pytest tests/test_org_assurance.py -q`; both pass in the selected managed worktree (79 focused corpus tests). The locked environment and all tool caches are isolated under `isolated temporary storage` because the managed worktree is not writable by the shell sandbox.
- [x] Rerun `make all` on the final pre-review design/plan/log tree: Ruff passed; Mypy passed across 89 files; vendor-name and documentation checks passed; all 906 tests passed at 91.15% coverage with Python 3.12.13. Tool caches and coverage output were isolated under `isolated temporary storage`; Hypothesis used its in-memory database because the worktree cache path was not writable.
- [x] Rerun `make vendor-name-check`, audit-code `check(cycles)` with exactly zero `src/` cycles, and `git diff --check` on the final pre-review tree. The index was bound to this exact base commit; `src/` remained unchanged. The post-review closure checks below still must run after the verdict is recorded.
- [x] After the first complete D1 quality gate passed, add a factual dated D1 decision/verification entry to `docs/log.md`. It explicitly says final post-log checks and Sol XHigh review are pending and does not claim D1 closure.
- [x] After the Sol verdict was recorded in `docs/log.md`, rerun the maintained-docs checker with the current date, `make all`, `make vendor-name-check`, `check(cycles)`, and `git diff --check`. All passed after the review; full suite: 906 tests, 91.15% coverage, Python 3.12.13; cycle index bound to this exact base and returned zero cycles. A final status-only tracking edit still requires the last tree check.
- [x] At D1 closure, `docs/log.md` records exact base/head, dirty state, command outcomes, coverage, cycle-audit provenance, Sol verdict, and remaining D2 gates. Evidence contains no private vault contents.

**Execution evidence — partial D1 checkpoint (2026-09-29):** selected managed worktree remains detached at `cf11de2fa7573b10d2555391676da3c3fbbe9f30`; it is intentionally dirty with this plan, the design spec, `docs/README.md`, and the project-authored Org fixtures/assurance tests. `uv sync --locked --all-extras` completed in an isolated `isolated temporary storage` environment. `uv run pytest tests/test_org_assurance.py -q` reported 77 passed. `make all` passed: Ruff, Mypy across 89 files, documentation checks, 904 tests, and 91.15% coverage. Hypothesis used its in-memory database because the managed worktree cache path was not writable. `make vendor-name-check`, the maintained-docs checker after this checkpoint edit, and `git diff --check` passed. The read-only audit-code `check(cycles)` reported zero `src/` cycles at this same HEAD; no production `src/` file changed in this tranche. Beads read-only inventory for this repository showed 33 ready/open tasks, zero in progress, zero blocked, and no Org-specific task; no Beads/GitHub state changed.

**D1 closure gate:** all pre-review checks must pass on the final D1 tree, no D1 safety/API decision may remain unresolved, and the plan/spec must be linked from `docs/README.md`. Final Sol XHigh review must be `PASS` or blocker-free `PASS_WITH_NOTES`; then record the verdict in `docs/log.md` and pass the post-review checks above. Only then is D1 closed. Otherwise report partial/inconclusive and do not advance. No source edits may precede this gate.

## Task 5 — Finalize the API-specific D2 plan and pass Sol XHigh review

**Files:** this canonical plan, design spec, `docs/README.md`.

- [x] Freeze the selected API, caller-title precedence, exact OS/path/filesystem/object policy, diagnostic map, residuals, and named D2 tests below. Do not narrow to text-only or POSIX-only.
- **Final Sol gate:** obtain a read-only `gpt-6-sol` XHigh review of the exact final plan and design after pre-review checks pass. Only `PASS` or blocker-free `PASS_WITH_NOTES` permits the post-review log and checks; D1 closes only when those post-review checks also pass. Repair and re-review any blocker; no source edits before D1 closure. Record the verdict in `docs/log.md`; do not mutate the reviewed spec or plan solely to encode the verdict.
- [x] Keep the existing navigation link unchanged. Run the maintained-docs checker, `make vendor-name-check`, and `git diff --check` for this plan-only edit; bind results to the live tree. D1/full-suite receipts remain historical and separate.

### Selected D2 API and IR contract — Sol XHigh-approved specification

The owner-selected contract is frozen by the design spec, and this API/IR concretization has passed the exact-hash Sol XHigh source-spec gate. The review approves the specification only; it does not prove implementation or the scanner-work bound. The persistent goal authorizes only local D2 implementation. Keep Org types private; do not export them from package root, add `source_format` to shared models, or reuse `LogseqPage`/`LogseqNode`.

Production parser file: `src/logseq_matryca_parser/_org_parser.py`. Use frozen dataclasses and immutable tuples. Retain source string once; represent element payloads as spans, not copied text; store only bounded derived scalar metadata.

```python
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal

class OrgDiagnosticCode(StrEnum):
    OPAQUE_EXECUTABLE_SYNTAX = "ORG_OPAQUE_EXECUTABLE_SYNTAX"
    UNCLOSED_DRAWER = "ORG_UNCLOSED_DRAWER"
    PAGE_TITLE_REQUIRED = "ORG_PAGE_TITLE_REQUIRED"
    PAGE_TITLE_TOO_LARGE = "ORG_PAGE_TITLE_TOO_LARGE"
    INVALID_UNICODE = "ORG_INVALID_UNICODE"
    SOURCE_TOO_LARGE = "ORG_SOURCE_TOO_LARGE"
    LINE_LIMIT_EXCEEDED = "ORG_LINE_LIMIT_EXCEEDED"
    ELEMENT_LIMIT_EXCEEDED = "ORG_ELEMENT_LIMIT_EXCEEDED"
    NESTING_LIMIT_EXCEEDED = "ORG_NESTING_LIMIT_EXCEEDED"
    INVALID_UTF8 = "ORG_INVALID_UTF8"
    DIAGNOSTICS_TRUNCATED = "ORG_DIAGNOSTICS_TRUNCATED"
    FILE_PATH_INVALID = "ORG_FILE_PATH_INVALID"
    FILE_SOURCE_UNSUPPORTED = "ORG_FILE_SOURCE_UNSUPPORTED"
    FILE_SOURCE_REJECTED = "ORG_FILE_SOURCE_REJECTED"
    FILE_READ_FAILED = "ORG_FILE_READ_FAILED"

@dataclass(frozen=True)
class OrgSpan:
    start: int       # 0-based, half-open Unicode-code-point offset into source_text
    end: int
    line_start: int  # 1-based inclusive
    line_end: int

@dataclass(frozen=True)
class OrgDiagnostic:
    code: OrgDiagnosticCode
    severity: Literal["warning", "error"]
    line: int | None = None

@dataclass(frozen=True)
class OrgHeading:
    span: OrgSpan
    title_span: OrgSpan
    level: int
    marker_span: OrgSpan | None
    priority: str | None
    tag_spans: tuple[OrgSpan, ...]

@dataclass(frozen=True)
class OrgReference:
    """Inline annotation nested within one source-line paragraph."""
    span: OrgSpan
    kind: Literal["page", "external", "file"]
    target_span: OrgSpan
    resolution: Literal["unresolved", "never", "not_applicable"]

@dataclass(frozen=True)
class OrgParagraph:
    """One physical source-line unit, not a GNU Org paragraph abstraction."""
    span: OrgSpan
    annotations: tuple[OrgReference, ...]

@dataclass(frozen=True)
class OrgListItem:
    span: OrgSpan
    child_items: tuple["OrgListItem", ...]

@dataclass(frozen=True)
class OrgList:
    span: OrgSpan
    ordered: bool
    items: tuple[OrgListItem, ...]

@dataclass(frozen=True)
class OrgDirective:
    span: OrgSpan
    name_span: OrgSpan
    value_span: OrgSpan

@dataclass(frozen=True)
class OrgProperty:
    key_span: OrgSpan
    value_span: OrgSpan

@dataclass(frozen=True)
class OrgPropertyDrawer:
    span: OrgSpan
    properties: tuple[OrgProperty, ...]
    owner_heading_ordinal: int | None

@dataclass(frozen=True)
class OrgTimestamp:
    span: OrgSpan
    raw_span: OrgSpan
    kind_name: Literal["scheduled", "deadline", "closed", "clock"]
    date_value: date | None  # derived ISO calendar date only for scheduled/deadline

@dataclass(frozen=True)
class OrgOpaque:
    span: OrgSpan
    kind: Literal[
        "source_block", "query_block", "dynamic_block",
        "other_block", "macro_directive", "unowned_property_drawer",
        "unterminated_drawer",
    ]

OrgElement = (
    OrgHeading | OrgParagraph | OrgList | OrgDirective
    | OrgTimestamp | OrgPropertyDrawer | OrgOpaque
)

@dataclass(frozen=True)
class OrgDocument:
    page_title: str  # required, non-empty caller input; no inferred identity
    source_text: str
    elements: tuple[OrgElement, ...]

@dataclass(frozen=True)
class OrgParseResult:
    document: OrgDocument | None
    diagnostics: tuple[OrgDiagnostic, ...]
```

Selected text entrypoint:

```python
def parse_org_text(
    text: str,
    *,
    page_title: object = _MISSING,
) -> OrgParseResult: ...
```

Use the same keyword-only `page_title` contract for `parse_org_file`. Title validation is deterministic and precedes all filesystem calls: omitted or non-`str` returns `ORG_PAGE_TITLE_REQUIRED`. For a `str`, scan left-to-right without creating an encoded copy. A lone surrogate encountered before valid UTF-8 length exceeds 1,024 bytes returns `ORG_INVALID_UNICODE`; the first valid scalar that makes the total exceed 1,024 returns `ORG_PAGE_TITLE_TOO_LARGE` immediately, without inspecting the suffix. Only a complete in-limit scan may classify empty or Unicode-whitespace-only input as `ORG_PAGE_TITLE_REQUIRED`; otherwise preserve the title unchanged. The maximum is 1,025 scalar checks (4,100 charged title-work units). No path, `#+TITLE`, or headline inference is permitted.

Selected file entrypoint:

```python
def parse_org_file(
    path: str | Path,
    *,
    page_title: object = _MISSING,
) -> OrgParseResult: ...
```

After title acceptance and before any OS call, accept only `str` or `Path`; validate the exact spelling exposed at the API boundary (`os.fspath(path)` for a `Path`). Require that spelling to be absolute in the active OS namespace. Reject bytes, relative/drive-relative spellings, NUL, `.`/`..`, empty/repeated/trailing components when present in the exposed spelling, non-lowercase `.org`, and more than 32,767 Unicode code points as `ORG_FILE_PATH_INVALID`. `pathlib.Path` may normalize repeated separators or `.` components before the parser receives it; the parser cannot reject original constructor text no longer represented by `os.fspath`. Add `test_parse_org_file_validates_pathlib_fspath_spelling` to assert this observable API behavior. Do not call `resolve`, `realpath`, `stat`, `lstat`, or full-path open as a precheck. Never return, log, or diagnose the path. Sol XHigh should confirm this API-boundary interpretation does not materially narrow the accepted absolute-path policy.

| Profile | Bootstrap and one-component walk | Same-handle acceptance |
|---|---|---|
| Linux | `ubuntu-24.04` x64; root `/`; `os.open(component, dir_fd=parent_fd)` once per component. Parents use `O_PATH | O_CLOEXEC | O_NOFOLLOW`; leaf uses `O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | O_NOCTTY`. No `openat2`, procfd, or full-path fallback. | Every parent: `fstat` directory and `fstatfs` `f_type == 0xEF53` (ext-family; magic does not distinguish ext2/3/4). Leaf: same descriptor `fstat` regular file plus same `fstatfs` allowlist. |
| macOS | `macos-15` arm64; root `/`; one `os.open(component, dir_fd=parent_fd)` per component. Parents use `O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW`; leaf uses `O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | O_NOCTTY`. | Every parent: `fstat` directory and `fstatfs` `f_fstypename == "apfs"`. Leaf: same descriptor `fstat` regular file and `fstatfs` APFS. No path-wide precheck/fallback. |
| Windows | `windows-2025` x64; accept only `X:\component\...\name.org`. Reject UNC, extended/device namespaces, `/`, ADS colons except drive colon, Win32-invalid/control characters, reserved DOS device basenames, trailing spaces/dots, and empty/dot/dot-dot components. Before native calls, reject any component over 255 UTF-16 code units or the maximum reported from the held volume root. Bootstrap `\??\X:\` with one `NtCreateFile`, `RootDirectory=NULL`, `CreateDisposition=FILE_OPEN`, `DesiredAccess=FILE_READ_ATTRIBUTES | FILE_TRAVERSE | SYNCHRONIZE`, all three share modes, and `FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT`. Open each child as one relative name with `OBJECT_ATTRIBUTES.RootDirectory=held_parent`, `OBJ_CASE_INSENSITIVE`, `FILE_OPEN`, the same sharing/options, and `FILE_READ_ATTRIBUTES | FILE_TRAVERSE | SYNCHRONIZE` for parents or `FILE_READ_DATA | FILE_READ_ATTRIBUTES | SYNCHRONIZE` for the leaf. Do not set `FILE_DIRECTORY_FILE` or `FILE_NON_DIRECTORY_FILE`. | Check every root/child handle before reuse: `FILE_STANDARD_INFO.Directory` must match expected parent/leaf role; `FILE_ATTRIBUTE_TAG_INFO` must not report reparse; `GetVolumeInformationByHandleW` must report NTFS. Leaf additionally requires `GetFileType == FILE_TYPE_DISK`, an operational predicate rather than universal `S_ISREG` proof. Read default stream with synchronous `ReadFile` on the same handle and `lpOverlapped=NULL`. Query/type/API failures fail closed. Full ABI and flag composition remain unqualified until real-Windows gates pass. |

Run qualification matrix on exactly `ubuntu-24.04` x64, `macos-15` arm64, and `windows-2025` x64 with Python 3.12 and 3.13. GitHub's [hosted-runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) maps these labels to Linux x64, macOS arm64, and Windows x64 respectively. Same-handle filesystem checks use Linux [`statfs(2)`/`fstatfs(2)`](https://man7.org/linux/man-pages/man2/statfs.2.html) and Apple's [`statfs(2)`/`fstatfs(2)`](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/statfs.2.html). Missing platform/API/flag/`dir_fd`/filesystem capability returns `ORG_FILE_SOURCE_UNSUPPORTED`; any root or component outside filesystem/object allowlist returns `ORG_FILE_SOURCE_REJECTED`. Read at most 8,388,609 actual bytes from the accepted leaf handle, strict-decode UTF-8 after byte-limit check, and close every handle/descriptor on every path. Never crawl, open neighbors, evaluate content, or resolve links.

Fixed file outcomes return no document, one Org-local `error`, no line, path, OS status/message, exception text, or source snippet. Map path grammar to `ORG_FILE_PATH_INVALID`; unsupported OS/architecture/API/flag/ABI to `ORG_FILE_SOURCE_UNSUPPORTED`; disallowed filesystem/root/object, symlink/reparse, non-directory parent, or wrong leaf predicate to `ORG_FILE_SOURCE_REJECTED`; missing/denied/sharing/query/read error to `ORG_FILE_READ_FAILED`; over-limit bytes to `ORG_SOURCE_TOO_LARGE`; invalid/truncated UTF-8 to `ORG_INVALID_UTF8`. Syntax/resource mapping remains the design's fixed Org-local map. Accepted residuals: open/query/provider side effects may precede rejection; remote/provider I/O may occur; no physical-locality, immutable-snapshot, or hard-wall-clock-deadline promise.

For the selected required-title contract, parser input stays in-memory only for the text function. The text function must not access filesystem, execute content, resolve references, or mutate source. Candidate `OrgSpan` offsets follow the design's Unicode-code-point coordinate system. `page_title`, element syntax, directives, property keys/values, tag spelling, paragraphs, lists, reference targets, timestamp spelling, and opaque contents remain recoverable from retained `source_text` via spans; `level`, `priority`, `ordered`, reference kind/resolution, ISO date-only projection, diagnostic code/severity, and semantic block ordinal/parent ordinal are derived scalars. `OrgReference.resolution` is descriptive only (`unresolved` for an internal page reference without graph context; `never` for file links; `not_applicable` for external links); it must not trigger resolution. `OrgTimestamp.date_value` is populated only for the fixture-backed date-only SCHEDULED/DEADLINE subset; CLOSED/CLOCK remain opaque and have no normalized date. No page/block UUIDs or graph pointers are proposed. The maintainer selected omission of source-path provenance from `OrgDocument` and the public result; the path remains internal to the reader boundary.

### Selected text-parser TDD slices

Production file: `src/logseq_matryca_parser/_org_parser.py`. Tests: `tests/test_org_parser.py`. Existing six fixtures and `tests/org_assurance/manifest.py` supply expectations only; the manifest loader remains test-only. These tests target the selected API and IR contract above.

1. **Corpus agreement:** add `test_parse_org_text_matches_exact_projection_for_each_fixture` and `test_parse_org_text_matches_semantic_projection_for_each_fixture`. Assert all exact-v1 and semantic-v1 records, including opaque content and diagnostics; test count remains six source fixtures.
2. **Source structure:** add `test_parse_org_text_preserves_source_offsets_and_line_spans`, `test_parse_org_text_preserves_heading_order_and_ancestry`, `test_parse_org_text_preserves_nested_list_order`, and `test_parse_org_text_list_parent_uses_active_ancestor_stack`. Assert span slicing, 1-based inclusive lines, heading ordinals/parents, and no copied source payload contract. The list test must include `- A\n  - B\n- C\n    - D` and prove `D` is a paragraph, not a child of stale `B`; the orphan ends the list run and allocates/counts no list item. Candidate BOM test pins first physical-line element span at offset 0 including leading BOM, with token/value subspans after it.
3. **Unsupported and malformed forms:** add `test_parse_org_text_preserves_unknown_workflow_marker`, `test_parse_org_text_keeps_unterminated_drawer_opaque`, `test_parse_org_text_records_inert_constructs`, `test_parse_org_text_warns_once_per_executable_construct`, `test_parse_org_text_leaves_ordinary_paragraphs_undiagnosed`, and `test_parse_org_text_does_not_execute_or_resolve_content`. For the existing fixture, emit one `ORG_OPAQUE_EXECUTABLE_SYNTAX` warning at each opener line for `#+BEGIN_SRC` (line 2), `#+BEGIN_QUERY` (line 6), `#+BEGIN: custom-report` (line 10), and `#+MACRO` (line 14). Exact-v1 keeps macro directive line 14 and expansion paragraph line 15 as separate elements; the semantic opaque record may aggregate both lines as a derived projection. Exact-v1 keeps inert-content lines 15 and 16 as two separate one-line paragraph elements; properties-references lines 9 and 10 likewise stay separate. Line 16 paragraph contains nested file-link annotation; semantic projection emits opaque `file_link` at line 16 with resolution `never`, without I/O or executable-syntax warning. Line 10 properties-references paragraph contains external-link annotation; semantic projection emits opaque `external_link` with no I/O. Only characterized internal `[[Reference Page]]` becomes a page reference, nested in its line paragraph and semantically `unresolved`. `CLOSED` and `CLOCK` stay exact timestamp lines and project as opaque, without warning. Ordinary unrecognized text is a paragraph-line with no diagnostic. The unterminated `PROPERTIES` drawer emits one `ORG_UNCLOSED_DRAWER` error at its opener. Probe subprocess, `eval`/`exec`, network APIs, file/asset opens, neighboring-file reads, and unchanged source.
4. **Input and limits:** add parameterized `test_parse_org_text_enforces_source_bytes`, `..._title_bytes`, `..._line_limit`, `..._element_limit`, `..._nesting_limit`, and `..._diagnostic_limit`, each generated at limit−1/limit/limit+1 without checked-in large fixtures. Apply the D2 element/depth formulas and the exact scanner-work schedule in Resource and diagnostic accounting; Sol XHigh must resolve the bound before source implementation. For the selected shared source-node counter, add `test_parse_org_text_node_budget_counts_heading_tags`, `..._nested_list_items`, `..._property_entries`, `..._inline_annotations`, and `..._mixed_nodes`. For each category and mixed input, exactly 100,000 counted nodes are accepted and attempted node 100,001 returns no document with `ORG_ELEMENT_LIMIT_EXCEEDED`; allocation instrumentation must prove the counter rejects before constructing node 100,001. The tag case uses one heading with enough tags to exercise the boundary. For scanner work, add `test_parse_org_text_scanner_work_is_bounded_over_powers_of_two` and `test_parse_org_text_scanner_work_aborts_at_bound_plus_one`. Use a private test-injected counter; charge source inspection, failed literal/delimiter lookahead, non-consuming iterations, bounded byte work, and fixed-size output initialization. Exercise increasing powers of two and near-cap repeated partial `[[`, `#+BEGIN_...`, timestamp, and drawer/block closer patterns. Assert `W <= 64 * (B + N + T + E + L + 1)` and bound+1 abort, with no timing-only limit. Do not add a public work error. Add `test_parse_org_text_dense_long_line_near_miss_is_bounded` for generated dense long lines/near-miss delimiters within the source cap. Also add `test_parse_org_text_line_and_bom_policy`, `test_parse_org_text_rejects_lone_surrogate`, and title validation/precedence tests for the selected non-empty-title contract. For nesting add `test_parse_org_text_enforces_heading_and_list_depth_at_limit` for heading level and nested-list depth independently at 128 accepted and 129 rejected, plus `test_parse_org_text_uses_max_depth_across_dimensions`: heading level 1 with list depth 128 has total depth 128 and is accepted, not rejected as summed depth 129.
5. **Isolation/non-regression:** add `test_parse_org_text_has_no_filesystem_side_effects` and `test_parse_org_text_calls_are_state_isolated`. Preserve package-root exports and lazy imports; assert existing Markdown projection, `.md` discovery, and `LogseqGraph.load_directory()` behavior remain unchanged. Do not modify those production modules for Org D2.

Additional final-review cases: heading-shaped runs at 128, 129, and 130 stars; a valid list chain at depth 128, a depth-129 candidate with an active depth-128 parent, and an orphan depth-129 candidate that becomes a paragraph because parent validity precedes overflow; empty and ASCII-space/tab-only lines ending a list run; non-ASCII whitespace remaining content; unclosed-drawer property entries charged even when discarded; failed lookahead and paragraph-fallback source reads charged; and each 100,000/100,001 element-count category rejected before allocation of occurrence 100,001.

Focused proposed command after implementation: `uv run pytest tests/test_org_parser.py tests/test_org_assurance.py -q`. No parser test command is authorized or run by this planning edit.

### Selected file-reader success/parity TDD slice

For every owner-selected supported platform, add `test_parse_org_file_matches_text_parser_for_each_fixture_and_supported_platform` to the selected reader test module (`tests/test_org_source_posix.py` or `tests/test_org_source_windows.py`). Iterate all six project-owned `.org` fixtures using fixture IDs as test identifiers; call the explicit file entrypoint with an explicit fixture `page_title`; compare document and diagnostics against `parse_org_text` given identical fixture bytes decoded under the selected UTF-8 contract. Then assert exact-v1 and semantic-v1 projections for file result against both fixture expectation files. The test-only manifest contract requires a non-empty `page_title` for both entrypoints and checks that semantic expectations match the explicit title; preserve this invariant.

The maintainer selected omission of source-path provenance from `OrgDocument` and the parse result, so compare complete documents and diagnostics with no path normalization. Do not include absolute paths in expectation files, diagnostic payloads, assertion IDs, or emitted failure messages. Assert there is no path-bearing diagnostic. Execute parity on every selected supported platform, not only the development host. This slice applies to the selected explicit-file scope once a reader contract is approved; it does not authorize choosing a reader mechanism.

Focused command after D2 authorization and implementation: `uv run pytest tests/test_org_source_posix.py tests/test_org_source_windows.py tests/test_org_parser.py tests/test_org_assurance.py -q`. Expected: all six fixture IDs pass through both entrypoints on each selected supported platform, complete file/text results match with no source-path provenance, and both fixture projections match. This plan edit does not authorize running parser tests.

### Resource and diagnostic accounting — selected limits; security details remain review gates

The list recognizer maintains only the active ancestor stack. For a candidate at depth `d > 1`, pop stack entries at depth `d` or deeper, then require the active top at exactly `d−1`; otherwise emit the line as a paragraph, end the list run, and do not create/count a list item. Parent validation precedes the depth-129 overflow check. A depth-1 item starts or continues the current uninterrupted list run and clears deeper active ancestors. A whitespace-only line is blank only when every code point is ASCII space or tab; it ends the run. Heading-shaped star runs followed by the required space are depth failures at 129 stars or more; malformed star text without that delimiter is a paragraph.

- Source and title limits are inclusive: 8,388,608 UTF-8 source bytes (including retained leading BOM) and 1,024 UTF-8 title bytes. Count without first allocating an unbounded encoded copy; reject lone surrogates.
- Logical lines: at most 250,000 under the frozen LF/CRLF-only line policy; empty source has zero lines; final newline adds no phantom line; lone CR and other Unicode separators remain content.
- IR elements: increment one shared counter before allocating each source-backed syntax node and count exactly once: top-level nodes, nested list items, property entries, inline references/link annotations, and every heading-tag occurrence. Exclude document/result roots, diagnostics, and semantic-v1 test projections. The inclusive limit is 100,000; attempted node 100,001 returns no document with `ORG_ELEMENT_LIMIT_EXCEEDED`. Each production IR node carries fixed O(1) span/scalar overhead. Retain source text once; bound line-index storage by 250,000 logical lines and diagnostics by 256. The production parser does not retain or emit semantic-v1; the test-only projector is deterministic, bounded by the parsed document, may aggregate adjacent macro/expansion elements, and does not duplicate source text. Use explicit stacks, not recursive descent. D2 tests and Sol XHigh review must qualify these rules before implementation; they are not existing parser guarantees.
- Nesting formula: `max(heading_level, nested_list_item_depth)`, each category measured independently from root and never summed. Root is depth 0; valid category level/depth 128 is accepted. Heading-shaped runs at 129 or more stars return no document with `ORG_NESTING_LIMIT_EXCEEDED`. A nested-list depth-129 candidate returns that error only if an active depth-128 parent exists; an orphan candidate becomes a paragraph before the overflow check. Blocks and drawers are non-nesting states and do not contribute to structural depth. Opaque bodies are not evaluated or expanded. D2 tests and Sol XHigh review must qualify the implementation; this is not an existing parser guarantee.
- Diagnostics: at most 256 total in a result. Parse diagnostics carry exactly `code`, `severity`, optional 1-based `line`; no path, message, OS error, source excerpt, or free-form context. Current fixtures establish four `ORG_OPAQUE_EXECUTABLE_SYNTAX` warnings—one each for `#+BEGIN_SRC`, `#+BEGIN_QUERY`, `#+BEGIN: custom-report`, and `#+MACRO`/its expansion—at opener lines 2, 6, 10, and 14. `file:` links, `CLOSED`, `CLOCK`, normal prose, and other unsupported-but-inert opaque content do not receive that warning unless a future reviewed corpus change says otherwise. Unterminated `PROPERTIES` drawer gets one `ORG_UNCLOSED_DRAWER` error at line 2. These are the only current document-diagnostic classes; fixed input/resource failures return no document and one error diagnostic. If a 256th ordinary diagnostic would be emitted, return no document with at most 255 ordinary diagnostics plus `ORG_DIAGNOSTICS_TRUNCATED` (`error`) in slot 256, then stop.
- Scanner work — final Sol XHigh gate, normative proposal in the design: define `B` as actual file bytes read or, for text containing only Unicode scalar values, its UTF-8 byte length computed without an encoded copy. If text contains a lone surrogate, set `B=0` and reject during the `4N` scalar-validation pass before byte-length use. `N` is source code points, `T` title code points, `L` logical lines, and `E` counted source IR occurrences. A private test-injected counter charges source inspection, line-loop work, bounded byte operations, and fixed-size IR/index initialization; require `W <= 64 * (B + N + T + E + L + 1)` and abort at bound+1. The design's exact charge table totals `8B + 24N + 4T + 48E + 7L + 16`. This is a conservative abstract-work claim, not CPU time, decoder-internal instruction count, OS syscall instruction count, or file-I/O latency. The path-spelling pass is separate, single-pass, and bounded by the 32,767-code-point path cap. For text input, `8B` is unused file-I/O/decode allowance; byte-length calculation is charged in `4N`. Decoder internals are not instrumented; one strict decode is precharged by the actual-byte cap as an abstract bounded-work claim. Ordinary diagnostics charge to their source occurrence within its 48E allowance; one fixed input/resource or terminal-truncation diagnostic uses the fixed allowance. Sol XHigh must challenge charge coverage against the exact finite recognizer; pass the stated bound or block and require reconciliation before source edits. Test each charged path, powers of two, and near-cap malformed delimiters. No timing-only limit, public work error, or filesystem-I/O promise.
- Proposed no-document codes remain those in the design: `ORG_PAGE_TITLE_REQUIRED`, `ORG_PAGE_TITLE_TOO_LARGE`, `ORG_INVALID_UNICODE`, `ORG_SOURCE_TOO_LARGE`, `ORG_LINE_LIMIT_EXCEEDED`, `ORG_ELEMENT_LIMIT_EXCEEDED`, `ORG_NESTING_LIMIT_EXCEEDED`, `ORG_INVALID_UTF8`, plus file codes `ORG_FILE_PATH_INVALID`, `ORG_FILE_SOURCE_UNSUPPORTED`, `ORG_FILE_SOURCE_REJECTED`, and `ORG_FILE_READ_FAILED`. Do not add these to stable `DiagnosticCode`.
- Leading U+FEFF is scanner metadata but remains in `source_text`. First physical-line element begins at offset 0 and includes a leading BOM; token/value subspans begin after it; BOM-only source has no elements. Repeated/interior BOMs are not stripped. Pin with an explicit test. No Unicode normalization. Apply the title validation order frozen above; the design/plan review must confirm its interaction with the byte counter before D2 implementation.

Work-bound implementation constraints: use monotone cursors within named scan phases and charge every code-point inspection, including failed lookahead and paragraph fallback. Charge temporary objects, builder slots, final tuple slots, active-stack entries, and diagnostics before allocation; freeze each builder into an immutable tuple exactly once, charge those slots, and release the builder. Do not use source slices, copied token/value strings, regex/backtracking, `find`, `startswith`, `splitlines`, cursor rewinds, or repeated tuple concatenation that bypasses the counter. Keep the per-occurrence `48E` allowance inclusive of temporary and final allocations; abort before an allocation if its charge would exceed the bound. Required counter tests cover dense near-misses, discarded drawer properties, powers-of-two inputs, near-cap inputs, and `bound+1`.

### D2 mechanical IR rules — Sol XHigh-approved specification; implementation proof required

The following deterministic accounting rules and syntax subset are limited to D2. Sol XHigh approved them as specification; required tests and integrated review must still prove the implementation. No owner reader/path choice remains open. They do not add Logseq compatibility claims.

- **Element count and memory:** increment the shared counter before allocating each source-backed syntax node or occurrence. Count top-level nodes, nested list items, property entries (including buffered entries discarded for an unclosed drawer), inline references/link annotations, and every heading-tag occurrence exactly once. A structurally orphaned list candidate is a paragraph and is not allocated or counted as a list item. Exclude document/result roots, diagnostics, and semantic-v1 test projections. Limit 100,000 is inclusive; attempted node 100,001 returns no document with `ORG_ELEMENT_LIMIT_EXCEEDED`. Each production IR node has fixed O(1) span/scalar overhead; source is retained once; line-index and diagnostics storage are bounded by 250,000 logical lines and 256 diagnostics. The production parser does not retain or emit semantic-v1; the test-only projector is bounded by the parsed document and may aggregate adjacent macro/expansion elements without duplicating source text. Use explicit stacks and no recursive descent. Charge temporary and final allocations before construction; freeze each builder to a tuple once.
- **Depth:** `max(heading_level, nested_list_item_depth)`, with each category measured independently from root and never summed. Root is 0. Heading-shaped runs of 1–128 stars are accepted; 129 or more stars followed by the required ASCII space returns no document with `ORG_NESTING_LIMIT_EXCEEDED`; a run without that delimiter is a paragraph. For list candidates, use the active ancestor stack, pop items at the candidate depth or deeper, and validate an active parent at depth `d−1` before applying the depth-129 limit. A missing parent makes the candidate a paragraph, ends the run, and does not count or allocate a list item; a valid depth-129 child returns no document with `ORG_NESTING_LIMIT_EXCEEDED`. Blocks and drawers are non-nesting states and do not contribute to structural depth. Tests must cover heading 128/129/130, valid list depth 128/child 129, orphan depth 129, stale parents, and heading level 1 plus list depth 128 (accepted overall depth 128).
- **Paragraph lines:** every recognized unstructured physical source line is one `OrgParagraph` element/span. Do not join adjacent lines into a multi-line paragraph. This is a Matryca source-line unit chosen to match exact-v1; it is not a GNU Org paragraph-conformance claim. Inline references/link annotations nest in the containing paragraph-line span.
- **Directive/drawer ownership:** preserve each directive in source order as an `OrgDirective`; never use `#+TITLE` as caller identity. For the fixture-backed semantic projection only, `TITLE` and `FILETAGS` before the first heading have document scope. A `PROPERTIES` drawer immediately following a heading belongs to that heading, retains original ordered key/value spans, and projects to `heading:<ordinal>`. Do not inherit, merge, or normalize. A drawer without an immediately preceding heading stays opaque; unterminated drawer remains opaque through EOF with one opener-line error.
- **References and link annotations:** nest inline annotations inside their physical-line paragraph. Only characterized internal `[[Reference Page]]` becomes a page reference with exact target span and semantic `resolution="unresolved"`; never query graph. External and file links remain opaque inline annotations; semantic projection emits `external_link` and `file_link`, with file-link `resolution="never"`. No link causes I/O. `((UUID))` remains opaque/unclassified absent separate evidence.
- **Timestamps:** exact IR keeps each timestamp as its own physical-line node. Only date-only `SCHEDULED`/`DEADLINE` normalize to derived ISO date while retaining raw span. `CLOSED`/`CLOCK` stay opaque in semantic projection, without normalized date or diagnostic. Do not normalize ranges, repeaters, zones, or time tracking.
- **Opaque/diagnostic behavior:** preserve `#+BEGIN_SRC`, `#+BEGIN_QUERY`, `#+BEGIN: custom-report`, and `#+MACRO` directive as opaque exact elements. Emit one `ORG_OPAQUE_EXECUTABLE_SYNTAX` warning per recognized construct at opener line: fixture lines 2, 6, 10, 14 respectively. Exact-v1 keeps macro directive line 14 and expansion paragraph line 15 as distinct nodes; semantic opaque aggregation across lines 14–15 is derived. Ordinary source-line text has no diagnostic. File/external annotations, `CLOSED`, `CLOCK`, and unknown workflow markers remain inert and undiagnosed. Unterminated `PROPERTIES` drawer gets one `ORG_UNCLOSED_DRAWER` error.
- **BOM spans:** retain one leading U+FEFF as scanner metadata. A first physical-line element span begins at offset 0 and includes BOM; token/value subspans begin after it. BOM-only source has no elements; repeated/interior BOMs are not stripped. Pin with an exact source-offset test.

### Historical reader research — superseded, not an implementation path

This section preserves earlier platform research for provenance only. The selected normative reader contract in Task 5 replaces every candidate below. Do not implement or choose among these historical alternatives. The current reader is the Linux/macOS/Windows matrix above; unsupported cases fail closed.

Earlier statements below that no mechanism, grammar, bootstrap, leaf predicate, or residual policy was selected are historical and superseded. The selected contract still has implementation qualification gates, especially the Windows ABI and operational leaf predicate.

**Historical platform-acquisition evidence — facts vs. inference:** Microsoft documents `NtCreateFile.RootDirectory` as directory-handle-relative and `FILE_OPEN_REPARSE_POINT` as bypassing normal reparse processing for the opened component. `FILE_NON_DIRECTORY_FILE` excludes directories but may accept data files, logical/virtual/physical devices, or volumes. `FILE_STANDARD_INFO` reports a `Directory` boolean; `FILE_ATTRIBUTE_TAG_INFO` returns attributes and a reparse tag; `GetFileType` is coarse and `FILE_TYPE_DISK` is not proof of an ordinary regular file. Sources: [`NtCreateFile`](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile), [`FILE_STANDARD_INFO`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info), [`FILE_ATTRIBUTE_TAG_INFO`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_attribute_tag_info), [`GetFileType`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype). Linux `openat2(2)` and Apple `open(2)` were evaluated as alternatives in earlier research; the current contract instead uses the held one-component walks specified above ([`openat2(2)`](https://man7.org/linux/man-pages/man2/openat2.2.html), [`openat(2)`](https://man7.org/linux/man-pages/man2/openat.2.html), [XNU `open(2)`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/open.2)).

Residuals and adversarial reader tests are now explicit in the selected contract and Review focus above. This older evidence predates owner selection and does not replace the normative profile or D2 qualification gates.

```python
def parse_org_file(
    path: Path | str,
    *,
    page_title: object = _MISSING,  # selected required-title contract
) -> OrgParseResult: ...
```

Use the selected required-title candidate for the file entrypoint as for text input. Both retain the design's title-before-I/O ordering. Selected file-source no-document precedence: path grammar (`ORG_FILE_PATH_INVALID`), unavailable platform/capability (`ORG_FILE_SOURCE_UNSUPPORTED`), disallowed root/filesystem/type/symlink/reparse (`ORG_FILE_SOURCE_REJECTED`), OS open/read failure (`ORG_FILE_READ_FAILED`), byte overflow (`ORG_SOURCE_TOO_LARGE`), then strict UTF-8 failure (`ORG_INVALID_UTF8`). Diagnostics reveal no path or OS detail. Byte ceilings do not promise a wall-clock deadline or immutable concurrent-write snapshot; caller-selected remote-backed mounts may trigger OS I/O.

**Historical alternative A — POSIX-only reader (not selected):** Earlier work considered `src/logseq_matryca_parser/_org_source_posix.py`. This is not the selected platform scope and is not an implementation option.

**Historical alternative B — Windows-only reader (not selected):** Earlier work considered Windows-only file input. The selected implementation does include Windows, with the exact drive-root/NTFS/operational-leaf profile above, real Windows ABI/adversarial tests, and a separate Sol security review. Treat this historical prose only as evidence for those gates.

**Historical Windows feasibility note:** Microsoft's compatibility list's omission of `FILE_OPEN_REPARSE_POINT` from documented `FILE_DIRECTORY_FILE` combinations is a documentation gap, not evidence the combination fails. Do not claim undocumented parent/no-follow flag composition is qualified. The selected implementation uses the `NtCreateFile` pattern above and fails closed on any failed native call or same-handle validation. Its leaf predicate is operational, not a universal regular-file proof. The drive-root bootstrap and residual policy are frozen above. ABI/native behavior still requires real Windows CI and Sol security review. Primary sources: [`NtCreateFile`](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile), [`FILE_STANDARD_INFO`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info), [`FILE_ATTRIBUTE_TAG_INFO`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_attribute_tag_info), [`GetFileType`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype).

**Selected Windows D2 TDD/ABI gate:** `test_org_file_rejects_parent_and_leaf_reparse_points`, `test_org_file_rejects_windows_namespaces_and_raw_path_aliases`, `test_org_file_rejects_ads_and_non_default_streams`, `test_org_file_validates_ntfs_leaf_predicate`, `test_org_file_bounds_short_and_growing_reads`, `test_org_file_rejects_invalid_and_truncated_utf8`, `test_org_file_closes_handles_on_success_and_failure`, and `test_org_source_windows_ctypes_layout_matches_abi`. Cover drive/UNC/device namespaces; traversal; ADS/colon; control/length/component limits; reserved names, trailing dots/spaces, case and 8.3 aliases; ordinary file versus device/volume/directory/reparse; non-NTFS and failed volume queries; short reads, cap+1, growth/rename races; UTF-8 failures; and all cleanup paths. ABI assertions must match Windows x64 for `UNICODE_STRING`, `OBJECT_ATTRIBUTES`, and `IO_STATUS_BLOCK`, including field offsets, lengths, handle representation, and NTSTATUS/IO_STATUS_BLOCK interpretation. Run these on the actual selected Windows runner/filesystem, not only mocks; unavailable or mismatched ABI/capability must fail closed as `ORG_FILE_SOURCE_UNSUPPORTED`.

**Historical alternative C — text-only reader (not selected):** Earlier discussions considered text-only scope. The owner-selected contract includes the explicit `.org` path on all three qualified runner profiles; no text-only fallback is permitted.

### Remaining D2 characterization and review gates — no owner choice pending

- The design freezes a finite, fixture-preserving parser-v1 recognizer, IR variants, malformed recovery, tag/link/timestamp spellings, and source-work charge schedule. Sol XHigh reviewed the exact recognizer and found the abstract inequality valid; this does not prove runtime enforcement or claim full GNU Org grammar or Logseq application conformance. Required tests must demonstrate every charge and bound+1 abort.
- Unsupported forms remain source text or use only the fixed diagnostics named by the design. The one-physical-line paragraph unit is a Matryca source representation, not GNU Org paragraph conformance.
- `Path` grammar validates only the spelling surfaced by `os.fspath`; the original constructor text may already have had repeated separators or `.` components normalized. Use the surfaced spelling and do not invent a `Path`-history mechanism.
- The source-node counter, heading/list depth formula, BOM span details, title-byte-count contract, and `W <= 64 * (B + N + T + E + L + 1)` charge schedule have passed Sol XHigh specification review. These are not existing parser guarantees; implementation and tests remain required.
- Windows `ctypes` structure layouts and call/flag composition remain unqualified until the named real-Windows x64 tests pass on `windows-2025` with Python 3.12 and 3.13. A mocked ABI test alone is insufficient. Any mismatch or unavailable required capability must fail closed.
- The owner-approved bounded title precedence is: omitted/non-`str` → `ORG_PAGE_TITLE_REQUIRED`; then scan left-to-right, returning `ORG_INVALID_UNICODE` for a surrogate encountered before overflow, or `ORG_PAGE_TITLE_TOO_LARGE` immediately when a valid scalar takes UTF-8 length above 1,024 bytes; do not inspect the suffix after overflow. A complete in-limit scan then returns `ORG_PAGE_TITLE_REQUIRED` for empty or Unicode-whitespace-only input; otherwise preserve unchanged. Scan ≤1,025 scalars / 4,100 charged title-work units. Validate before every filesystem call.
- Corpus validator allows only two diagnostic codes on a document, not only two records: current inert fixture expects four `ORG_OPAQUE_EXECUTABLE_SYNTAX` warnings, one per recognized source/query/dynamic/macro construct. Preserve that exact contract; ordinary paragraph text, `file:` links, `CLOSED`, and `CLOCK` remain undiagnosed in current fixtures.
- D1 final-tree verification and owner choices are complete, as recorded in the live checkpoint and `docs/log.md`. D2 implementation and native-platform qualification remain open.

**Check:** complete Task 4's D1 artifacts and pre-review checks first, then obtain a final Sol XHigh `PASS` or blocker-free `PASS_WITH_NOTES` on this exact plan/spec. Record that verdict in `docs/log.md` and pass Task 4's post-review checks; only then may D1 be recorded complete and D2 implementation tasks start. This plan edit does not claim D1 completion or authorize source changes.

## D2 implementation and verification gates

These acceptance gates apply to the maintainer-authorized D2 implementation
and CI-qualification tranche:

- Focused tests for exact/semantic corpus projections, every accepted feature, unsupported diagnostics, caller-title determinism, IR nesting/order invariants, source locations, malformed/large/deep input, encoding, both approved entrypoints, and inert untrusted content. Test graph parent/left fields only if a graph projector is separately justified and accepted in scope.
- No-execution probes for subprocess/shell, `eval`/`exec` hooks, network calls, file/link resolution, and adjacent reads; unchanged source bytes and parser-state isolation across repeated parses. Prove the text entrypoint performs no filesystem I/O and the file entrypoint obeys the selected-path contract.
- Exact diagnostic assertions for deterministic codes/severity, line locations, context allow-list, and no absolute paths or source-content leakage.
- Markdown non-regression: fixed semantic projection equality, unchanged package-root exports and optional lazy imports, unchanged `.md` discovery, and no implicit `.org` loading by `LogseqGraph.load_directory()`.
- Required local audit-code `check(cycles)` with exactly `0` cycles in `src/`; if the audit index/tool is unavailable, record the evidence as unverified rather than infer a pass.
- Security review by `security_reviewer_sol` after the parser implementation diff, because this is an untrusted parsing/filesystem boundary; `reviewer_sol` quality review after integration.
- Full repository gates on the exact implementation head: `uv sync --locked --all-extras`, `make all`, `make vendor-name-check`, and `git diff --check`.
- Distribution contract matching `.github/workflows/ci.yml`: assemble a clean temporary source snapshot from the exact intended tree, build one wheel and one sdist there, inspect the complete sdist member manifest for ignored or maintainer-local files, validate the wheel contract, and run Twine validation on both artifacts. Never treat a dirty maintainer worktree build as publishable.
- Clean downstream typing proof matching CI: verify the clean build contains exactly one wheel; record its SHA-256; use a fresh isolated virtual environment, install exactly `mypy==1.20.2` and that wheel, then invoke the environment's interpreter from outside the source tree on `tests/typing_samples/public_api.py`. Confirm the sample imports the installed wheel, not the checkout. Record the wheel identity and exit result; do not reuse a prior environment or type-check the source tree in place.
- Final documentation edits occur before the last docs checker, `make all`, vendor check, package contract, cycle audit, and diff check. If documentation changes package contents after wheel checks, rebuild and repeat package checks. Bind the handoff to final `HEAD` and clean/dirty state.
- Do not mark Org support experimental in the public support matrix until D2 gates pass. Any page-level experimental claim must still state that whole-graph loading, watchers, writing/round-trip, DB graphs, and complete Org conformance are unsupported.

## D2 execution and publication sequence

These are bite-sized implementation steps. Production parser/source edits require Task 4 D1 closure and a Sol XHigh review of the exact current design and plan returning `PASS` or blocker-free `PASS_WITH_NOTES`. That review approves specification only; implementation and work-bound claims require their own tests and reviews. Sol must validate source-node accounting, depth rules, and the stated `B/N/T/E/L` scanner-work bound against the exact recognizer and charge coverage before source edits; any unresolved blocker requires design/plan reconciliation.

1. **Reader tests first (local slice complete; native matrix remains open):** `tests/test_org_source_posix.py` and `tests/test_org_source_windows.py` cover raw path grammar (including observable `os.fspath(Path)` behavior), parent/leaf symlink or reparse rejection, every-component filesystem identity, same-handle type checks, byte cap, UTF-8 errors, diagnostic mapping, and handle cleanup. POSIX tests verify `fstatfs` ABI layout against each native runner. Windows tests assert x64 `UNICODE_STRING`, `OBJECT_ATTRIBUTES`, and `IO_STATUS_BLOCK` sizes/offsets; `NTSTATUS` success/error interpretation versus `IO_STATUS_BLOCK.Status`; handle/null/invalid-handle representation; UTF-16 byte lengths; and exact access/create/share flags. Local macOS arm64 focused run passed 51 tests with one Linux-native test skipped. Actual `ubuntu-24.04` x64 and `windows-2025` x64 Python 3.12/3.13 qualification remains required; mocked Windows checks are not native qualification.
2. **Implement the source boundary (local implementation complete; native matrix remains open):** `src/logseq_matryca_parser/_org_source.py` is the platform dispatcher, `_org_source_posix.py` implements Linux/macOS held-dirfd walks, and `_org_source_windows.py` implements the one-component `NtCreateFile` walk. The internal boundary accepts one `str | Path`; success returns bounded raw bytes; failure carries only a fixed file-diagnostic code and never path/OS text. No full-path-open or fallback path. Sol security review is `PASS_WITH_NOTES` for reader logic only; real Linux and Windows qualification remains pending.
3. **Parser text API by TDD:** add `tests/test_org_parser.py` first, then `src/logseq_matryca_parser/_org_parser.py` implementing private immutable IR, `parse_org_text(text, *, page_title=...)`, fixed Org-local diagnostics, source spans, counters, and inert opaque handling. Run the focused corpus/parser tests; assert exact and semantic projection matches and no filesystem side effects.
4. **File entrypoint integration:** in `_org_parser.py`, implement `parse_org_file(path, *, page_title=...)`; prove title validation precedes all OS calls, read through the source dispatcher, enforce actual-byte cap before strict UTF-8 decode, map source failures to the frozen diagnostics, then delegate decoded content to `parse_org_text`. Add six-fixture file/text parity tests on each qualified OS profile.
5. **Security and regressions:** run adversarial reader tests, inert-content probes, diagnostic privacy checks, repeated-parse isolation, and unchanged Markdown/package-root/graph-loader checks. Request `security_reviewer_sol` High on the parser/filesystem diff and `reviewer_sol` on the integrated change. Re-grade all findings; fix blockers in one TDD pass and rerun the full suite.
6. **Final local gates:** on the final intended diff, run the local cycle audit, focused tests, `uv sync --locked --all-extras`, `make all`, vendor-name check, documentation checks, and `git diff --check`. Assemble a clean temporary source snapshot from the exact intended tree, build wheel and sdist there, inspect the sdist member manifest for maintainer-local or ignored files, then run the wheel contract, Twine checks, and the exact-wheel downstream typing proof. Any failure stops before commit or push.
7. **Maintainer-authorized CI draft:** only after all local gates and Sol reviews pass, commit the experimental Org parser plus the explicitly authorized nine-document privacy sanitation, create `feat/logseq-og-org-parser-ci` if absent, push, and open a draft PR against `main` for the native `ubuntu-24.04`, `macos-15`, and `windows-2025` matrix with Python 3.12/3.13. Keep the PR explicitly not ready to merge. If any CI job fails, stop and report it; no merge, tag, release, publication, Beads/GitHub issue write, or project mutation is allowed.

## Self-review against accepted design spec

- [x] Absolute `str | Path` `.org` file path only; no vault-root contract, path-derived identity, crawling, linked-file reads, or source-path output.
- [x] Selected platform matrix and per-handle filesystem allowlists are explicit: Linux ext-family with `O_PATH` parents, macOS APFS descriptor-relative `O_NOFOLLOW`, and Windows drive-rooted NTFS with one-component `NtCreateFile`/`FILE_OPEN_REPARSE_POINT` and operational leaf predicate.
- [x] Raw grammar cap, title validation precedence, source byte cap, strict UTF-8, fixed no-document diagnostic map, residuals, and title-before-I/O ordering are recorded.
- [x] Runner labels/Python versions, Linux/macOS `fstatfs` ABI test, Windows x64 ctypes ABI test, adversarial component/leaf tests, and fail-closed unsupported conditions are explicit.
- [x] Historical text-only/POSIX-only/root-relative options are labeled superseded and non-normative; they are not live fallbacks.
- [x] D1 final-tree evidence/review precedes D2, and final Sol XHigh plan review precedes source edits; Windows security and real-runner qualification remain separate D2 gates.
- [x] No D1 closure is claimed by this plan edit. No implementation, Beads update, GitHub mutation, commit, or publication occurred as part of this plan edit.

## Explicit later tranches

Do not include D3 whole-graph loading, D4 watcher/incremental refresh, D5 Org writing/round-trip, or Logseq DB access in D2. Each needs its own evidence and approved plan. D3 must resolve mixed-format selection, `.md`/`.org` identity collisions, namespace/journal paths, aliases/backlinks, graph indexing, and unsupported refresh/watch behavior before implementation.

## Current handoff

The local D2 parser and source-reader implementation is present in the isolated worktree. Owner-approved parser corrections and privacy sanitation are applied. A prior whole-branch Sol review returned `PASS_WITH_NOTES`; the 2026-10-01 final local gates passed after the checkpoint correction: `make all` (1,032 passed, five platform-specific skips, 89.79% coverage), explicit `make vendor-name-check`, clean-source wheel contract, Twine 6.2.0, strict downstream typing on the installed wheel, and artifact privacy review. The 303-entry sdist contains each of the 16 scoped Markdown documents exactly once and excludes the local restart handoff and cache/build artifacts. The final source/package gates are complete for this exact tree. The remaining qualification is the native GitHub Actions matrix; this is CI qualification only: do not mark the PR merge-ready, merge it, tag or release it, publish packages, or modify Beads/GitHub issues/projects. The primary checkout remains out of scope and untouched. D3–D5 remain deferred.

## Historical appendix — non-normative checkpoints

Every continuation and review note below records an earlier worktree snapshot. Any earlier status saying a maintainer choice is pending, D1 is blocked on this selected contract, or a candidate is unselected is superseded by the live checkpoint and Task 5. Preserve the old review/evidence results only as historical records; current execution authority and gates are above.

## Continuation checkpoint — 2026-09-29

Historical note: an independent Luna audit found that an earlier 100,000-element candidate omitted potentially million-scale heading-tag spans. Later proposals counted every tag before allocation and added tag-, list-, property-, link-, mixed-node-budget, and dense-long-line tests. The current design further clarifies that semantic-v1 is test-only, not a one-to-one production projection. These D2 proposals remain untested and require final Sol XHigh review; this historical note does not close D1 or authorize parser implementation.

Verification evidence supplied for this checkpoint: `make all` passed before the latest documentation-only accounting edit (Ruff, Mypy 89 files, vendor-name-check, docs checker, 904 tests, 91.15% coverage; Python 3.12.13; Hypothesis in-memory fallback; process exit 0; test phase 46.52s). After that edit, docs checker, vendor-name-check, diff, and whitespace checks passed. No source or test files changed in the accounting edit. This evidence verifies the current D1 worktree only, not parser behavior or completion of D1. Current read-only Beads status: `parser-0pc` remains blocked on maintainer choices for file boundary and title policy; no Beads mutation occurred. The primary checkout was preserved. No GitHub, commit, push, or PR action is authorized or implied.

## Continuation checkpoint — 2026-09-29

Luna's D1 audit verdict is `PASS_WITH_NOTES`; this reviewer result is distinct from D1 completion. At this historical checkpoint, D1 remained `BLOCKED` on maintainer choices for file platform, trusted root, path grammar, object-type policy, caller `page_title`, and result provenance. Later maintainer decisions settled the required caller title and omission of source-path provenance; those two are not current blockers. The reader-contract choices remain open. At this checkpoint, `HEAD` is `cf11de2fa7573b10d2555391676da3c3fbbe9f30`, design SHA-256 is `ee0b10d2996af2de7f4c093b637135ee14413b94ebdc1535d0daaef327498a37`, and manifest SHA-256 is `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`. Historical plan SHA-256 before this checkpoint edit was `96e3aba5d9b065427beb694f784e0b7d35d14ec13a48c62902b7327c2f888ecc`; reverify the final plan hash live after editing rather than embedding a self-hash. Fresh focused corpus result: 77 passed. Docs checker, vendor-name-check, and diff-check: PASS. Read-only Beads status: no Org issues ready/open; `parser-0pc` remains blocked; no Beads mutation. No parser implementation occurred.

## Continuation checkpoint — 2026-09-29

Platform-acquisition documentation update only; no parser implementation. Exact `HEAD`: `cf11de2fa7573b10d2555391676da3c3fbbe9f30`. Design SHA-256 after its evidence update: `ee4b100a7c74a22af33c300f63f19cf2c7ba1a97f44dde61cd50cb53ddd9ceb6`. Corpus manifest SHA-256: `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`. Historical plan SHA-256 before this edit: `420de9ef2dcd295394513bbadc68867fcd0a5c4db837b61322abcde98af392ae`; reverify final plan SHA live after editing instead of embedding a self-hash. Supplied verification evidence: focused corpus 77 passed; docs checker, vendor-name-check, and diff-check passed. Read-only Beads status remains `parser-0pc` blocked; this is a notes-only documentation update, with no Beads mutation. D1 still awaits owner choices; no platform is selected.

## Continuation checkpoint — 2026-09-29

After the platform-acquisition evidence update, `make docs-check` passed with UV cache and project environment redirected to `isolated temporary storage`. A first `make all` attempt stopped at Ruff because the managed worktree cache is not writable; this was an environment permission failure, not a lint finding. The complete rerun with Ruff, Mypy, coverage, pytest, and UV state isolated under `isolated temporary storage` passed: Ruff, Mypy across 89 source files, vendor-name check, documentation checker, and 904 tests; coverage 91.15% (above the 80% gate), Python 3.12.13, exit 0. `git diff --check` also passed. No production source changed. These are D1 worktree checks only: they do not close the unresolved file-reader/title/provenance decisions or qualify a production parser. No Beads/GitHub mutation, commit, push, or PR occurred.

## Continuation checkpoint — 2026-09-29

Windows acquisition feasibility note only; no parser implementation or platform selection. Exact `HEAD`: `cf11de2fa7573b10d2555391676da3c3fbbe9f30`. Design SHA-256 after update: `49e4500284b9d20fe1b0a91b38e1a820ee5a8811a70ad209880f6dc9a28d3167`; corpus manifest SHA-256: `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`. Historical plan SHA-256 before this edit: `c50f2809b4ef810c229d76d5bbfd3f426ccc3c651fb6d835374aba589d1c5d5b`; verify the final plan SHA live after editing rather than embedding a self-hash. Latest full test result supplied: `make all` passed, 904 tests, 91.15% coverage. After this edit, the direct documentation checker, vendor-name-check, `git diff --check`, and whitespace scan passed. Read-only Beads status: `parser-0pc` remains blocked; no Beads mutation. D1 still awaits owner decisions on platform, root/path/object predicate, title, and provenance. No commit or publication.

## Continuation checkpoint — 2026-09-29

Maintainer decisions now recorded: preserve cross-platform text plus one explicit `.org` path and continue reader research; require non-empty caller-supplied `page_title` for both entrypoints with no identity derivation; omit source-path provenance from `OrgDocument` and the parse result. These choices do not select or qualify a file reader and do not authorize parser code. D1 remains open on the normative reader contract: Windows root/bootstrap/locality, raw path grammar, object predicate, mechanism/capability behavior, and residual acceptance. Exact title-validation precedence remains a D2 API detail. POSIX-only or text-only would reduce the selected scope and is not recommended by this plan.

Sol XHigh preliminary platform findings are recorded in the design as documented facts, conservative inferences, and residual risks. Key unresolved points: Microsoft's `FILE_DIRECTORY_FILE` compatibility list omits `FILE_OPEN_REPARSE_POINT` (documentation gap, not proof of incompatibility); a metadata-only no-follow open followed by same-handle checks is an unqualified workaround inference; the NTFS non-directory/non-reparse disk/default-stream predicate is operational, not universal regular-file proof; volume/root bootstrap and mapped/`SUBST` locality remain owner choices. No side-effect-free open, immutable snapshot, hard read deadline, hard-link exclusivity, or malicious-driver protection is claimed.

Latest supplied full `make all` evidence at this exact `HEAD`: Ruff PASS; Mypy across 89 files PASS; vendor-name-check PASS; docs checker PASS; 904 tests PASS; 91.15% coverage; Python 3.12.13; Hypothesis in-memory fallback; process exit 0; test phase 46.52s; environment, caches, and `coverage output` isolated under `isolated temporary storage`. The initial default-cache `make all` attempt could not initialize the sandbox-restricted UV cache before Ruff produced a result; this was environmental, not a Ruff/lint failure. For this documentation update, `make docs-check` likewise stopped before the checker because the default UV cache was sandbox-restricted; direct `python3 scripts/check_documentation.py --root . --profile docs/maintained.toml --as-of-date 2026-09-29` passed. `make vendor-name-check`, `git diff --check`, and the design/plan trailing-whitespace scan passed. This evidence verifies the D1 worktree only, not parser behavior or D1 completion. Read-only Beads status: `parser-0pc` remains blocked; no Beads/GitHub mutation. No parser source/tests, commit, push, or PR changed in this update. Primary checkout remains preserved. Design SHA-256 at that checkpoint: `218910671cc928215a3a29002060f6db0bdc9e13f1f0168d4dde93bf679c4d19`.

## Continuation checkpoint — 2026-09-29

After the latest maintainer choices, `HEAD` remains `cf11de2fa7573b10d2555391676da3c3fbbe9f30`; the managed worktree is intentionally dirty, and `src/` has no changes. The selected contract direction is cross-platform text plus one explicit `.org` file path, required non-empty caller-supplied `page_title`, and no source-path field in `OrgDocument` or the public result. D1 remains open on the reader boundary. A maintainer choice is pending on whether the API accepts one explicit OS path or requires a trusted `vault_root` plus relative path; this choice does not authorize implementation. The Windows mechanism/object predicate, raw grammar, root bootstrap/locality, and residual guarantees must then be frozen in D1. The primary checkout remains untouched.

The latest canonical design SHA-256 is `ca3da6ce647399e1f7c3aebdf0e9857a931abc632d81c9217ae9099253f6895d`; corpus manifest SHA-256 remains `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`. The read-only Beads task `parser-0pc` is still `BLOCKED` on this reader contract; its current description matches the selected title and result shape. A fresh sandbox read was denied on the Beads lock, then the exact read-only task inspection succeeded after narrow escalation. No Beads or GitHub mutation occurred.

The complete `make all` result at this exact source/test tree remains 904 tests passed, 91.15% coverage, Ruff and Mypy passed; no source or test files changed after that run. `make docs-check` with an isolated UV environment stopped before its checker because DNS could not fetch `charset-normalizer==3.4.7`; the direct maintained-document checker, `make vendor-name-check`, and `git diff --check` passed before this checkpoint entry. These are D1 evidence only and do not qualify a parser. Re-run final documentation and full quality gates after D1 is frozen. No parser implementation, commit, push, PR, merge, release, or GitHub issue mutation occurred.
## Continuation checkpoint — 2026-09-29 — corpus contract correction

Live managed-worktree anchor remains `cf11de2fa7573b10d2555391676da3c3fbbe9f30`; it is detached and intentionally dirty. The primary checkout remains dirty/divergent and untouched. `src/` remains unchanged. The design hash after the latest D1 clarification is `ab59142c76b89620b828e1d41c7e25af468cb008c7f01caafd4eb712765d2873`; manifest hash remains `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`. Rehash the plan after this entry.

The independent Luna D1 audit found a concrete contradiction: the selected owner rule requires a non-empty caller `page_title` for text and file inputs, while the test-only manifest validator forbade it for file mode and returned `None`. The file-mode corpus repair is complete: `OrgFixtureCase.page_title` is non-optional; both entrypoints require the explicit non-empty title; semantic projections must match that title. A red test first showed missing file titles were accepted. A second test, after schema acceptance was corrected, showed a mismatching file-mode semantic title was accepted; the unconditional match check fixed it. The full focused corpus suite now passes: 79 tests. No parser source or public API was added.

The same audit supports the six project-authored, Apache-2.0-declared fixtures and finite source-only semantic contract, with no claim of full GNU Org or OG parser parity. The test-only loader's lstat/read race remains acceptable only for a stable, trusted checkout; it is not a production reader. Diagnostic schema and security fixtures specify expected behavior but do not qualify a production parser. Resource ceilings are documented; node, depth, tag, and scanner-work accounting still need concrete D2 implementation/review and are not proven by corpus tests.

The file-input boundary is still owner-gated. A fresh independent Luna challenge recommends an absolute caller-selected path because approved scope names one explicit `.org` file but does not promise vault containment; the earlier root-relative recommendation is withdrawn. The replacement owner-choice question is pending. If selected, absolute paths still need strict raw grammar and component-by-component no-follow acquisition. Provider/network side effects and Windows object/type policy remain separate unresolved decisions; do not imply a narrower platform result or claim physical locality. `parser-0pc` remains read-only `BLOCKED` on this contract. `bd prime` could not read the embedded-dolt lock in the sandbox; one narrowly escalated `bd show parser-0pc --readonly --sandbox --json` confirmed current task text. No Beads/GitHub write, sync, commit, push, PR, merge, or release occurred.

This checkpoint's focused test, documentation, vendor, and diff gates must be rerun after the final spec/plan edits. The earlier `make all` result is stale for the current test tree. D1 and implementation gates remain open.

## Continuation checkpoint — 2026-09-29 — result-provenance decision and full verification

The maintainer reaffirmed that `OrgDocument` and the parse result must omit the source path. This resolves result provenance only; it does not choose the path accepted by `parse_org_file`. The outstanding path-shape choice remains absolute caller-selected path (recommended by the latest Luna challenge) versus a caller-supplied trusted root plus relative path. No vault-containment promise is currently approved. Windows acquisition, root/bootstrap/locality, raw path grammar, object predicate, provider/network effects, and residual guarantees remain D1 gates. No parser implementation has begun.

At `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`, after the corpus title-contract repair, isolated `make all` passed on Python 3.12.13: Ruff PASS; Mypy across 89 files PASS; vendor-name check PASS; documentation checker PASS; 906 tests PASS in 48.60 seconds; total coverage 91.15% (above the 80% floor); exit 0. Hypothesis used its in-memory database fallback. UV environment, caches, and coverage output were kept under `isolated temporary storage`. This verifies the current D1 evidence/test tree, not D1 completion or production parser behavior. After this checkpoint edit, `make docs-check`, `make vendor-name-check`, and `git diff --check` passed; the design/plan/corpus trailing-whitespace scan found no matches.

The focused `tests/test_org_assurance.py` suite passed 79 tests after the TDD repair: file-mode cases now require a non-empty manifest `page_title`, and semantic expectations must match it. The corpus remains test-only; no production source or public API changed. Live SHA-256 before this checkpoint edit: design `ab59142c76b89620b828e1d41c7e25af468cb008c7f01caafd4eb712765d2873`, manifest `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`; rehash the plan after edits.

Read-only Beads still identifies `parser-0pc` as `BLOCKED` on the reader contract. No Beads/GitHub writes or sync, commit, push, PR, merge, or release occurred. The managed worktree is intentionally dirty and `src/` remains unchanged; the primary checkout remains untouched.

## Continuation checkpoint — 2026-09-29 — official reader-capability refresh

Live anchors reverified: managed worktree `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`; primary checkout remains dirty/divergent and untouched; `src/` remains unchanged. The result-shape decision is settled (no source path in `OrgDocument`/result), while absolute caller path versus trusted root plus relative path remains an owner decision.

Fresh official documentation review adds two concrete capability facts. Python 3.12 says `os.supports_dir_fd` is Unix-only (not Windows) and exposes `O_NOFOLLOW_ANY` only on macOS. Linux man-pages 6.19 says `openat2` path-wide `RESOLVE_NO_SYMLINKS` requires Linux 5.6+, and `OPENAT2_REGULAR` can fail with `EFTYPE` for non-regular targets starting in Linux 7.2. Thus Linux <7.2 needs an explicit decision: fail closed for file input, or admit component-open plus same-handle `fstat(S_ISREG)` with the weaker special-file open-side-effect residual. Never silently retry without `OPENAT2_REGULAR`. Microsoft documents Windows handle-relative `NtCreateFile` and no-reparse primitives, but not the exact `ctypes` flag composition or a universal regular-file predicate; the NTFS candidate still needs owner selection and real Windows qualification. No reviewed API proves universal physical locality, no provider effects, immutable snapshots, or hard I/O deadlines.

Live Beads verification for the Parser common-directory tracker: read-only sandbox `prime` cannot acquire the embedded-dolt lock; the narrowly escalated read-only `show parser-0pc --json` succeeds. It confirms status `BLOCKED`, priority 1, and the same file-reader acceptance contract; revision `8043262218790456125`. No tracker or GitHub write/sync occurred.

The full local suite remains the current evidence: 906 passed, 91.15% coverage, Ruff/Mypy/vendor/docs PASS. After the latest design and plan edits, `make docs-check`, `make vendor-name-check`, and `git diff --check` passed; the design/plan/corpus trailing-whitespace scan found no matches. No parser code, commit, push, PR, merge, or release occurred. Design SHA-256 before this final evidence sentence was `2d61d333c17506aff9609bb367673358f9e28d45660bde796da1915eb7fe7ff1`; rehash after final D1 edits.

## Continuation checkpoint — 2026-09-29 — Linux pre-7.2 reader candidate and provenance reaffirmation

The maintainer reaffirmed that the Org result must omit source-path provenance. This is an output-shape decision only; it does not choose the input path shape. D1 still requires a decision between one absolute caller-selected path and a trusted root plus relative path; the latter adds a vault-containment contract.

Luna independently checked the Linux <7.2 `O_PATH` candidate against official man-pages. Documented facts: `O_PATH` obtains a filesystem-object reference without opening the file itself and supports `fstat`; `openat2(RESOLVE_NO_SYMLINKS)` blocks ordinary and magic-link traversal in the caller path; `/proc/self/fd/N` deliberately refers to a held descriptor through a magic link. Inference: acquire an `O_PATH` handle without following links, reject unless same-handle metadata says regular, reopen only an internally constructed self-procfd path while the original descriptor remains live, verify the readable handle identifies the same object, then perform the bounded read. The procfd reopen must intentionally permit that one magic link and must never use caller-controlled text. Do not request the `O_PATH|O_NOFOLLOW` final-symlink special case. Fail closed without usable procfs or on identity mismatch. This is a candidate, not an accepted or qualified contract; it still allows lookup/provider effects, normal data-open/read effects, concurrent writes, and unbounded I/O. Official references: [`open(2)`](https://man7.org/linux/man-pages/man2/open.2.html), [`openat2(2)`](https://www.man7.org/linux/man-pages/man2/openat2.2.html), [`proc_pid_fd(5)`](https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html), [`symlink(7)`](https://man7.org/linux/man-pages/man7/symlink.7.html).

Current Beads evidence was refreshed read-only against the Parser common-directory tracker: `parser-0pc` remains `blocked`, priority 1, revision `8043262218790456125`. Its acceptance criteria still block on the exact file-reader contract. The sandbox could not open its embedded-Dolt lock; one narrow read-only `--readonly --sandbox show` query completed with elevated filesystem access. No Beads write, sync, or GitHub access occurred.

At this checkpoint the managed worktree remains detached at `cf11de2fa7573b10d2555391676da3c3fbbe9f30`, intentionally dirty; `src/` remains unchanged, and the primary checkout remains untouched. Latest full-suite evidence at the same source/test tree is `make all` PASS: Ruff, Mypy (89 files), vendor/docs checks, 906 tests, 91.15% coverage, Python 3.12.13. The 79-test focused Org suite also passed. Re-run documentation checks after this checkpoint update. No parser implementation, commit, push, PR, merge, release, or GitHub issue mutation occurred.

## Continuation checkpoint — 2026-09-29 — current evidence and verification

The maintainer reaffirmed that source path stays out of `OrgDocument` and the public result. The input boundary remains distinct and unresolved: one absolute caller-selected path versus a trusted root plus relative path. No parser code was added.

Fresh official Linux man-page review and Luna's independent challenge qualify `O_PATH` plus controlled `/proc/self/fd/N` reopen as a pre-7.2 *candidate only*. It can pin an object without opening file data, reject a non-regular object with `fstat`, and reopen only the still-held descriptor after private same-object checks. It requires usable procfs, a narrowly scoped deliberate magic-link exception, private descriptor lifetime, and fail-closed identity checks. It does not establish a selected contract or remove provider effects, ordinary data-open/read effects, concurrent-write risk, or unbounded I/O. `OPENAT2_REGULAR` on Linux 7.2+ remains a separate capability. Windows and macOS leaf predicates and the path/root policy remain unresolved.

Read-only Beads was rechecked against the Parser common-directory tracker. `bd prime` could not open the embedded-Dolt lock under the sandbox; a single narrowly escalated `bd --readonly --sandbox show parser-0pc --json` succeeded. `parser-0pc` remains `blocked`, priority 1, revision `8043262218790456125`; acceptance still requires the exact cross-platform reader contract. No Beads write, sync, or GitHub call occurred.

At `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`, post-update `make all` passed: Ruff, Mypy across 89 files, vendor-name check, documentation checker, 906 tests, and 91.15% coverage on Python 3.12.13. A first run in a fresh isolated environment stopped before Ruff because DNS could not fetch a locked dependency; this was environmental, not a lint/test finding. Re-running the same Make target with the already populated locked environment and its isolated caches passed. `git diff --check` passed, the trailing-whitespace scan found no matches, and `git diff --exit-code -- src` confirmed no parser source changes. Worktree stayed detached and intentionally dirty; primary checkout remained untouched. Design SHA-256 at this checkpoint: `b594c2498cc01b2be96db3216ba80f39a688c3734772b6808f05f150cc1a43fa`; manifest SHA-256: `36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`. The next restart/continuation must reverify the plan hash live; no self-hash is embedded.

## Continuation checkpoint — 2026-09-29 — macOS and architecture review

Owner clarification: keep the source path out of `OrgDocument` and the public
parse result. This does not select the input path shape. Live source anchor
remains detached `HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`; the design,
plan, fixtures, assurance validator/tests, and navigation edits remain
intentionally uncommitted in the managed worktree. Primary checkout is
untouched, and `src/` remains unchanged.

Luna's read-only official-source review found that XNU `O_NOFOLLOW_ANY`
documents rejection of symlinks in every component, while `getattrlistat`
with `FSOPT_NOFOLLOW_ANY` plus `ATTR_CMN_OBJTYPE` is only a precheck and races
with a later open. The reviewed XNU header contains no `O_PATH` equivalent;
`O_EVTONLY` is for event monitoring, and `O_SYMLINK` opens a final link.
Potential macOS sequence: no-follow open, retain descriptor, `fstat` and reject
unless regular before reading, then bounded reads through that descriptor.
This cannot promise that a special object is never opened. No minimum macOS
version for the flag was established. Required future qualification includes
parent/final/broken symlinks, regular/directories/FIFOs/available special
objects, replacement races, target filesystems/providers, descriptor cleanup,
and oldest/current supported macOS. Primary sources: [XNU `open(2)`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/open.2),
[XNU `getattrlist(2)`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/getattrlist.2),
[XNU `fcntl.h`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/fcntl.h).

Astra's read-only architecture memo is **BLOCKED for D1**, not a rejection of
the parser direction. It says a bounded cross-platform contract may be
possible only with explicit platform-specific mechanisms, support limits,
fail-closed behavior, and accepted residuals; no universal unconditional
file-reader guarantee is evidenced. For the approved one-file scope, Astra
recommends an absolute caller-selected path because no vault-containment
promise exists. This remains a recommendation, not a maintainer choice.
Remaining owner decisions are: (1) absolute input path or trusted root plus
relative path; (2) exact OS/version/filesystem/capability matrix; (3) each
platform's bootstrap, no-follow, and leaf-type predicate; (4) whether
non-regular-object open side effects must be prevented or only reads rejected
before bytes; (5) accepted provider/network, snapshot, deadline, hard-link,
and filesystem residuals; and (6) whether to admit and qualify platform-native
bindings. Root-relative input adds a containment contract; an absolute path
does not eliminate raw grammar, no-follow, authority, or type checks.

After these documentation-only updates, the maintained-docs checker, vendor-
name check, and `git diff --check` passed; the whitespace scan found no
trailing whitespace, and `git diff --exit-code -- src` confirmed no parser
source change. Design SHA-256 is
`32ba9afdc8e5d1aaad681e113aaee0134b0cbcb403d514a8dd1bd8db76f8d64f`; plan
SHA-256 is intentionally not embedded in its own contents and must be
recomputed from the live file when resuming;
corpus-manifest SHA-256 remains
`36b80143a2c0834762105fe003a2b5ca579043a61f265595b58a7ce0235653e0`.
The latest full-suite evidence remains 906 passed, 91.15% coverage, and all
quality gates green at the previously recorded exact source/test tree; no
full-suite rerun was needed for these documentation-only changes. This still
does not close D1. No parser implementation, Beads/GitHub mutation, commit,
push, PR, merge, or release occurred.

### Historical D1 decision packet — superseded

This earlier recommendation proposed the absolute-path, bounded three-platform
reader now selected above. Its proposal wording and unresolved-choice list are
retained only as historical context; the normative policy and accepted
residuals are in Task 5. The historical security note remains relevant: Windows
`ctypes`/`NtCreateFile` requires real-runner ABI/adversarial qualification and
separate Sol security review. This packet is not a current owner-choice gate.

### Live repository cross-check — 2026-09-29

The current CI workflow confirms its test matrix is `ubuntu-24.04`, `macos-15`,
and `windows-2025`, each with Python 3.12 and 3.13. These are concrete
qualification targets for the proposed experimental reader, not proof that
all OS versions or filesystems are supported. The existing
`local_graph_assurance._read_regular_file` path performs `lstat`, path
resolution and vault containment, then opens the resolved pathname with
`O_NOFOLLOW`, followed by descriptor identity checks and bounded reads. This
supports the existing trusted-vault workflow but does not anchor every path
component to a held directory descriptor at open time; it is not a drop-in
proof for the stricter Org contract. Verified against `src/logseq_matryca_parser/local_graph_assurance.py` at the live base. No source changes.

## Historical Sol XHigh read-only decision review — 2026-09-29

Sol reverified the live anchors (`HEAD cf11de2fa7573b10d2555391676da3c3fbbe9f30`,
design SHA-256 `32ba9afdc8e5d1aaad681e113aaee0134b0cbcb403d514a8dd1bd8db76f8d64f`,
plan SHA-256 `f254b3c746bfcfee2ad53424c5be75f26280e11c90220346b3b460483d173a55`)
and concluded **D1 remains BLOCKED**. The absolute-path direction is coherent
for this one-file scope, but neither that recommendation nor a yes to the
proposed packet is a complete normative reader contract. The owner still must
choose the input boundary and accept or reject the named residual/security
policy. In particular, Windows NTFS's checked non-directory/non-reparse
`FILE_TYPE_DISK` default-stream profile is an operational predicate, not a
universal regular-file guarantee; Windows parent-open flag composition and
root/locality evidence remain unqualified. Linux policy must name either
`OPENAT2_REGULAR` on 7.2+ plus the explicit pre-7.2 `O_PATH`/procfd candidate,
or fail-closed behavior; “strongest available” is too vague. macOS remains
`O_NOFOLLOW_ANY` plus same-descriptor `fstat` before bytes, with possible
pre-rejection open effects. Microsoft confirms `FILE_NON_DIRECTORY_FILE` may
include devices or volumes and documents `FILE_DIRECTORY_FILE` compatibility
without `FILE_OPEN_REPARSE_POINT`; Linux documents `OPENAT2_REGULAR` since
7.2 and the `O_PATH` behavior; Apple documents path-wide `O_NOFOLLOW_ANY`.
Primary sources: [Microsoft `NtCreateFile`](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile),
[Microsoft `GetFileType`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype),
[Linux `openat2(2)`](https://www.man7.org/linux/man-pages/man2/openat2.2.html),
[Linux `open(2)`](https://man7.org/linux/man-pages/man2/open.2.html),
[Apple XNU `open(2)`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/open.2).

The design was corrected after this review to replace the stale Linux
pre-7.2 ordinary-open-plus-`fstat` description with the two actual candidates,
and to describe the accepted file leaf as a platform-specific predicate rather
than asserting universal “regular file” status. Still required before D1 can
close: exact path grammar and bootstrap/root rules, platform capability and
filesystem matrix, per-OS leaf predicate and open-time residuals, fixed error
mapping, and explicit owner acceptance. Owner approval will only permit
freezing D1 and requesting final plan review; it does not authorize parser
implementation. No source or test code changed.
