from __future__ import annotations

import inspect
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

import pytest

from logseq_matryca_parser.graph import LogseqGraph
from tests.performance.synthetic_vault import (
    BLOCKS_PER_PAGE,
    DEEP_CHAIN_DEPTH,
    PAGE_COUNT,
    SyntheticVault,
    build_synthetic_vault,
)


def test_synthetic_vault_has_the_fixed_original_shape() -> None:
    vault = build_synthetic_vault()

    assert vault.page_count == PAGE_COUNT == 96
    assert vault.blocks_per_page == BLOCKS_PER_PAGE == 24
    assert vault.deep_chain_depth == DEEP_CHAIN_DEPTH == 1024
    assert len(vault.files) == PAGE_COUNT
    assert vault.total_source_bytes > 0
    assert sum(1 for line in vault.deep_chain_source.splitlines() if line.lstrip().startswith("- ")) == (
        DEEP_CHAIN_DEPTH
    )


def test_synthetic_vault_is_deterministic_and_materializes_only_under_destination(tmp_path: Path) -> None:
    first = build_synthetic_vault()
    second = build_synthetic_vault()
    destination = tmp_path / "synthetic"

    first.materialize(destination)

    assert first.source_sha256 == second.source_sha256
    assert sorted(path.relative_to(destination) for path in destination.rglob("*.md"))
    assert all(path.is_relative_to(destination) for path in destination.rglob("*.md"))
    assert len(list(destination.rglob("*.md"))) == PAGE_COUNT


def test_synthetic_vault_has_no_external_input_parameter() -> None:
    assert inspect.signature(build_synthetic_vault).parameters == {}


def test_synthetic_vault_rejects_materialization_escape(tmp_path: Path) -> None:
    vault = SyntheticVault(
        files=((PurePosixPath("../escape.md"), b"- prohibited\n"),),
        page_count=1,
        blocks_per_page=1,
        deep_chain_depth=1,
    )

    with pytest.raises(ValueError):
        vault.materialize(tmp_path / "root")


def test_synthetic_vault_materializes_into_temporary_directory() -> None:
    vault = build_synthetic_vault()

    with TemporaryDirectory() as root:
        destination = Path(root) / "synthetic"
        vault.materialize(destination)

        assert destination.is_dir()
        assert (destination / "pages").is_dir()


def test_ordinary_pages_expose_logseq_alias_tag_and_cross_page_link(tmp_path: Path) -> None:
    vault = build_synthetic_vault()
    root = vault.materialize(tmp_path / "synthetic")

    graph = LogseqGraph.load_directory(root)
    page = graph.pages["runtime-evidence-page-0001"]
    root_node = page.root_nodes[0]

    assert len(page.root_nodes) == BLOCKS_PER_PAGE
    assert graph.get_page("runtime-evidence-alias-0001") is page
    assert "runtime-evidence" in root_node.tags
    assert "runtime-evidence-page-0002" in root_node.wikilinks
