# Task 1 report — filesystem traversal and declared limits

## Status

DONE

## Files changed and commit

- `tests/test_local_graph_assurance.py`: added seven focused tests covering the
  requested traversal failures, filtering, root validation, and byte limits.
- `.superpowers/sdd/2026-08-24-local-assurance-coverage/task-1-report.md`:
  this report.
- Commit SHA: `0b56c28`.

No production file was changed because the tests demonstrated no contract
defect.

## Tests added and mutations caught

- `test_assurance_reports_only_directory_read_error`: catches treating an
  `iterdir()` failure as a successful or mixed report, or leaking a second
  finding/count.
- `test_assurance_reports_only_entry_stat_error`: catches ignoring an
  `lstat()` failure or continuing traversal with an incomplete entry record.
- `test_assurance_ignores_excluded_directories_and_non_markdown_entries`:
  catches counting entries below `.git`, `.recycle`, or `logseq`, or counting
  non-regular/non-Markdown entries.
- `test_assurance_rejects_non_directory_roots`: catches accepting a regular
  file at either declared `pages` or `journals` root.
- `test_assurance_enforces_max_file_bytes_during_traversal`: catches omitting
  the per-file size guard or returning the wrong limit finding.
- `test_assurance_enforces_max_total_bytes_during_traversal`: catches
  accumulating traversal bytes without enforcing the aggregate limit.
- Existing `test_assurance_rechecks_total_bytes_while_reading` remains the
  read-stage mutation check for aggregate bytes after enumeration.

## Commands and results

- `rtk uv run ruff check tests/test_local_graph_assurance.py` — passed.
- `rtk uv run pytest -q tests/test_local_graph_assurance.py` — 28 passed.
- `rtk uv run pytest -q tests/test_local_graph_assurance.py --cov --cov-report=term-missing --cov-fail-under=0` — 28 passed; assurance module coverage reported 301 statements, 126 misses, 58%.
- `rtk git diff --check` — passed.

The configured assurance baseline in the task brief was 301 statements, 134
misses, 55%. The result is 8 fewer misses and 3 percentage points higher
coverage: 301 statements, 126 misses, 58%.

An initial probe using an explicit filesystem path as the coverage target
collected no data; it was not used for the reported result. A direct explicit
module target also triggered an environment-specific multiprocessing pickling
failure under the coverage plugin. The configured `--cov` command above ran
the complete focused suite successfully and is the authoritative coverage
receipt.

## Self-review and remaining concerns

- Reviewed the diff and confirmed only the permitted test file plus this
  report changed; no production behavior or coverage configuration changed.
- Tests assert status, finding codes, and aggregate observations. The two
  filesystem-error tests patch only the narrow OS boundaries that are not
  portable to exercise with `tmp_path` alone.
- No paths, titles, UUIDs, Markdown fragments, exception text, host names, or
  credentials are placed in reports or committed fixtures.
- Remaining concern: the explicit module-target coverage invocation is
  incompatible with this environment's multiprocessing/coverage interaction;
  the repository-configured coverage invocation is green and records the
  requested module result.
