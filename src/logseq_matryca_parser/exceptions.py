"""Domain-specific parser exceptions."""

from __future__ import annotations

from collections.abc import Sequence

from logseq_matryca_parser.diagnostics import Diagnostic


class LogseqParserError(Exception):
    """Base exception for parser failures."""


class LogseqIndentationError(LogseqParserError):
    """Raised when indentation jumps violate stack-machine constraints."""


class BlockReferenceError(LogseqParserError):
    """Raised when a block reference cannot be resolved."""


class PageTitleCollisionError(LogseqParserError):
    """Raised when strict graph loading encounters one or more title collisions."""

    def __init__(self, diagnostics: Sequence[Diagnostic]) -> None:
        self.diagnostics = tuple(diagnostics)
        if not self.diagnostics:
            raise ValueError("PageTitleCollisionError requires at least one diagnostic")
        first = self.diagnostics[0]
        winner = first.context["winner_path"]
        loser = first.context["loser_path"]
        super().__init__(
            f"Page title collision for {first.context['title']!r}: "
            f"winner={winner}, loser={loser}"
        )


class SessionAliasRegistryError(Exception):
    """Raised when the X-Ray alias state file cannot be parsed or validated."""
