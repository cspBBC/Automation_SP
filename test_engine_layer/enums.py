"""Enums - Test case type classifications."""

from enum import Enum


class TestCaseType(Enum):
    """Classification of test case types."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    EDGE = "EDGE"
