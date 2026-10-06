"""Regression tests for the non-mutating Makefile and CI quality contract."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_nltk_is_absent_from_parser_extras_and_lock() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

    assert all(
        "nltk" not in dependency.casefold()
        for dependencies in pyproject["project"]["optional-dependencies"].values()
        for dependency in dependencies
    )
    assert all(
        "nltk" not in dependency.casefold()
        for dependency in pyproject["tool"]["uv"]["constraint-dependencies"]
    )
    assert not any(package["name"].casefold() == "nltk" for package in lock["package"])


class MakefileContractError(AssertionError):
    """Stable diagnostics for the deliberately small supported Makefile syntax."""


_TARGET_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _read_makefile_recipes(target: str, makefile: Path = ROOT / "Makefile") -> list[str]:
    entries: dict[str, tuple[list[str], list[str]]] = {}
    continuation_targets: set[str] = set()
    current: tuple[list[str], list[str]] | None = None

    for line_number, raw_line in enumerate(makefile.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("\t"):
            if current is None:
                raise MakefileContractError(f"orphan-recipe:{line_number}")
            if raw_line.rstrip().endswith("\\"):
                continuation_targets.update(
                    name for name, entry in entries.items() if entry is current
                )
                continue
            recipe = raw_line[1:].strip()
            if recipe:
                current[1].append(recipe)
            continue
        if ":" not in raw_line:
            raise MakefileContractError(f"unsupported-syntax:{line_number}")

        name, prerequisite_text = raw_line.split(":", 1)
        name = name.strip()
        prerequisites = prerequisite_text.split()
        if not _TARGET_NAME.fullmatch(name) or any(
            not _TARGET_NAME.fullmatch(item) for item in prerequisites
        ):
            raise MakefileContractError(f"invalid-declaration:{line_number}")
        if name == ".PHONY":
            current = None
            continue
        if name in entries:
            raise MakefileContractError(f"duplicate-target:{name}")
        current = (prerequisites, [])
        entries[name] = current

    if not _TARGET_NAME.fullmatch(target):
        raise MakefileContractError("invalid-requested-target")
    if target not in entries:
        raise MakefileContractError("unknown-target")

    expanded: set[str] = set()
    visiting: set[str] = set()
    commands: list[str] = []

    def visit(name: str) -> None:
        if name in visiting:
            raise MakefileContractError("dependency-cycle")
        if name in expanded:
            return
        if name not in entries:
            raise MakefileContractError("unresolved-prerequisite")
        if name in continuation_targets:
            raise MakefileContractError("unsupported-continuation")
        visiting.add(name)
        prerequisites, recipes = entries[name]
        for prerequisite in prerequisites:
            visit(prerequisite)
        visiting.remove(name)
        expanded.add(name)
        commands.extend(recipes)

    visit(target)
    if not commands:
        raise MakefileContractError("empty-closure")
    return commands


def test_structural_reader_preserves_depth_first_recipe_order(tmp_path: Path) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "all: first second\n\tprintf aggregate\nfirst:\n\tprintf first\nsecond:\n\tprintf second\n",
        encoding="utf-8",
    )

    assert _read_makefile_recipes("all", makefile) == [
        "printf first",
        "printf second",
        "printf aggregate",
    ]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("all: missing\n", "unresolved-prerequisite"),
        ("all: loop\nloop: all\n", "dependency-cycle"),
        ("all:\n\tprintf first \\\n\tprintf second\n", "unsupported-continuation"),
        ("all:\nall:\n\tprintf duplicate\n", "duplicate-target:all"),
    ],
)
def test_structural_reader_fails_closed_on_ambiguous_syntax(
    tmp_path: Path, text: str, message: str
) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text(text, encoding="utf-8")

    with pytest.raises(MakefileContractError, match=re.escape(message)):
        _read_makefile_recipes("all", makefile)


def test_lint_targets_separate_verification_from_rewrites() -> None:
    assert _read_makefile_recipes("lint") == ["uv run ruff check ."]
    assert _read_makefile_recipes("lint-fix") == ["uv run ruff check . --fix"]


def test_all_uses_only_non_mutating_ruff_targets() -> None:
    commands = _read_makefile_recipes("all")

    assert "uv run ruff check ." in commands
    assert "uv run ruff check . --fix" not in commands


def test_check_type_checks_compatibility_snapshot_generator() -> None:
    commands = _read_makefile_recipes("check")

    mypy_command = next(command for command in commands if command.startswith("uv run mypy "))
    assert "scripts/update_compat_snapshots.py" in mypy_command
    assert "scripts/generate_supply_chain_evidence.py" in mypy_command


def test_ci_finishes_with_clean_checkout_assertion() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    lint = workflow.index("run: make lint")
    verify_clean = workflow.index("run: make verify-clean")

    assert lint < verify_clean
    assert verify_clean > workflow.index("run: make docs-check")


def test_verify_clean_reports_any_dirty_checkout() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert 'status="$$(git status --porcelain)"' in makefile
    assert "printf '%s\\n' \"$$status\"" in makefile


def test_all_external_actions_are_immutable_sha_pins() -> None:
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    uses_pattern = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)

    for workflow in workflows:
        for action in uses_pattern.findall(workflow.read_text(encoding="utf-8")):
            if action.startswith("./"):
                continue
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), (
                f"{workflow.name} has a mutable action reference: {action}"
            )


def test_release_builds_once_and_orders_publication() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(encoding="utf-8")

    assert workflow.count("uv build --out-dir release-bundle/dist") == 1
    assert workflow.count('version: "0.11.7"') == 2
    assert "needs: pre-flight" in workflow
    assert "needs: build" in workflow
    assert "needs: publish" in workflow
    assert "sed 's#  dist/#  #' > SHA256SUMS" in workflow
    assert workflow.count("sha256sum --check -") == 3
    assert "packages-dir: release-bundle/dist/" in workflow
    assert "release-bundle/dist/*" in workflow


def test_build_backend_pin_keeps_release_metadata_twine_compatible() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'requires = ["hatchling==1.30.1"]' in pyproject


def test_release_publishes_and_verifies_supply_chain_evidence() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(encoding="utf-8")

    assert "--format cyclonedx1.5" in workflow
    assert "scripts/generate_supply_chain_evidence.py" in workflow
    assert "release-bundle/SBOM.cdx.json" in workflow
    assert "release-bundle/DEPENDENCY_LICENSES.json" in workflow
    assert workflow.count("actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6") == 2
    assert "id-token: write" in workflow
    assert "attestations: write" in workflow
    assert "gh attestation verify" in workflow
    assert "sbom-path: release-bundle/SBOM.cdx.json" in workflow


def test_dependency_review_is_read_only_and_pr_scoped() -> None:
    workflow = (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "pull_request_target" not in workflow
    assert "contents: read" in workflow
    assert "fail-on-severity: moderate" in workflow
    assert "license-check: false" in workflow
    assert "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294" in workflow


def test_scorecard_follows_the_restricted_official_job_shape() -> None:
    workflow = (ROOT / ".github" / "workflows" / "scorecard.yml").read_text(encoding="utf-8")

    assert 'branches: ["main"]' in workflow
    assert "permissions: read-all" in workflow
    assert "contents: read" in workflow
    assert "security-events: write" in workflow
    assert "id-token: write" in workflow
    assert "persist-credentials: false" in workflow
    assert "ossf/scorecard-action@2d1146689b8cda280b9bc96326124645441f03bc" in workflow
    assert "publish_results: true" in workflow


def test_daily_metrics_write_job_is_main_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "daily-metrics.yml").read_text(encoding="utf-8")

    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "ref: main" in workflow
    assert "git pull --ff-only origin main" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "pull_request" not in workflow
    assert "pull_request_target" not in workflow


def test_ci_uses_locked_cross_platform_native_actions_jobs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for job in ("quality", "tests", "dependency-audit", "package-contract"):
        assert f"\n  {job}:\n" in workflow
    for runner in ("ubuntu-24.04", "macos-15", "windows-2025"):
        assert runner in workflow
    assert '["3.12", "3.13"]' in workflow
    assert workflow.count("uv sync --locked --all-extras") == 4
    assert workflow.count("pip-audit") == 1
    assert "uv run pip-audit --no-deps --disable-pip" in workflow
    assert "--ignore-vuln PYSEC-2026-3740" not in workflow
    assert '-r "${{ runner.temp }}/requirements-audit.txt"' in workflow
    for flag in ("--all-extras", "--no-dev", "--no-emit-workspace"):
        assert flag in workflow
    assert "--no-hashes" not in workflow
    assert "twine==6.2.0" in workflow
    assert "mypy==1.20.2 dist-contract/*.whl" in workflow
    assert workflow.count("persist-credentials: false") == 4
    assert workflow.count("timeout-minutes:") == 4
    assert "pull_request_target" not in workflow


def test_ci_keeps_quality_checks_out_of_the_runtime_matrix() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    quality = workflow.split("\n  quality:\n", 1)[1].split("\n  tests:\n", 1)[0]
    tests = workflow.split("\n  tests:\n", 1)[1].split("\n  dependency-audit:\n", 1)[0]

    assert "run: make lint" in quality
    assert "run: make check" in quality
    assert "run: make docs-check" in quality
    assert "run: make vendor-name-check" in quality
    assert "run: make verify-clean" in quality
    assert "make " not in tests
    assert "uv run pytest" in tests
    assert "--cov-fail-under=80" in tests


def test_workflow_analysis_is_path_scoped_read_only_and_blocking() -> None:
    workflow = (ROOT / ".github/workflows/workflow-analysis.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert 'branches: ["main"]' in workflow
    assert workflow.count("paths:") == 2
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "timeout-minutes: 5" in workflow
    assert "actionlint_1.7.12_linux_amd64.tar.gz" in workflow
    assert "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8" in workflow
    assert 'run: |\n          "$RUNNER_TEMP/actionlint" -color' in workflow
    assert "zizmor==1.29.0" in workflow
    assert "--offline" not in workflow
    assert "--strict-collection" in workflow
    assert "--format=github" in workflow
    assert "GH_TOKEN" not in workflow
    assert "pull_request_target" not in workflow


def test_dependency_hygiene_is_periodic_and_not_a_pull_request_gate() -> None:
    workflow = (ROOT / ".github/workflows/dependency-hygiene.yml").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert "timeout-minutes: 5" in workflow
    assert 'version: "0.11.7"' in workflow
    assert "uv sync --locked --all-extras" in workflow
    assert "deptry==0.25.1" in workflow
    assert "uv run --with deptry==0.25.1 deptry . --github-output" in workflow


def test_dependabot_delays_routine_version_updates() -> None:
    config = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")

    assert config.count("cooldown:") == 2
    assert config.count("default-days: 7") == 2


def test_actionlint_pre_commit_hook_is_commit_pinned() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "https://github.com/rhysd/actionlint" in config
    assert "rev: 914e7df21a07ef503a81201c76d2b11c789d3fca" in config
    assert "-   id: actionlint" in config


def test_deptry_configuration_has_only_measured_scope_rules() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deptry = pyproject["tool"]["deptry"]

    assert deptry["extend_exclude"] == ["legacy"]
    assert deptry["per_rule_ignores"] == {"DEP004": ["logseq_matryca_parser"]}
    assert "ignore" not in deptry


def test_zizmor_configuration_has_no_global_rule_disable() -> None:
    config = (ROOT / "zizmor.yml").read_text(encoding="utf-8")

    assert "disable: true" not in config
    assert "dangerous-triggers" not in config


@pytest.mark.parametrize(
    "workflow_name",
    [
        "dependency-review.yml",
        "parser-adversarial.yml",
        "scorecard.yml",
        "daily-metrics.yml",
        "pypi_publish.yml",
    ],
)
def test_specialized_workflows_pin_standard_runner_images(workflow_name: str) -> None:
    workflow = (ROOT / ".github/workflows" / workflow_name).read_text(encoding="utf-8")

    assert "ubuntu-latest" not in workflow
    assert "runs-on: ubuntu-24.04" in workflow


def _workflow_jobs(text: str) -> list[list[str]]:
    """Read only conventional block jobs; reject layouts we cannot inspect."""
    jobs: dict[str, list[str]] = {}
    inside = False
    seen = False
    current: list[str] | None = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("jobs:"):
            assert not seen and re.fullmatch(r"jobs:\s*(?:#.*)?", line)
            seen = inside = True
            continue
        if not inside:
            continue
        assert "\t" not in line[: len(line) - len(line.lstrip())]
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            inside = False
            continue
        if indent == 2:
            match = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):\s*(?:#.*)?", line)
            assert match is not None, "unsupported job declaration"
            name = match[1]
            assert name not in jobs, "duplicate job"
            current = jobs[name] = []
        else:
            assert indent >= 4 and current is not None, "ambiguous job layout"
            assert not (indent == 4 and line.lstrip().startswith("<<:")), "merged job"
            current.append(line)
    assert seen and jobs, "missing block jobs"
    return list(jobs.values())


def _require_job_bounds(text: str) -> None:
    for job in _workflow_jobs(text):
        limits = [line for line in job if line.startswith("    timeout-minutes:")]
        assert len(limits) == 1, "each job needs its own timeout"
        assert re.fullmatch(r"    timeout-minutes:\s*[1-9][0-9]*\s*(?:#.*)?", limits[0])


def _require_read_only_checkouts(text: str) -> None:
    checkout_count = 0
    for job in _workflow_jobs(text):
        markers = [i for i, line in enumerate(job) if line.startswith("    steps:")]
        assert len(markers) == 1 and re.fullmatch(r"    steps:\s*(?:#.*)?", job[markers[0]])
        steps: list[list[str]] = []
        for line in job[markers[0] + 1 :]:
            indent = len(line) - len(line.lstrip())
            if indent == 4:
                break
            if indent == 6:
                assert re.match(r"      - (?:name|uses|run|id|if|shell):", line), "unsupported step"
                steps.append([line])
            else:
                assert indent >= 8 and steps, "ambiguous step layout"
                assert not (indent == 8 and line.lstrip().startswith("<<:")), "merged step"
                steps[-1].append(line)
        assert steps, "empty steps"
        for step in steps:
            uses = [line for line in step if re.match(r"(?:      - |        )uses:", line)]
            assert len(uses) <= 1, "duplicate step uses"
            if not uses:
                continue
            scalar = uses[0].split("uses:", 1)[1].split(" #", 1)[0].strip()
            plain = r"[A-Za-z0-9_.][A-Za-z0-9_./:@-]*"
            assert re.fullmatch(rf"(?:{plain}|'{plain}'|\"{plain}\")", scalar), (
                "unsupported uses scalar"
            )
            action = scalar.strip("\"'")
            if not action.casefold().startswith("actions/checkout@"):
                continue
            checkout_count += 1
            with_markers = [i for i, line in enumerate(step) if line.startswith("        with:")]
            assert len(with_markers) == 1
            start = with_markers[0]
            assert re.fullmatch(r"        with:\s*(?:#.*)?", step[start])
            options: list[str] = []
            for line in step[start + 1 :]:
                indent = len(line) - len(line.lstrip())
                if indent <= 8:
                    break
                if indent == 10:
                    assert not line.lstrip().startswith("<<:"), "merged checkout options"
                    options.append(line)
            flags = [line for line in options if line.startswith("          persist-credentials:")]
            assert len(flags) == 1
            assert re.fullmatch(r"          persist-credentials:\s*false\s*(?:#.*)?", flags[0])
    assert checkout_count > 0, "missing inspected checkout"


def test_specialized_workflows_bound_every_job() -> None:
    for name in (
        "dependency-review.yml",
        "parser-adversarial.yml",
        "scorecard.yml",
        "daily-metrics.yml",
        "pypi_publish.yml",
    ):
        _require_job_bounds((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def test_specialized_read_only_checkouts_do_not_persist_credentials() -> None:
    for name in (
        "dependency-review.yml",
        "parser-adversarial.yml",
        "scorecard.yml",
        "pypi_publish.yml",
    ):
        _require_read_only_checkouts(
            (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        )

    metrics = (ROOT / ".github/workflows/daily-metrics.yml").read_text(encoding="utf-8")
    assert "persist-credentials: true" in metrics


def _synthetic_specialized_workflows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, adversarial: str
) -> None:
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    for name in ("dependency-review.yml", "scorecard.yml", "daily-metrics.yml", "pypi_publish.yml"):
        (workflows / name).write_text(
            (ROOT / ".github/workflows" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (workflows / "parser-adversarial.yml").write_text(adversarial, encoding="utf-8")
    monkeypatch.setattr(__import__(__name__, fromlist=["ROOT"]), "ROOT", tmp_path)


def test_workflow_contracts_accept_multiple_independently_protected_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _synthetic_specialized_workflows(
        tmp_path,
        monkeypatch,
        """jobs:
  first:
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@abc
        with:
          persist-credentials: false
  second:
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@abc
        with:
          persist-credentials: false
""",
    )
    test_specialized_workflows_bound_every_job()
    test_specialized_read_only_checkouts_do_not_persist_credentials()


@pytest.mark.parametrize(
    "workflow",
    [
        "jobs:\n  first:\n    timeout-minutes: 10\n  second:\n    runs-on: ubuntu-24.04\n",
        "jobs:\n  first:\n    steps:\n      - run: true\n        timeout-minutes: 10\n",
        "jobs: {first: {timeout-minutes: 10}}\n",
        "jobs:\n  first:\n    timeout-minutes: 10\n  first:\n    runs-on: ubuntu-24.04\n",
        "jobs:\n  first:\n    timeout-minutes: 0\n",
        "jobs:\n  first:\n    timeout-minutes: true\n",
    ],
)
def test_workflow_contract_rejects_unbounded_or_ambiguous_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow: str
) -> None:
    _synthetic_specialized_workflows(tmp_path, monkeypatch, workflow)
    with pytest.raises(AssertionError):
        test_specialized_workflows_bound_every_job()


@pytest.mark.parametrize(
    "later_step",
    [
        "      - uses: actions/checkout@def\n",
        "      - uses: actions/checkout@def\n        with:\n          persist-credentials: true\n",
    ],
)
def test_workflow_contract_rejects_unprotected_later_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, later_step: str
) -> None:
    workflow = (
        "jobs:\n  first:\n    timeout-minutes: 10\n    steps:\n"
        "      - uses: actions/checkout@abc\n        with:\n"
        "          persist-credentials: false\n" + later_step
    )
    _synthetic_specialized_workflows(tmp_path, monkeypatch, workflow)
    with pytest.raises(AssertionError):
        test_specialized_read_only_checkouts_do_not_persist_credentials()


def test_workflow_contract_rejects_credential_flag_on_unrelated_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = (
        "jobs:\n  first:\n    timeout-minutes: 10\n    steps:\n"
        "      - uses: actions/checkout@abc\n"
        "      - uses: example/other@abc\n        with:\n"
        "          persist-credentials: false\n"
    )
    _synthetic_specialized_workflows(tmp_path, monkeypatch, workflow)
    with pytest.raises(AssertionError):
        test_specialized_read_only_checkouts_do_not_persist_credentials()


@pytest.mark.parametrize(
    "scalar",
    [
        ">-\n          actions/checkout@def",
        "|-\n          actions/checkout@def",
        "*checkout",
        "!!str actions/checkout@def",
        '"actions/\\x63heckout@def"',
    ],
)
def test_workflow_contract_rejects_unsupported_uses_after_protected_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scalar: str
) -> None:
    workflow = (
        "jobs:\n  first:\n    timeout-minutes: 10\n    steps:\n"
        "      - uses: actions/checkout@abc\n        with:\n"
        "          persist-credentials: false\n      - uses: " + scalar + "\n"
    )
    _synthetic_specialized_workflows(tmp_path, monkeypatch, workflow)
    with pytest.raises(AssertionError):
        test_specialized_read_only_checkouts_do_not_persist_credentials()


def test_adversarial_workflow_uses_the_locked_environment() -> None:
    workflow = (ROOT / ".github/workflows/parser-adversarial.yml").read_text(encoding="utf-8")

    assert 'version: "0.11.7"' in workflow
    assert "uv sync --locked --all-extras" in workflow


def test_release_disables_dependency_caches_and_preserves_order() -> None:
    workflow = (ROOT / ".github/workflows/pypi_publish.yml").read_text(encoding="utf-8")

    assert "enable-cache: true" not in workflow
    assert workflow.count("enable-cache: false") == 2
    assert "needs: pre-flight" in workflow
    assert "needs: build" in workflow
    assert "needs: publish" in workflow
    assert "softprops/action-gh-release" not in workflow
    assert "gh release create" in workflow
    assert "--verify-tag" in workflow
    assert "--notes-file release-bundle/RELEASE_NOTES.md" in workflow
    assert "--no-hashes" not in workflow
    assert "uv export --all-extras --no-dev --no-emit-workspace" in workflow
    assert "pip-audit --no-deps --disable-pip" in workflow


def test_ci_assurance_document_is_maintained_and_linked_from_entry_points() -> None:
    assurance = ROOT / "docs/CI_ASSURANCE.md"
    assert assurance.is_file()

    text = assurance.read_text(encoding="utf-8")
    for heading in (
        "## Pull-request and main checks",
        "## Scheduled and settings-managed assurance",
        "## Release assurance",
        "## Evidence boundaries",
    ):
        assert heading in text

    maintained = (ROOT / "docs/maintained.toml").read_text(encoding="utf-8")
    assert '"docs/CI_ASSURANCE.md"' in maintained
    for path in ("docs/README.md", "docs/index.md", "CONTRIBUTING.md", "AGENTS.md"):
        entry_point = (ROOT / path).read_text(encoding="utf-8")
        expected = "CI_ASSURANCE.md" if path.startswith("docs/") else "docs/CI_ASSURANCE.md"
        assert expected in entry_point


def test_ci_assurance_document_keeps_hosted_claims_evidence_bounded() -> None:
    text = (ROOT / "docs/CI_ASSURANCE.md").read_text(encoding="utf-8")

    assert "Local PASS" in text
    assert "Hosted PASS" in text
    assert "Settings PASS" in text
    assert "Publication PASS" in text
    assert "pull_request_target" in text
    assert "CodeQL default setup" in text
