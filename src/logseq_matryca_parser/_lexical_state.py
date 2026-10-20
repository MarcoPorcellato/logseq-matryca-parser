from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_LexicalMode = Literal["normal", "yaml", "code", "query", "drawer"]


@dataclass
class _LexicalState:
    mode: _LexicalMode = "normal"
    frontmatter_active: bool = True
    properties_allowed: bool = True
    code_fence_char: str | None = None
    code_fence_length: int = 0

    def begin_yaml_frontmatter(self) -> None:
        self.mode = "yaml"

    def finish_yaml_frontmatter(self) -> None:
        self.mode = "normal"
        self.frontmatter_active = False

    def begin_code_block(
        self,
        *,
        fence_char: str | None = None,
        fence_length: int = 0,
    ) -> None:
        self.mode = "code"
        self.frontmatter_active = False
        self.properties_allowed = False
        self.code_fence_char = fence_char
        self.code_fence_length = fence_length if fence_char is not None else 0

    def consume_code_line(
        self,
        *,
        is_code_fence: bool,
        fence_char: str | None = None,
        fence_length: int = 0,
        fence_suffix: str = "",
    ) -> None:
        matches_opening_fence = self.code_fence_char is None or (
            fence_char == self.code_fence_char
            and fence_length >= self.code_fence_length
            and not fence_suffix.strip()
        )
        if is_code_fence and matches_opening_fence:
            self.mode = "normal"
            self.properties_allowed = True
            self.code_fence_char = None
            self.code_fence_length = 0
        self.frontmatter_active = False

    def begin_query_block(self) -> None:
        self.mode = "query"
        self.frontmatter_active = False
        self.properties_allowed = False

    def consume_query_line(self, *, is_query_end: bool) -> None:
        if is_query_end:
            self.mode = "normal"
        self.frontmatter_active = False

    def begin_drawer(self) -> None:
        self.mode = "drawer"

    def consume_drawer_line(self, *, is_drawer_end: bool, is_bullet: bool) -> bool:
        if is_drawer_end or is_bullet:
            self.mode = "normal"
            return False
        return True

    def observe_structural_node(self) -> None:
        self.frontmatter_active = False
        self.properties_allowed = True

    def observe_property(self) -> None:
        self.frontmatter_active = False

    def observe_continuation(
        self,
        *,
        is_code_fence: bool,
        is_query_begin: bool,
        fence_char: str | None = None,
        fence_length: int = 0,
    ) -> None:
        self.frontmatter_active = False
        self.properties_allowed = False
        if is_code_fence:
            self.begin_code_block(fence_char=fence_char, fence_length=fence_length)
        if is_query_begin:
            self.begin_query_block()

    def observe_nonstructural_line_without_node(self) -> None:
        self.frontmatter_active = False
