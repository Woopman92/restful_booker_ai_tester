"""Separate expected response discrepancies from test-data cleanup failures."""


class ResponseValuesMismatch(AssertionError):
    """Report response values that differ from the expected test data."""


class FormResponseMismatch(AssertionError):
    """Report the confirmed unsupported form-response serialization."""


class CleanupError(RuntimeError):
    """Report failures while discovering or deleting test-owned records."""
