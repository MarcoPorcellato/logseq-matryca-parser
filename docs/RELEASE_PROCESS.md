# Release process

**Logseq Matryca Parser** (The Logos Protocol · Marco Porcellato · [Matryca.ai](https://matryca.ai)) uses a **curated** [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog). Pushing a `v*` git tag triggers **two** workflows:

| Workflow | Result |
|----------|--------|
| [`.github/workflows/pypi_publish.yml`](../.github/workflows/pypi_publish.yml) | Builds and publishes the package to **PyPI** (OIDC). |
| [`.github/workflows/github_release.yml`](../.github/workflows/github_release.yml) | Creates a **GitHub Release** with notes extracted from `CHANGELOG.md`. |

---

## During development

Add user-facing bullets under **`## [Unreleased]`** (`Added` / `Changed` / `Fixed` / `Removed` / `Security`). One line per notable change. See [`.cursor/rules/05-auto-changelog.mdc`](../.cursor/rules/05-auto-changelog.mdc).

---

## Release day (local)

Replace `X.Y.Z` with the semver you are shipping (no `v` prefix in `pyproject.toml`; use `vX.Y.Z` for the git tag).

### 1. Prepare (Cursor or manual)

- [ ] Move everything from `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`
- [ ] Leave an empty `## [Unreleased]` section at the top
- [ ] Set `version = "X.Y.Z"` in `pyproject.toml` and `__version__` in `src/logseq_matryca_parser/__init__.py`
- [ ] Run `make all` (ruff, mypy, pytest)

**Cursor shortcut:** ask the agent to *“prepare release vX.Y.Z”* (see [`.cursor/rules/04-release-preparation.mdc`](../.cursor/rules/04-release-preparation.mdc)).

### 2. Verify release notes (optional but recommended)

```bash
python scripts/extract_changelog.py vX.Y.Z | less
```

You should see exactly the section that will appear on GitHub if you attach release notes manually.

### 3. Commit, tag, push

```bash
git add CHANGELOG.md pyproject.toml src/logseq_matryca_parser/__init__.py README.md CONTRIBUTING.md SECURITY.md docs/
git commit -m "chore: release X.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

### 4. CI does the rest

On tag push:

1. **PyPI** — builds sdist/wheel and publishes (trusted publishing).
2. **GitHub Release** — publishes release notes from `scripts/extract_changelog.py`.

Verify both under **Actions** on GitHub (`Publish to PyPI` and `GitHub Release`).

#### Retroactive release (tag already pushed)

If the tag exists but no GitHub Release was created (e.g. before `github_release.yml` existed):

1. Open **Actions → GitHub Release → Run workflow**
2. Enter the tag (e.g. `v1.1.1`) and run.

PyPI cannot be re-published for the same version; use a patch bump if the wheel upload failed.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Tag on GitHub but no **Release** page | Run **GitHub Release** workflow manually (`workflow_dispatch`) with that tag. |
| PyPI version already exists | Bump patch version; never re-use a published version. |
| Notes look wrong | Re-run locally: `python scripts/extract_changelog.py vX.Y.Z` and compare to `CHANGELOG.md`. |
| CI fails on tests | Run `make all` locally before tagging. |

---

## Related

- [`CHANGELOG.md`](../CHANGELOG.md)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — quality gates before tag
- [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) — contributor task index
- [`scripts/extract_changelog.py`](../scripts/extract_changelog.py)
