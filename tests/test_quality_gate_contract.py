"""Regression tests for the non-mutating Makefile and CI quality contract."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nltk_security_floor_uses_a_stable_registry_constraint() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    constraints = pyproject["tool"]["uv"]["constraint-dependencies"]

    assert "nltk>=3.10.3" in constraints


def test_nltk_is_not_declared_as_a_vcs_override() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    overrides = pyproject["tool"]["uv"].get("override-dependencies", [])

    assert not any(dependency.startswith("nltk") for dependency in overrides)


def test_nltk_lock_uses_a_patched_registry_release() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    nltk = next(package for package in lock["package"] if package["name"] == "nltk")

    assert nltk["source"] == {"registry": "https://pypi.org/simple"}
    assert tuple(int(part) for part in nltk["version"].split(".")) >= (3, 10, 3)


def _dry_run(target: str) -> list[str]:
    result = subprocess.run(
        ["make", "--no-print-directory", "--dry-run", target],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_lint_targets_separate_verification_from_rewrites() -> None:
    assert _dry_run("lint") == ["uv run ruff check ."]
    assert _dry_run("lint-fix") == ["uv run ruff check . --fix"]


def test_all_uses_only_non_mutating_ruff_targets() -> None:
    commands = _dry_run("all")

    assert "uv run ruff check ." in commands
    assert "uv run ruff check . --fix" not in commands


def test_check_type_checks_compatibility_snapshot_generator() -> None:
    commands = _dry_run("check")

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
    workflow = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(
        encoding="utf-8"
    )

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
    workflow = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(
        encoding="utf-8"
    )

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
    workflow = (ROOT / ".github" / "workflows" / "daily-metrics.yml").read_text(
        encoding="utf-8"
    )

    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "ref: main" in workflow
    assert "git pull --ff-only origin main" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "pull_request" not in workflow
    assert "pull_request_target" not in workflow


def test_workflow_analysis_is_path_scoped_and_blocking() -> None:
    workflow = (ROOT / ".github" / "workflows" / "workflow-analysis.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert 'branches: ["main"]' in workflow
    assert workflow.count("paths:") == 2
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "actionlint_1.7.12_linux_amd64.tar.gz" in workflow
    assert "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8" in workflow
    assert 'run: |\n          "$RUNNER_TEMP/actionlint" -color' in workflow
    assert "zizmor==1.29.0" in workflow
    assert "--offline" in workflow
    assert "--strict-collection" in workflow
    assert "--format=github" in workflow
    assert "GH_TOKEN" not in workflow


def test_dependency_hygiene_is_periodic_and_not_a_pull_request_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "dependency-hygiene.yml").read_text(
        encoding="utf-8"
    )

    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "contents: read" in workflow
    assert "persist-credentials: false" in workflow
    assert "deptry==0.25.1" in workflow
    assert "uv run --with deptry==0.25.1 deptry . --github-output" in workflow
    assert "uvx --from deptry" not in workflow


def test_actionlint_pre_commit_hook_is_pinned_to_the_qualified_commit() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "https://github.com/rhysd/actionlint" in config
    assert "rev: 914e7df21a07ef503a81201c76d2b11c789d3fca" in config
    assert "-   id: actionlint" in config


def test_non_writing_checkouts_do_not_persist_credentials() -> None:
    workflows = {
        name: (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        for name in ("ci.yml", "parser-adversarial.yml", "pypi_publish.yml")
    }

    assert workflows["ci.yml"].count("persist-credentials: false") == 2
    assert workflows["parser-adversarial.yml"].count("persist-credentials: false") == 1
    assert workflows["pypi_publish.yml"].count("persist-credentials: false") == 2

    daily_metrics = (ROOT / ".github" / "workflows" / "daily-metrics.yml").read_text(
        encoding="utf-8"
    )
    assert "persist-credentials: true" in daily_metrics
    assert "zizmor: ignore[artipacked]" in daily_metrics


def test_release_build_jobs_disable_dependency_caches() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pypi_publish.yml").read_text(
        encoding="utf-8"
    )

    assert "enable-cache: true" not in workflow
    assert workflow.count("enable-cache: false") == 2


def test_dependabot_delays_version_updates_without_delaying_security_updates() -> None:
    config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert config.count("cooldown:") == 2
    assert config.count("default-days: 7") == 2


def test_deptry_configuration_has_only_the_measured_scope_rules() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deptry = pyproject["tool"]["deptry"]

    assert deptry["extend_exclude"] == ["legacy"]
    assert deptry["per_rule_ignores"] == {"DEP004": ["logseq_matryca_parser"]}
    assert "ignore" not in deptry


def test_zizmor_configuration_uses_only_the_release_action_exception() -> None:
    config = (ROOT / "zizmor.yml").read_text(encoding="utf-8")

    assert config.count("ignore:") == 1
    assert "artipacked:" not in config
    assert "superfluous-actions:" in config
    assert "pypi_publish.yml:205" in config
    assert "disable: true" not in config


def test_ccp_matrix_configuration_covers_both_supported_python_versions() -> None:
    config = tomllib.loads((ROOT / ".commit-ci-preflight.toml").read_text(encoding="utf-8"))

    assert config["schema_version"] == "2.0"
    assert config["project"] == "MarcoPorcellato/logseq-matryca-parser"
    assert config["receipt"] == {
        "output": ".ccp/receipt.json",
        "freshness_seconds": 86400,
    }
    assert config["environment"] == {"allow": []}

    runtimes = {runtime["id"]: runtime for runtime in config["runtimes"]}
    assert set(runtimes) == {"python312", "python313"}
    for runtime in runtimes.values():
        assert re.fullmatch(r"[^@]+@sha256:[0-9a-f]{64}", runtime["image"])
        assert runtime["network"] is True

    checks = config["checks"]
    assert {check["runtime_id"] for check in checks} == set(runtimes)
    assert all(check["required"] is True for check in checks)
    assert all(check["argv"][0] not in {"bash", "sh", "zsh"} for check in checks)
    assert all("make" not in check["argv"] for check in checks)
    assert {check["id"] for check in checks} == {
        "python312-sync",
        "python312-lint",
        "python312-types",
        "python312-vendor-policy",
        "python312-docs",
        "python312-tests",
        "python313-sync",
        "python313-tests",
    }


def test_ccp_operator_targets_verify_the_qualified_binary_before_use() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts" / "run_qualified_ccp.sh").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for target in ("ccp-plan", "ccp-doctor", "ccp-dry-run", "ccp-verify"):
        assert f"{target}:" in makefile
    assert "ccp-run:" not in makefile
    assert "command -v commit-ci-preflight" in launcher
    assert "/Users/" not in launcher
    assert "b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c" in launcher
    assert ".ccp/receipt.json" in gitignore
    assert ".ccp-mounts/" in gitignore


def test_ccp_policy_binds_the_reviewed_matrix_and_required_checks() -> None:
    policy = tomllib.loads((ROOT / ".commit-ci-policy.toml").read_text(encoding="utf-8"))

    assert policy["schema_version"] == "2.0"
    assert policy["project"] == "MarcoPorcellato/logseq-matryca-parser"
    assert policy["configuration_digest"] == (
        "sha256:4fb7f31095c8c74938df25f623cddb7feacc96d5fa9fe7364bf25b679a4796a2"
    )
    assert {(item["id"], item["runtime_id"]) for item in policy["required_checks"]} == {
        ("python312-sync", "python312"),
        ("python312-lint", "python312"),
        ("python312-types", "python312"),
        ("python312-vendor-policy", "python312"),
        ("python312-docs", "python312"),
        ("python312-tests", "python312"),
        ("python313-sync", "python313"),
        ("python313-tests", "python313"),
    }

    runtimes = {runtime["id"]: runtime for runtime in policy["runtimes"]}
    assert runtimes["python312"]["configuration_digest"] == (
        "sha256:28e8e38ea6eb7eef702b36f57f8c373ecc125896b3a3c30c021c501a0bc70a3f"
    )
    assert runtimes["python313"]["configuration_digest"] == (
        "sha256:82ed2a348589b029b4feeb03f34c46d9c12039dd9f113691de706c39606cf9b3"
    )
    assert all(
        runtime["platforms"]
        == [{"host_os": "macos", "host_arch": "aarch64", "runtime_kind": "docker_compatible"}]
        for runtime in runtimes.values()
    )
