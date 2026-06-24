"""Dedicated tests for the parser exception hierarchy (issue #21).

Verifies that all domain exceptions inherit from LogseqParserError and
that each class can be instantiated with a message string.
"""

from __future__ import annotations

import pytest

from logseq_matryca_parser.exceptions import (
    BlockReferenceError,
    LogseqIndentationError,
    LogseqParserError,
)


class TestExceptionHierarchy:
    """Structural assertions on the exception class hierarchy."""

    def test_block_reference_error_is_subclass_of_logseq_parser_error(self):
        """BlockReferenceError must inherit from the base parser exception."""
        assert issubclass(BlockReferenceError, LogseqParserError)

    def test_logseq_indentation_error_is_subclass_of_logseq_parser_error(self):
        """LogseqIndentationError must inherit from LogseqParserError.

        Note: LogseqIndentationError is reserved for a future strict
        indentation mode and is not raised by the parser today.
        """
        assert issubclass(LogseqIndentationError, LogseqParserError)

    def test_base_exception_is_standard_exception(self):
        """LogseqParserError itself inherits from built-in Exception."""
        assert issubclass(LogseqParserError, Exception)


class TestExceptionInstantiation:
    """Behavioural assertions — can instantiate and use as exceptions."""

    def test_block_reference_error_can_be_raised_and_caught(self):
        with pytest.raises(BlockReferenceError, match="test error"):
            raise BlockReferenceError("test error")

    def test_block_reference_error_is_caught_by_base_class(self):
        """Catching LogseqParserError also catches BlockReferenceError."""
        with pytest.raises(LogseqParserError):
            raise BlockReferenceError("caught by base")

    def test_logseq_indentation_error_can_be_raised_and_caught(self):
        """LogseqIndentationError accepts a message like other exceptions."""
        with pytest.raises(LogseqIndentationError, match="indent"):
            raise LogseqIndentationError("broken indent")

    def test_logseq_indentation_error_is_caught_by_base_class(self):
        """Catching LogseqParserError also catches LogseqIndentationError."""
        with pytest.raises(LogseqParserError):
            raise LogseqIndentationError("caught by base")

    def test_base_exception_stores_message(self):
        exc = LogseqParserError("base message")
        assert str(exc) == "base message"
