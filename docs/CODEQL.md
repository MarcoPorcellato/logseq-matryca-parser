# CodeQL code scanning

**Logseq Matryca Parser** (v1.2.2+) uses **GitHub CodeQL default setup** for static analysis (SAST) on Python.

## Why there is no `codeql.yml` workflow

GitHub does not allow **default setup** and a custom **advanced** CodeQL workflow at the same time. Uploading SARIF from `.github/workflows/codeql.yml` fails with:

> CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled

Default setup is the recommended path for this repository: GitHub maintains the analysis configuration, runs on current runner images (Node 24+), and scans Python without duplicating CI.

## Where to see results

- **Security → Code scanning** on the repository
- [CodeQL status page](https://github.com/MarcoPorcellato/logseq-matryca-parser/security/code-scanning/tools/CodeQL/status/) for coverage and run history

## Switching to an advanced workflow (optional)

Only if you need a custom `codeql.yml` (extra queries, manual build steps, etc.):

1. **Settings → Advanced Security → Code scanning**
2. Next to **CodeQL analysis**, open the menu and choose **Disable CodeQL** (disables default setup)
3. Add or restore `.github/workflows/codeql.yml` using [github/codeql-action](https://github.com/github/codeql-action) **v4** or newer

Do not re-enable default setup while an advanced workflow is active.

## Related

- [`SECURITY.md`](../SECURITY.md) — vulnerability reporting
- [Troubleshooting: default setup enabled](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/troubleshoot-sarif-uploads/default-setup-enabled)
