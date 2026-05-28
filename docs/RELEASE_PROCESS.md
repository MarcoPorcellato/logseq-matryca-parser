# Release process

**Logseq Matryca Parser** (The Logos Protocol · Marco Porcellato · [Matryca.ai](https://matryca.ai)) uses a **curated** [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog). PyPI publishing is triggered when you push a `v*` git tag.

---

## During development

Add user-facing bullets under **`## [Unreleased]`** (`Added` / `Changed` / `Fixed` / `Removed` / `Security`). One line per notable change. See [`.cursor/rules/05-auto-changelog.mdc`](../.cursor/rules/05-auto-changelog.mdc).

---

## Release day (local)

Replace `X.Y.Z` with the semver you are shipping (no `v` prefix in `pyproject.toml`; use `vX.Y.Z` for the git tag).

### 1. Prepare (Cursor or manual)

- [ ] Move everything from `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`
- [ ] Leave an empty `## [Unreleased]` section at the top
- [ ] Set `version = "X.Y.Z"` in `pyproject.toml`
- [ ] Run `make all` (ruff, mypy, pytest)

**Cursor shortcut:** ask the agent to *“prepare release vX.Y.Z”* (see [`.cursor/rules/04-release-preparation.mdc`](../.cursor/rules/04-release-preparation.mdc)).

### 2. Verify release notes (optional but recommended)

```bash
python scripts/extract_changelog.py vX.Y.Z | less
```

You should see exactly the section that will appear on GitHub if you attach release notes manually.

### 3. Commit, tag, push

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "chore: release X.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

### 4. CI does the rest

On tag push, [`.github/workflows/pypi_publish.yml`](../.github/workflows/pypi_publish.yml):

1. Builds sdist and wheel with `python -m build`
2. Publishes to PyPI (trusted publishing)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| PyPI version already exists | Bump patch version; never re-use a published version. |
| Notes look wrong | Re-run locally: `python scripts/extract_changelog.py vX.Y.Z` and compare to `CHANGELOG.md`. |
| CI fails on tests | Run `make all` locally before tagging. |

---

## Related

- [`CHANGELOG.md`](../CHANGELOG.md)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — quality gates before tag
- [`scripts/extract_changelog.py`](../scripts/extract_changelog.py)
