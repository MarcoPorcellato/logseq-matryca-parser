"""Opt-in scale-fixture correctness checks; not collected by default CI.

Select this file explicitly with pytest. No vault is parsed or materialized,
and no performance observation or runtime-admission receipt is produced.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import PurePosixPath

import pytest

from tests.performance.decision_vault import build_decision_vault
from tests.test_performance_decision_vault import (
    _assert_reference_vault,
    _change_byte,
    _change_line_endings,
    _change_order,
    _drop_page,
)


@pytest.mark.parametrize(
    ("profile_id", "pages", "blocks", "source_bytes", "fingerprint"),
    [
        (
            "vault-scale-1000-v1",
            1000,
            25000,
            1_532_437,
            "bba08886accc6d7a92253ba033fb8149f3af93e52428f61470c6c4f7a4e06e01",
        ),
        (
            "vault-scale-10000-v1",
            10000,
            241000,
            5_762_437,
            "47e33f710c722aaaefee822a304bb4a65bc68149c111705e106de92f305b7c12",
        ),
    ],
    ids=["vault-scale-1000-v1", "vault-scale-10000-v1"],
)
def test_scale_profile_matches_independent_bytes_and_golden(
    profile_id: str,
    pages: int,
    blocks: int,
    source_bytes: int,
    fingerprint: str,
) -> None:
    vault = build_decision_vault(profile_id)
    _assert_reference_vault(vault, pages, source_bytes, fingerprint)
    assert (
        sum(
            line.lstrip().startswith(b"- ")
            for _, content in vault.files
            for line in content.splitlines()
        )
        == blocks
    )
    assert build_decision_vault(profile_id).files == vault.files
    assert vault.deep_chain_source == build_decision_vault("vault-small-96-v1").deep_chain_source

    for mutate in (_drop_page, _change_byte, _change_line_endings, _change_order):
        changed = replace(vault, files=mutate(vault.files))
        with pytest.raises(AssertionError):
            _assert_reference_vault(changed, pages, source_bytes, fingerprint)

    final_path = PurePosixPath(f"pages/runtime-evidence-page-{pages - 1:04d}.md")
    changed_files = tuple(
        (
            name,
            content.replace(b"[[runtime-evidence-deep]]", b"[[runtime-evidence-nope]]", 1)
            if name == final_path
            else content,
        )
        for name, content in vault.files
    )
    assert changed_files != vault.files
    changed = replace(vault, files=changed_files)
    assert changed.total_source_bytes == source_bytes
    with pytest.raises(AssertionError):
        _assert_reference_vault(changed, pages, source_bytes, fingerprint)
