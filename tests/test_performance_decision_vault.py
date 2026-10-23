"""Byte identity checks for the private decision-vault fixtures.

These tests do not parse a graph, materialize a vault or admit runtime evidence.
Larger-profile checks are explicitly selected in decision_vault_scale_checks.py.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from pathlib import PurePosixPath
from types import ModuleType

import pytest

from tests.performance import synthetic_vault as legacy
from tests.performance.synthetic_vault import SyntheticVault

_SMALL_SHA256 = "adcbc2e2085aad2533ad5f9f5961c0525b291ad4fd47a89eb7ac42ab7b77e583"
_SMALL_SOURCE_BYTES = 1_107_557


def _decision_module() -> ModuleType:
    return importlib.import_module("tests.performance.decision_vault")


def _reference_files(total_pages: int) -> tuple[tuple[PurePosixPath, bytes], ...]:
    """Independent R2 templates: never call the builder or its byte helpers."""
    files: list[tuple[PurePosixPath, bytes]] = []
    for page in range(1, total_pages):
        destination = (
            f"runtime-evidence-page-{page + 1:04d}"
            if page + 1 < total_pages
            else "runtime-evidence-deep"
        )
        body = f"alias:: runtime-evidence-alias-{page:04d}\n\n".encode()
        for block in range(24):
            suffix = f" #runtime-evidence [[{destination}]]" if block == 0 else ""
            body += f"- block-{page:04d}-{block:02d}{suffix}\n".encode()
        files.append((PurePosixPath(f"pages/runtime-evidence-page-{page:04d}.md"), body))
    deep = b"".join(
        b"  " * (depth + 1) + f"- chain-{depth:04d}\n".encode() for depth in range(1024)
    )
    files.append((PurePosixPath("pages/runtime-evidence-deep.md"), deep))
    return tuple(sorted(files))


def _reference_digest(files: tuple[tuple[PurePosixPath, bytes], ...]) -> str:
    digest = sha256()
    for name, content in files:
        digest.update(name.as_posix().encode("utf-8") + b"\0" + content + b"\0")
    return digest.hexdigest()


def _assert_reference_vault(
    vault: SyntheticVault,
    total_pages: int,
    source_bytes: int,
    fingerprint: str,
) -> None:
    assert (vault.page_count, vault.blocks_per_page, vault.deep_chain_depth) == (
        total_pages,
        24,
        1024,
    )
    assert len(vault.files) == total_pages
    assert vault.total_source_bytes == source_bytes
    assert vault.source_sha256 == fingerprint
    assert _reference_digest(vault.files) == fingerprint
    expected = _reference_files(total_pages)
    assert _reference_digest(expected) == fingerprint
    assert sum(len(content) for _, content in expected) == source_bytes
    assert tuple(name for name, _ in vault.files) == tuple(name for name, _ in expected)
    for actual_file, expected_file in zip(vault.files, expected, strict=True):
        assert actual_file == expected_file


def _forbid_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("fixture construction was not permitted")

    for name in (
        "build_synthetic_vault",
        "_ordinary_page_filename",
        "_build_ordinary_page_content",
        "_build_deep_chain",
    ):
        monkeypatch.setattr(legacy, name, forbidden)


def test_small_profile_matches_legacy_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = legacy.build_synthetic_vault()
    original = legacy.build_synthetic_vault
    calls = 0

    def observed() -> SyntheticVault:
        nonlocal calls
        calls += 1
        return original()

    builder = _decision_module().build_decision_vault
    monkeypatch.setattr(legacy, "build_synthetic_vault", observed)
    first = builder("vault-small-96-v1")
    second = builder("vault-small-96-v1")
    assert first == second == expected
    assert first.files == expected.files
    assert calls == 2


def test_small_profile_matches_independent_golden() -> None:
    vault = _decision_module().build_decision_vault("vault-small-96-v1")
    _assert_reference_vault(vault, 96, _SMALL_SOURCE_BYTES, _SMALL_SHA256)
    assert (
        sum(
            line.lstrip().startswith(b"- ")
            for _, content in vault.files
            for line in content.splitlines()
        )
        == 3304
    )


class _ProfileLike:
    def __str__(self) -> str:
        raise AssertionError("profile input must not be coerced")

    def __eq__(self, other: object) -> bool:
        raise AssertionError("profile input must not be compared before validation")


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        True,
        False,
        96,
        96.0,
        b"vault-small-96-v1",
        PurePosixPath("vault-small-96-v1"),
        ["vault-small-96-v1"],
        {"profile_id": "vault-small-96-v1"},
        _ProfileLike(),
    ],
    ids=["none", "true", "false", "int", "float", "bytes", "path", "list", "dict", "coercible"],
)
def test_profile_id_rejects_non_string_without_construction(
    invalid: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _decision_module().build_decision_vault
    _forbid_construction(monkeypatch)
    with pytest.raises(TypeError, match="^profile_id must be a string$"):
        builder(invalid)


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "vault-scale-999-v1",
        "../outside",
        "private-input-marker",
        "VAULT-SMALL-96-V1",
        "vault-small-96-v1 ",
    ],
)
def test_unknown_profile_rejected_without_construction(
    invalid: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _decision_module().build_decision_vault
    _forbid_construction(monkeypatch)
    with pytest.raises(ValueError, match="^unknown decision vault profile$") as error:
        builder(invalid)
    if invalid:
        assert invalid not in str(error.value)


def test_builder_import_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _decision_module()
    _forbid_construction(monkeypatch)
    importlib.reload(module)
    assert module.DECISION_VAULT_GENERATOR_NAMESPACE == "decision-vault-generator"
    assert module.DECISION_VAULT_GENERATOR_VERSION == 1


def test_small_dispatch_does_not_construct_scale_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = legacy._build_ordinary_page_content
    calls: list[int] = []

    def small_only(index: int, page_count: int, blocks_per_page: int) -> str:
        assert page_count == 96 and blocks_per_page == 24
        calls.append(index)
        return original(index, page_count, blocks_per_page)

    monkeypatch.setattr(legacy, "_build_ordinary_page_content", small_only)
    vault = _decision_module().build_decision_vault("vault-small-96-v1")
    _assert_reference_vault(vault, 96, _SMALL_SOURCE_BYTES, _SMALL_SHA256)
    assert calls == list(range(1, 96))


def test_builder_accepts_only_profile_selection() -> None:
    assert tuple(inspect.signature(_decision_module().build_decision_vault).parameters) == (
        "profile_id",
    )
    assert not inspect.signature(legacy.build_synthetic_vault).parameters


def _drop_page(
    files: tuple[tuple[PurePosixPath, bytes], ...],
) -> tuple[tuple[PurePosixPath, bytes], ...]:
    return files[:-1]


def _change_path(
    files: tuple[tuple[PurePosixPath, bytes], ...],
) -> tuple[tuple[PurePosixPath, bytes], ...]:
    return ((PurePosixPath("pages/renamed.md"), files[0][1]),) + files[1:]


def _change_byte(
    files: tuple[tuple[PurePosixPath, bytes], ...],
) -> tuple[tuple[PurePosixPath, bytes], ...]:
    return files[:-1] + ((files[-1][0], files[-1][1] + b"x"),)


def _change_line_endings(
    files: tuple[tuple[PurePosixPath, bytes], ...],
) -> tuple[tuple[PurePosixPath, bytes], ...]:
    return files[:-1] + ((files[-1][0], files[-1][1].replace(b"\n", b"\r\n")),)


def _change_order(
    files: tuple[tuple[PurePosixPath, bytes], ...],
) -> tuple[tuple[PurePosixPath, bytes], ...]:
    return tuple(reversed(files))


@pytest.mark.parametrize(
    "mutate",
    [_drop_page, _change_path, _change_byte, _change_line_endings, _change_order],
    ids=["dropped-page", "path", "byte", "line-endings", "order"],
)
def test_fingerprint_changes_for_byte_path_and_order_mutations(
    mutate: Callable[
        [tuple[tuple[PurePosixPath, bytes], ...]], tuple[tuple[PurePosixPath, bytes], ...]
    ],
) -> None:
    vault = _decision_module().build_decision_vault("vault-small-96-v1")
    changed = replace(vault, files=mutate(vault.files))
    assert _reference_digest(changed.files) != _SMALL_SHA256
    with pytest.raises(AssertionError):
        _assert_reference_vault(changed, 96, _SMALL_SOURCE_BYTES, _SMALL_SHA256)
