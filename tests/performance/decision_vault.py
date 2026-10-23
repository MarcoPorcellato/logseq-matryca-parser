"""Finite, in-memory fixtures for private decision-comparison test support.

Fixture identity is not workload admission or Parser performance evidence.
Importing this module constructs no vault and performs no measurement.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Final

from tests.performance import comparison_contract, synthetic_vault
from tests.performance.synthetic_vault import SyntheticVault

DECISION_VAULT_GENERATOR_NAMESPACE: Final = "decision-vault-generator"
DECISION_VAULT_GENERATOR_VERSION: Final = 1


def build_decision_vault(profile_id: str) -> SyntheticVault:
    """Build one fixed synthetic profile without reading or writing a vault."""
    if type(profile_id) is not str:
        raise TypeError("profile_id must be a string")
    descriptor = next(
        (item for item in comparison_contract._VAULT_PROFILES if item.profile_id == profile_id),
        None,
    )
    if descriptor is None:
        raise ValueError("unknown decision vault profile")
    if descriptor.profile_id == "vault-small-96-v1":
        return synthetic_vault.build_synthetic_vault()
    files = [
        (
            PurePosixPath(synthetic_vault._ordinary_page_filename(index)),
            synthetic_vault._build_ordinary_page_content(
                index, descriptor.total_pages, descriptor.blocks_per_ordinary_page
            ).encode("utf-8"),
        )
        for index in range(1, descriptor.total_pages)
    ]
    files.append(
        (
            PurePosixPath("pages/runtime-evidence-deep.md"),
            synthetic_vault._build_deep_chain().encode("utf-8"),
        )
    )
    files.sort(key=lambda item: item[0].as_posix())
    return SyntheticVault(
        files=tuple(files),
        page_count=descriptor.total_pages,
        blocks_per_page=descriptor.blocks_per_ordinary_page,
        deep_chain_depth=descriptor.deep_chain_nodes,
    )
