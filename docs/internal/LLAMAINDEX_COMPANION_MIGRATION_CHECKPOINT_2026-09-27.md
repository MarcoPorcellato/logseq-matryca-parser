---
type: Document
---
# LlamaIndex companion migration checkpoint — 2026-09-27

## Resume anchors

- Parser worktree: `/Users/marco1/.codex/worktrees/nltk-llamaindex-decoupling/logseq-matryca-parser`
- Branch: `design/nltk-llamaindex-companion`
- Parser code anchor before this checkpoint: `1d11d97e1806b534a74a82585fc1aec54e56a4fa` (`chore: prepare parser 1.10.0 release`). This documentation checkpoint postdates that code anchor; run `git rev-parse HEAD` on resume to bind the current branch HEAD.
- Companion local clone: `/Users/marco1/Documents/CODICE con VS CODE/logseq-matryca-parser-llamaindex`
- Companion branch/HEAD at the draft PR opening: `feat/native-llamaindex-adapter` at `14fd8de399d5abd38c70e52125e81da8dda5c5b2`; `main` remains at bootstrap commit `47d954a713712b8a433970f9b0f23db070ee09b9`. Rebind both refs on resume.
- The companion clone was clean at the recorded draft-PR commit. Its `origin` points to `https://github.com/MarcoPorcellato/logseq-matryca-parser-llamaindex.git`. The staging source under `/private/tmp/logseq-llamaindex-companion.Cfq6w7` still exists; the durable clone remains the safest local resume source.
- Parser primary checkout is not the work surface; preserve its existing dirty/stale state.

## Completed local evidence

- Parser migration Tasks 1–4 are committed locally at the Parser anchor above. Sol integration review: `PASS_WITH_NOTES`; full local gate passed: `make all`, 825 tests, 91.13% coverage, docs, vendor-name, wheel/sdist contract, and unwaived dependency audit. Parser 1.10.0 wheel metadata and dependency evidence exclude both `llama-index-core` and `nltk`.
- Companion Tasks 5–6 are a local implementation checkpoint only. The package exports native LlamaIndex `TextNode` objects and keeps the Parser dependency graph separate. Candidate distribution name: `logseq-matryca-parser-llamaindex`; package version `0.1.0`; Python `>=3.12`; license `Apache-2.0`, copied exactly from Parser.
- Provisional companion requirements: `logseq-matryca-parser>=1.10.0,<1.11.0` and `llama-index-core>=0.14.22,<0.15`. Released Parser 1.9.0 still contains the old adapter; therefore the formerly suggested `>=1.9.0` lower bound was invalid. The 1.10.0 minimum is not yet registry-available, and neither endpoint has registry-install compatibility qualification.
- At companion HEAD `bcf7576caa99cf884280cffdb05238358b6be2f3`: offline wheel/sdist build passed, 8 tests passed, wheel metadata and packaged license were verified, full-tree Ruff passed on the clean clone. Sol review of local code: `PASS_WITH_NOTES`. Security review of local code: `PASS_WITH_NOTES`.
- A locally built Parser 1.10.0 wheel was installed with `--no-deps` into the isolated companion test environment for import-isolation coverage. This is local smoke evidence, not registry resolution or compatibility testing against released artifacts.
- This does **not** complete release qualification: no portable `uv.lock`, hosted Python 3.12/3.13 CI, production export audit, registry compatibility matrix, or installed-release acceptance exists yet. Those are deliberately pending until a real Parser 1.10.0 distribution can resolve.

## Security and publication boundary

- NLTK 3.10.3 remains in the current LlamaIndex dependency graph. GitHub advisory [GHSA-8mgp-746c-j5xp](https://github.com/advisories/GHSA-8mgp-746c-j5xp) reports affected versions `<=3.10.3` and no fixed release. The PyPA record [PYSEC-2026-3740](https://github.com/pypa/advisory-database/blob/main/vulns/nltk/PYSEC-2026-3740.yaml) has conflicting prose and machine-readable range. Treat the advisory as unresolved: no clean-audit claim, waiver, or release until authoritative records are reconciled and an accepted disposition exists. Security release gate: `BLOCKED`.
- After explicit authorization, `MarcoPorcellato/logseq-matryca-parser-llamaindex` was created as `PUBLIC`. The bootstrap `main` and feature branch were pushed, and [companion PR #1](https://github.com/MarcoPorcellato/logseq-matryca-parser-llamaindex/pull/1) was opened as a draft. [Parser PR #225](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/225) is also a draft. Neither PR has been merged; no package publication or release has occurred. Local reviews do not authorize those further actions.
- The GitHub repository name is now occupied by the authorized public repository. Earlier PyPI HTTP 404 was not a name reservation; recheck package availability before any publication decision.

## Next gates, in order

1. Rebind both local paths, branches, exact HEADs, and clean status before work.
2. Prequalify companion native-node and shim behavior against the exact candidate Parser 1.10.0 wheel; record both artifact hashes. This does not prove registry installation.
3. Decide Parser PR merge and 1.10.0 publication through separate explicit maintainer gates after its independent hosted, dependency, migration, and release checks pass.
4. After Parser 1.10.0 resolves from the registry, verify companion lower-bound installation and `<1.11.0` exclusion, generate a portable lock, add hosted Python 3.12/3.13 CI, run the exact production export audit, and repeat distribution/shim acceptance.
5. Reconcile the NLTK advisory from authoritative sources. Keep companion release blocked absent a fixed upstream release or a separately approved, narrowly scoped exception with compensating controls.
6. Both draft PRs exist. Review their exact hosted checks and complete the applicable qualification before each merge. Companion publication remains a separate authorization gate.

See the [implementation plan](../superpowers/plans/2026-09-27-llamaindex-companion-separation.md) for task ownership and detailed acceptance criteria.
