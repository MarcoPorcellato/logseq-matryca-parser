---
type: Document
---
# CodeQL code scanning

**Logseq Matryca Parser** (v1.6.0+) uses **GitHub CodeQL default setup** for static analysis (SAST) on Python.

## Why there is no `codeql.yml` workflow

GitHub does not allow **default setup** and a custom **advanced** CodeQL workflow at the same time. Uploading SARIF from `.github/workflows/codeql.yml` fails with:

> CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled

Default setup is the recommended path for this repository: GitHub maintains the analysis configuration, runs on current runner images (Node 24+), and scans Python without duplicating CI.

CodeQL is settings-managed assurance. Its source documentation records the
intended configuration, but only a current authenticated Settings/API readback
and an exact-head hosted result establish current status. See the
[continuous integration assurance map](CI_ASSURANCE.md) for the distinction
between local, hosted, settings, and publication evidence.

## Where to see results

- **Security → Code scanning** on the repository
- [CodeQL status page](https://github.com/MarcoPorcellato/logseq-matryca-parser/security/code-scanning/tools/CodeQL/status/) for coverage and run history

The repository also defines a separate scheduled OpenSSF Scorecard workflow.
It uploads third-party SARIF findings to the same code-scanning interface; it
does not replace CodeQL default setup or introduce a custom CodeQL analysis.
Treat the workflow file as the intended configuration and the hosted run as the
only current result.

## Switching to an advanced workflow (optional)

Only if you need a custom `codeql.yml` (extra queries, manual build steps, etc.):

1. **Settings → Advanced Security → Code scanning**
2. Next to **CodeQL analysis**, open the menu and choose **Disable CodeQL** (disables default setup)
3. Add or restore `.github/workflows/codeql.yml` using [github/codeql-action](https://github.com/github/codeql-action) **v4** or newer

Do not re-enable default setup while an advanced workflow is active.

## Related

- [`SECURITY.md`](../SECURITY.md) — vulnerability reporting
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — local quality gates (`make all`)
- [`CI_ASSURANCE.md`](CI_ASSURANCE.md) — complete CI map and evidence boundaries
- [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) — starter tasks for new contributors
- [`reference/DEPENDENCY_LICENSE_POLICY.md`](reference/DEPENDENCY_LICENSE_POLICY.md) — SBOM, dependency/license, and release provenance contract
- [Troubleshooting: default setup enabled](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/troubleshoot-sarif-uploads/default-setup-enabled)
