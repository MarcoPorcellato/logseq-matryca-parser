---
type: Document
---
# LlamaIndex companion migration checkpoint — 2026-09-27

## Resume anchors

- Parser worktree: `/Users/marco1/.codex/worktrees/nltk-llamaindex-decoupling/logseq-matryca-parser`
- Branch: `design/nltk-llamaindex-companion`
- Parser code anchor before this checkpoint: `1d11d97e1806b534a74a82585fc1aec54e56a4fa` (`chore: prepare parser 1.10.0 release`). This documentation checkpoint postdates that code anchor; run `git rev-parse HEAD` on resume to bind the current branch HEAD.
- Companion local clone: `/Users/marco1/Documents/CODICE con VS CODE/logseq-matryca-parser-llamaindex`
- Companion branch/HEAD: `feat/native-llamaindex-adapter` at `bcf7576caa99cf884280cffdb05238358b6be2f3`; local `main` remains at bootstrap commit `47d954a713712b8a433970f9b0f23db070ee09b9`.
- Companion clone is clean and has **no remote configured**. The staging source under `/private/tmp/logseq-llamaindex-companion.Cfq6w7` still exists. The durable clone is the safest local resume source; add a GitHub remote only after separate explicit authorization to create that exact public repository.
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
- Automatic review rejected creating `MarcoPorcellato/logseq-matryca-parser-llamaindex` as public pending explicit authorization for the exact name and visibility. Do not retry through another route. No GitHub repository, push, PR, package publication, or release has occurred. Sol and security local-code reviews do not authorize these actions.
- Public name lookup results from the earlier authenticated check were not a reservation. Recheck GitHub/PyPI availability only after authority to create/publish is resolved.

## Next gates, in order

1. Rebind both local paths, branches, exact HEADs, and clean status before work.
2. Publish Parser 1.10.0 only through its separate reviewed release process; then install actual registry artifacts at the declared companion lower bound and verify the `<1.11.0` exclusion with packaging tests.
3. After the dependency resolves, generate and review a portable lock, add hosted Python 3.12/3.13 CI, run the exact production export audit, and repeat distribution/shim acceptance.
4. Reconcile the NLTK advisory from authoritative sources. Keep companion release blocked absent a fixed upstream release or a separately approved, narrowly scoped exception with compensating controls.
5. Obtain explicit authorization before creating the exact public GitHub repository. Push, PR, and either package publication remain separate authorization gates.

See the [implementation plan](../superpowers/plans/2026-09-27-llamaindex-companion-separation.md) for task ownership and detailed acceptance criteria.
