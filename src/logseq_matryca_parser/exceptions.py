"""Domain-specific parser exceptions."""


class LogseqParserError(Exception):
    """Base exception for parser failures."""


class LogseqIndentationError(LogseqParserError):
    """Raised when indentation jumps violate stack-machine constraints."""


class BlockReferenceError(LogseqParserError):
    """Raised when a block reference cannot be resolved."""
