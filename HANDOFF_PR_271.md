# PR #271 handoff: Windows CI qualification

This checkpoint is for the next maintainer or agent. It is not a release note, a security advisory, or permission to change GitHub state. The handoff branch is for reference only; continue the engineering work from the live pull request, not from this documentation commit.

## Start here

- [Draft PR #271](https://github.com/MarcoPorcellato/logseq-matryca-parser/pull/271), source branch `fix/agent-state-inplace-security-local`, target `main`.
- Last verified PR head: [`776debbe158b180da12974d32a104509f1a5c73d`](https://github.com/MarcoPorcellato/logseq-matryca-parser/commit/776debbe158b180da12974d32a104509f1a5c73d).
- The [recorded Logos CI run](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/40793761745) tested merge commit `d74415a9ac5e5896ab49882e2e4fd15adf080e35`, with base `325c74d4edb7ac47a6e7ba2c0893dc5b488d3678` and the head above. Live `main` has advanced since that run. Refresh the PR head, base, and checks before proposing changes.
- The existing candidate hardens agent file writes, preserves in-place state updates and weekly append behavior, and does not change the parser, graph, or dependencies.

## What CI proved and what it did not

On the recorded head, 13 of 15 checks passed and two failed. Both macOS cells and both Ubuntu cells passed, as did the hosted package contract. The two Windows 2025 cells ([Python 3.12](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/40793761745/job/123185072620), [Python 3.13](https://github.com/MarcoPorcellato/logseq-matryca-parser/actions/runs/40793761745/job/123185072630)) failed the same four test cases each:

1. `tests/test_agent_file_metadata.py::test_new_file_inherits_distinctive_windows_dacl` (`False` and `True`): baseline `Get-Acl` fails with `CouldNotAutoloadMatchingModule` before the write helper runs. Native inheritance is not yet qualified. The cause of the PowerShell import failure is not established.
2. `tests/test_alias_state_security.py::test_changed_leaf_is_rejected_before_mutation_even_without_no_follow_flag` (`regular-True` and `symlink-True`): the expected backup is absent. The expected-`OSError` block can catch a fixture error before the helper's refusal is proven. The failing stage and underlying Windows error are not yet established.

Neither result establishes a production defect or demonstrates that the failing scenario works. Passing related cases do not clear these blockers.

## Recommended next step

1. Inspect the two linked jobs and test functions. Confirm that the current failure evidence still applies. Start with a test-only diagnostic plan; get maintainer approval before running new hosted diagnostics or publishing a correction.
2. For the DACL tests, collect bounded, sanitized PowerShell executable identity, edition/version, and the explicit `Microsoft.PowerShell.Security` import error. Keep the inheritance oracle and baseline assertions. Do not switch shells solely on the basis of the autoload symptom.
3. For the replacement tests, separate fixture open, rename, and replacement failures from the expected helper refusal. Preserve the original exception type, `errno`, and `winerror` without host paths. Close any descriptor the fixture opened if its injected swap fails before ownership passes to the helper. Keep the content and no-mutation assertions.
4. Use that evidence to propose the smallest correction. No blanket skips, weaker assertions, or production redesign. Validate both Windows cells and the other required checks against the exact corrected head and tested base, with independent review. Review documentation, changelog, and contract implications before proposing merge.

Keep #271 draft until the maintainer decides otherwise. Do not merge, tag, release, or publish an advisory based on this checkpoint. Do not add raw logs, local configuration, local paths, caches, or private evidence to the repository. Nuitka, ccache, and local editor configuration are outside this handoff.
