from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_LexicalMode = Literal["normal", "yaml", "code", "query", "drawer"]


@dataclass
class _LexicalState:
    mode: _LexicalMode = "normal"
    frontmatter_active: bool = True
    properties_allowed: bool = True

    def begin_yaml_frontmatter(self) -> None:
        self.mode = "yaml"

    def finish_yaml_frontmatter(self) -> None:
        self.mode = "normal"
        self.frontmatter_active = False

    def begin_code_block(self) -> None:
        self.mode = "code"
        self.frontmatter_active = False
        self.properties_allowed = False

    def consume_code_line(self, *, is_code_fence: bool) -> None:
        if is_code_fence:
            self.mode = "normal"
            self.properties_allowed = True
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

    def observe_continuation(self, *, is_code_fence: bool, is_query_begin: bool) -> None:
        self.frontmatter_active = False
        self.properties_allowed = False
        if is_code_fence:
            self.begin_code_block()
        if is_query_begin:
            self.begin_query_block()

    def observe_nonstructural_line_without_node(self) -> None:
        self.frontmatter_active = False
