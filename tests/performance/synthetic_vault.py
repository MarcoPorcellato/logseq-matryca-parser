from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Final

SYNTHETIC_VAULT_SCHEMA_VERSION: Final = 1
PAGE_COUNT: Final = 96
BLOCKS_PER_PAGE: Final = 24
DEEP_CHAIN_DEPTH: Final = 1024


def _ordinary_page_filename(index: int) -> str:
    return f"pages/runtime-evidence-page-{index:04d}.md"


def _ordinary_page_title(index: int) -> str:
    return f"runtime-evidence-page-{index:04d}"


def _page_link_target(index: int, page_count: int) -> str:
    if index < page_count - 1:
        return _ordinary_page_title(index + 1)
    return "runtime-evidence-deep"


def _build_ordinary_page_content(index: int, page_count: int, blocks_per_page: int) -> str:
    lines = [
        f"alias:: runtime-evidence-alias-{index:04d}\n",
        "\n",
        f"- block-{index:04d}-00 #runtime-evidence [[{_page_link_target(index, page_count)}]]\n",
    ]

    for block_index in range(1, blocks_per_page):
        lines.append(f"- block-{index:04d}-{block_index:02d}\n")

    return "".join(lines)


def _build_deep_chain() -> str:
    lines = []
    for depth in range(DEEP_CHAIN_DEPTH):
        lines.append(f"{'  ' * (depth + 1)}- chain-{depth:04d}\n")
    return "".join(lines)


@dataclass(frozen=True)
class SyntheticVault:
    files: tuple[tuple[PurePosixPath, bytes], ...]
    page_count: int
    blocks_per_page: int
    deep_chain_depth: int

    @property
    def total_source_bytes(self) -> int:
        return sum(len(content) for _, content in self.files)

    @property
    def deep_chain_source(self) -> str:
        return next(
            content.decode("utf-8")
            for relative_path, content in self.files
            if relative_path == PurePosixPath("pages/runtime-evidence-deep.md")
        )

    @property
    def source_sha256(self) -> str:
        digest = sha256()
        for relative_path, content in self.files:
            digest.update(relative_path.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(content)
            digest.update(b"\0")
        return digest.hexdigest()

    def materialize(self, destination: Path) -> Path:
        root = destination.resolve()
        for relative_path, content in self.files:
            target = (root / relative_path).resolve()
            try:
                target.relative_to(root)
            except ValueError as error:
                raise ValueError("synthetic vault path escapes destination") from error
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return root


def build_synthetic_vault() -> SyntheticVault:
    generated_files: list[tuple[PurePosixPath, bytes]] = []

    for index in range(1, PAGE_COUNT):
        path = PurePosixPath(_ordinary_page_filename(index))
        source = _build_ordinary_page_content(index, PAGE_COUNT, BLOCKS_PER_PAGE).encode(
            "utf-8"
        )
        generated_files.append((path, source))

    deep_path = PurePosixPath("pages/runtime-evidence-deep.md")
    generated_files.append((deep_path, _build_deep_chain().encode("utf-8")))

    generated_files.sort(key=lambda item: item[0].as_posix())

    return SyntheticVault(
        files=tuple(generated_files),
        page_count=PAGE_COUNT,
        blocks_per_page=BLOCKS_PER_PAGE,
        deep_chain_depth=DEEP_CHAIN_DEPTH,
    )
