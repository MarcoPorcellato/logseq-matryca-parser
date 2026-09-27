from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_DISTRIBUTIONS = {"llama-index-core", "nltk"}


def _normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _requirement_name(requirement: str) -> str:
    name = re.split(r"[<=>!~;\[]", requirement, maxsplit=1)[0].strip()
    return _normalized_name(name)


def test_ai_and_all_exclude_llamaindex_and_nltk() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = project["project"]["optional-dependencies"]

    assert optional["ai"] == ["langchain-core"]
    assert {_requirement_name(item) for item in optional["all"]} == {
        "networkx",
        "pyvis",
        "langchain-core",
    }
    constraints = project["tool"]["uv"]["constraint-dependencies"]
    assert "nltk" not in {_requirement_name(item) for item in constraints}


def test_root_lock_has_no_llamaindex_or_nltk() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = lock["package"]

    package_names = {_normalized_name(package["name"]) for package in packages}
    assert package_names.isdisjoint(FORBIDDEN_DISTRIBUTIONS)

    root = next(package for package in packages if package["name"] == "logseq-matryca-parser")
    optional_names = {
        _normalized_name(dependency["name"])
        for dependencies in root.get("optional-dependencies", {}).values()
        for dependency in dependencies
    }
    metadata_names = {
        _normalized_name(dependency["name"])
        for dependency in root.get("metadata", {}).get("requires-dist", [])
    }
    assert optional_names.isdisjoint(FORBIDDEN_DISTRIBUTIONS)
    assert metadata_names.isdisjoint(FORBIDDEN_DISTRIBUTIONS)
