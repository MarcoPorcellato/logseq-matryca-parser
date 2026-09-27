---
type: Document
---
# LlamaIndex companion migration checkpoint — 2026-09-27

## Resume anchors

- Parser: PR #225 has since merged; exact remote `main` is `870a35eb8014c030aaa874e8f1ce550556e0decb` (verified 2026-09-27). Earlier code qualification anchor was `1d11d97e1806b534a74a82585fc1aec54e56a4fa`; candidate-wheel gate source HEAD was `95154fa32f6f13ebb1f9b6accc26ccace8ff2435`, clean at gate time. Version 1.10.0 remains release preparation only and is not yet published to PyPI.
- Companion: [draft PR #1](https://github.com/MarcoPorcellato/logseq-matryca-parser-llamaindex/pull/1), branch `feat/native-llamaindex-adapter`; tested head `14fd8de399d5abd38c70e52125e81da8dda5c5b2`. Its bootstrap `main` is `47d954a713712b8a433970f9b0f23db070ee09b9`.
- Both candidate-wheel source checkouts were clean at the gate HEADs above. Preserve any dirty primary checkout and rebind repository and branch state before further work. Local workspace paths are intentionally omitted from this public record.

## Completed local evidence

- Parser migration Tasks 1–4 are committed locally at the Parser anchor above. Sol integration review: `PASS_WITH_NOTES`; full local gate passed: `make all`, 825 tests, 91.13% coverage, docs, vendor-name, wheel/sdist contract, and unwaived dependency audit. Parser 1.10.0 wheel metadata and dependency evidence exclude both `llama-index-core` and `nltk`.
- Companion Tasks 5–6 are a local implementation checkpoint only. The package exports native LlamaIndex `TextNode` objects and keeps the Parser dependency graph separate. Candidate distribution name: `logseq-matryca-parser-llamaindex`; package version `0.1.0`; Python `>=3.12`; license `Apache-2.0`, copied exactly from Parser.
- Provisional companion requirements: `logseq-matryca-parser>=1.10.0,<1.11.0` and `llama-index-core>=0.14.22,<0.15`. Released Parser 1.9.0 still contains the old adapter; therefore the formerly suggested `>=1.9.0` lower bound was invalid. The 1.10.0 minimum is not yet registry-available, and neither endpoint has registry-install compatibility qualification.
- At companion HEAD `bcf7576caa99cf884280cffdb05238358b6be2f3`: offline wheel/sdist build passed, 8 tests passed, wheel metadata and packaged license were verified, full-tree Ruff passed on the clean clone. Sol review of local code: `PASS_WITH_NOTES`. Security review of local code: `PASS_WITH_NOTES`.
- Candidate-wheel prequalification passed on Python 3.12.13: exact local Parser wheel SHA-256 `4bc8f3b544a996d88ea38b1e00e19ac390f0dfe2e247a47598d6cbaf3a7a3e27` and companion wheel SHA-256 `9309ae5f1c2d123622f67745e8ac02188835fadac1501a894dd9164a6f878261` resolved with all runtime dependencies. All 71 installed distributions passed dependency consistency checks. Installed-only assertions passed for native `TextNode` types, ordering, relationships, source IDs, and the Parser shim. This is local candidate-wheel evidence, not a registry or release qualification.
- This does **not** complete release qualification: no portable `uv.lock`, hosted companion Python 3.12/3.13 CI, production export audit, or registry compatibility matrix exists yet. Those remain pending until a real Parser 1.10.0 distribution can resolve.

## Security and publication boundary

- NLTK 3.10.3 remains in the current LlamaIndex dependency graph. GitHub advisory [GHSA-8mgp-746c-j5xp](https://github.com/advisories/GHSA-8mgp-746c-j5xp) reports affected versions `<=3.10.3` and no fixed release. The PyPA record [PYSEC-2026-3740](https://github.com/pypa/advisory-database/blob/main/vulns/nltk/PYSEC-2026-3740.yaml) has conflicting prose and machine-readable range. Treat the advisory as unresolved: no clean-audit claim, waiver, or release until authoritative records are reconciled and an accepted disposition exists. Security release gate: `BLOCKED`.
- After explicit authorization, `MarcoPorcellato/logseq-matryca-parser-llamaindex` was created as `PUBLIC`. The bootstrap `main` and feature branch were pushed, and [companion PR #1](https://github.com/MarcoPorcellato/logseq-matryca-parser-llamaindex/pull/1) was opened as a draft. At checkpoint time, Parser PR #225 was also a draft; it has since merged at the exact `main` commit recorded above. Parser 1.10.0 publication remains a separate maintainer gate. The companion PR state must be rebound before further decisions. Local reviews do not authorize those further actions.
- The GitHub repository name is now occupied by the authorized public repository. Earlier PyPI HTTP 404 was not a name reservation; recheck package availability before any publication decision.

## Next gates, in order

1. Rebind both repository branches, exact HEADs, current companion PR state, and clean status before work.
2. Preserve candidate-wheel prequalification evidence at the hashes above. It does not prove registry installation or companion release readiness.
3. Decide Parser 1.10.0 publication through a separate explicit maintainer gate after its independent hosted, dependency, migration, and release checks pass.
4. After Parser 1.10.0 resolves from the registry, verify companion lower-bound installation and `<1.11.0` exclusion, generate a portable lock, add hosted Python 3.12/3.13 CI, run the exact production export audit, and repeat distribution/shim acceptance.
5. Reconcile the NLTK advisory from authoritative sources. Keep companion release blocked absent a fixed upstream release or a separately approved, narrowly scoped exception with compensating controls.
6. Review the companion draft PR's exact hosted checks and complete its applicable qualification before any merge. Companion publication remains a separate authorization gate.

See the [implementation plan](../superpowers/plans/2026-09-27-llamaindex-companion-separation.md) for task ownership and detailed acceptance criteria.
