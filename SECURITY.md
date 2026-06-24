# Security Policy

## Supported Versions

Security fixes are provided **only for the latest released version** on [PyPI](https://pypi.org/project/logseq-matryca-parser/).

| Version | Supported |
| ------- | --------- |
| **1.4.1** (latest) | Yes |
| 1.4.0 and older | No |

We recommend always running the current release and upgrading promptly when a security advisory is published.

## Reporting a Vulnerability

**Please do not open a public GitHub issue** for security vulnerabilities. Public disclosure can put users at risk before a fix is available.

### Preferred channels

1. **GitHub Private Vulnerability Reporting** (recommended): open the [Security tab](https://github.com/MarcoPorcellato/logseq-matryca-parser/security) on this repository and use **Report a vulnerability**. This keeps the report private and lets us coordinate a fix and advisory through GitHub.
2. **Email**: send details to [marco@marcoporcellato.it](mailto:marco@marcoporcellato.it) if you cannot use GitHub's private reporting.

### What to include

- A clear description of the vulnerability and its impact
- Steps to reproduce (minimal input files, CLI commands, or code snippets)
- Affected version(s) and any known mitigations
- Your contact information for follow-up (optional but helpful)

### What to expect

| Timeline | Action |
| -------- | ------ |
| **Within 48 hours** | Acknowledgement of your report |
| **Within 7 days** | Initial assessment and severity classification |
| **Ongoing** | Status updates until the issue is resolved or declined with explanation |

When a fix is ready, we will:

1. Release a patched version on PyPI
2. Publish a [GitHub Security Advisory](https://github.com/MarcoPorcellato/logseq-matryca-parser/security/advisories) with credit to the reporter (unless you prefer to remain anonymous)
3. Document the fix in [`CHANGELOG.md`](CHANGELOG.md) under a `Security` section

## Scope

This policy covers the **logseq-matryca-parser** Python package, CLI (`matryca-parse`), and documented public APIs in `src/logseq_matryca_parser/`. Third-party dependencies are out of scope unless the vulnerability is exploitable through this project's intended use.

Report security issues via the [Security tab](https://github.com/MarcoPorcellato/logseq-matryca-parser/security) — not via public issues. For general bugs and features, see [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/GOOD_FIRST_ISSUES.md`](docs/GOOD_FIRST_ISSUES.md).

## Recognition

We appreciate responsible disclosure. Reporters who follow this policy will be credited in the security advisory when the fix is published, unless they request otherwise.
