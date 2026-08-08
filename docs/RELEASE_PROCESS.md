# Release process

**Logseq Matryca Parser** (The Logos Protocol · Marco Porcellato · [Matryca.ai](https://matryca.ai)) uses a **curated** [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog). Pushing a `v*` git tag triggers one ordered, fail-closed release workflow:

| Workflow | Result |
|----------|--------|
| [`.github/workflows/pypi_publish.yml`](../.github/workflows/pypi_publish.yml) | Qualifies the tag, builds once, publishes the exact distributions to **PyPI** with OIDC attestations, then creates the **GitHub Release** from the same checksummed bundle. |

The release graph is deliberately sequential:

```text
Python 3.12/3.13 pre-flight
  -> tag/version/changelog contract
  -> one wheel/sdist build + Twine + SHA-256
  -> PyPI trusted publication
  -> GitHub Release with the exact same distributions
```

Every external action is pinned to a full commit SHA. The uploaded Actions
artifact is transport only; `SHA256SUMS` is verified again before both public
publication stages.

---

## During development

Add user-facing bullets under **`## [Unreleased]`** (`Added` / `Changed` / `Fixed` / `Removed` / `Security`). One line per notable change. See [`.cursor/rules/05-auto-changelog.mdc`](../.cursor/rules/05-auto-changelog.mdc).

---

## Release day (local)

Replace `X.Y.Z` with the semver you are shipping (no `v` prefix in the source
version; use `vX.Y.Z` for the git tag).

### 1. Prepare (Cursor or manual)

- [ ] Move everything from `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`
- [ ] Leave an empty `## [Unreleased]` section at the top
- [ ] Set `__version__ = "X.Y.Z"` in `src/logseq_matryca_parser/_version.py`; Hatchling derives package metadata from this single source
- [ ] Update `README.md`, `SECURITY.md`, and contributor-facing current-version references
- [ ] Run `make all` (Ruff, Mypy, documentation checks, and Pytest)
- [ ] Run `python -m scripts.check_release_contract --tag vX.Y.Z`
- [ ] Build wheel and sdist once locally, run `python scripts/check_wheel_contract.py path/to/wheel.whl`, `twine check`, and record SHA-256 digests

**Cursor shortcut:** ask the agent to *“prepare release vX.Y.Z”* (see [`.cursor/rules/04-release-preparation.mdc`](../.cursor/rules/04-release-preparation.mdc)).

### 2. Verify release notes and package contract

```bash
python scripts/extract_changelog.py vX.Y.Z | less
python -m scripts.check_release_contract --tag vX.Y.Z
```

The first command shows exactly the section that will appear on GitHub. The
second rejects a malformed tag, a tag/source/runtime mismatch, non-empty
`[Unreleased]`, a missing versioned section, or release notes without bullets.

### 3. Commit, tag, push

```bash
git add CHANGELOG.md src/logseq_matryca_parser/_version.py README.md CONTRIBUTING.md SECURITY.md docs/
git commit -m "chore: release X.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

### 4. CI publishes the verified bundle

On tag push:

1. **Pre-flight** — Python 3.12 and 3.13 run dependency audit and `make all`.
2. **Build** — tag/version/changelog contract, one wheel/sdist build, wheel
   contract, Twine metadata check, release-note extraction, and SHA-256 manifest.
3. **PyPI** — trusted publishing uploads only the downloaded build artifact and
   creates PyPI's OIDC-backed attestations.
4. **GitHub Release** — runs only after PyPI succeeds and attaches the same
   wheel, sdist, and `SHA256SUMS` with curated changelog notes.

Verify the complete **Release** run under GitHub Actions, then verify the new
version, files, hashes, and attestations on PyPI and the GitHub Release page.

#### Failed or interrupted release

Do not rebuild or replace a published version. Inspect the failed job first:

1. If failure occurred before PyPI publication, fix the release contract and
   publish a new patch version.
2. If PyPI succeeded but GitHub Release creation failed, preserve the run's
   release bundle, verify `SHA256SUMS`, and create the GitHub Release from those
   exact files; never rebuild the distributions.
3. If artifact identity cannot be proven, publish a new patch version instead
   of attaching unverified files.

PyPI cannot be re-published for the same version; use a patch bump if the wheel upload failed.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Tag on GitHub but no **Release** page | Confirm whether PyPI succeeded; recover only from the checksummed artifact of that exact workflow run. |
| PyPI version already exists | Bump patch version; never re-use a published version. |
| Notes look wrong | Re-run locally: `python scripts/extract_changelog.py vX.Y.Z` and compare to `CHANGELOG.md`. |
| CI fails on tests | Run `make all` locally before tagging. |
| Tag/version mismatch | Run `python -m scripts.check_release_contract --tag vX.Y.Z`; align `_version.py`, runtime metadata, and changelog before creating a new tag. |
| Hash verification fails | Stop. Do not publish or attach the bundle; create a clean patch release after diagnosis. |

---

## Related

- [`CHANGELOG.md`](../CHANGELOG.md)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — quality gates before tag
- [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md) — contributor task index
- [`scripts/extract_changelog.py`](../scripts/extract_changelog.py)
