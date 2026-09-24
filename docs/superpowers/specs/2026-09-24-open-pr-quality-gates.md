# Open PR and Quality-Gate Repair Specification

## Purpose

Repair the stale issue-reconciliation evidence and make the repository policy
scanner fail closed while inspecting the complete Git working tree, including
hidden files. Then re-evaluate the four open pull requests against current
`main` and close only those whose exact heads pass all required checks and
review gates.

## Verified starting anchors

- Repository: `MarcoPorcellato/logseq-matryca-parser`.
- `main`: `ac91aca6a3d6bf3ad5f6f952ff4b8b366bdc9941` (`2026-09-23` metrics
  archive), independently confirmed through GitHub's commit search and local
  `origin/main`.
- Current open pull requests: #218, #219, #220, and #221.
- #218 head: `75b84d731e4b056a214e35aa63d4974b583ecceb`; hosted runs are waiting
  for maintainer approval (`action_required`).
- #219 head: `63207c96e7f19b12c8a6cfa204d69f774753b41e`; required Quality job
  fails at documentation validation. Other tests, packaging, and production
  audit passed on that older base.
- #220 head: `a6fa0a30a58b88057cd1363a396395d542b454bd`; Quality fails at
  documentation validation and production dependency audit fails.
- #221 head: `18174d2c37d28b809f4f83cd7fcabeea93d18406`; Quality fails at
  documentation validation and production dependency audit fails.
- Live issue search returns 33 open issues; the current maintained
  reconciliation still records an August 8 verification and expired
  `stale_after: 2026-09-07`.
- CI output reports `rg: command not found` followed by
  `vendor-name-check: OK`; this is a false-green policy check.

## Requirements

1. Create a dated, maintained issue snapshot that lists exactly the 33 issues
   returned by the live open-issue search, gives each a concise current
   disposition/next action, records the four related PR states, and separates
   confirmed facts from decisions still pending.
2. Preserve the August reconciliation as historical evidence. Update the
   quality index, documentation index, documentation system, and maintained
   profile so the dated snapshot is clearly the current ledger and the old
   ledger is clearly historical.
3. Replace the vendor checker with a standard-library Python implementation
   that scans Git-tracked and non-ignored untracked files, includes hidden
   paths, skips binary blobs, skips only explicitly exempt files, and returns
   nonzero when Git cannot enumerate repository files.
4. Preserve the current encoded forbidden-pattern boundary; do not write any
   prohibited third-party product name in repository files, test fixtures, or
   output.
5. Add tests proving hidden-path detection, exempt-file behavior, and
   fail-closed enumeration errors.
6. Run focused tests, documentation checks, vendor-name check, and full
   `make all` on the exact final commit candidate. Do not claim a check passed
   without its fresh output.
7. Ask Sol for a read-only review after implementation and local verification.
8. Rebase/update each candidate PR only after the repair lands or its exact
   diff is otherwise based on current `main`. Merge no PR unless its exact
   head is current, all required checks are green, unresolved review threads
   are absent, dependency/security review is favorable, and mergeability is
   confirmed immediately before merge.

## Boundaries

- Preserve the primary checkout and its local restart-handoff commit.
- Do not change parser/runtime behavior, dependency declarations, releases, or
  unrelated issues.
- A review verdict does not authorize a merge. The user's request to execute
  this plan authorizes only the scoped repair and controlled closure of the
  four PRs when every stated merge gate passes.
- Do not use `gh` for writes while its stored token is invalid. Use verified
  SSH Git transport or an available GitHub connector after confirming the
  exact target branch and commit.
- If permissions, CI approval, review requirements, or checks remain blocked,
  preserve the work and report the exact remaining gate instead of bypassing it.

## Exit criteria

- [ ] Current reconciliation contains all 33 live open issues and accurate PR
  states; old snapshot is explicitly historical.
- [ ] Scanner tests prove hidden-file coverage and fail-closed behavior.
- [ ] Focused and full local quality gates pass on the final candidate.
- [ ] Sol review is `PASS` or `PASS_WITH_NOTES` with no unresolved blocking
  finding.
- [ ] Each PR is either merged after all gates pass or retained open with a
  precise reason and maintainer next action.
