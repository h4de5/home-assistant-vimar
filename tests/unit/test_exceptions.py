"""Test exception hierarchy."""
import pytest
import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "custom_components", "vimar")
)

from vimarlink.vimarlink_exceptions import (
    VimarApiError,
    VimarAuthenticationError,
    VimarConfigError,
    VimarConnectionError,
    VimarSQLError,
    VimarTimeoutError,
    VimarXMLParseError,
)

pytestmark = pytest.mark.no_ha  # No HA required


def test_exception_hierarchy():
    """Test that all exceptions inherit from VimarApiError."""
    assert issubclass(VimarAuthenticationError, VimarApiError)
    assert issubclass(VimarConfigError, VimarApiError)
    assert issubclass(VimarConnectionError, VimarApiError)
    assert issubclass(VimarSQLError, VimarApiError)
    assert issubclass(VimarTimeoutError, VimarApiError)
    assert issubclass(VimarXMLParseError, VimarApiError)


def test_exception_str_representation():
    """Test exception string representation."""
    err = VimarAuthenticationError("Login failed")
    assert str(err) == "VimarAuthenticationError: Login failed"


def test_exception_can_be_raised():
    """Test exceptions can be raised and caught."""
    with pytest.raises(VimarConnectionError) as exc_info:
        raise VimarConnectionError("Connection refused")

    assert "Connection refused" in str(exc_info.value)


def test_base_exception_catch():
    """Test that VimarApiError catches all custom exceptions."""
    with pytest.raises(VimarApiError):
        raise VimarAuthenticationError("Test")

    with pytest.raises(VimarApiError):
        raise VimarConnectionError("Test")

    with pytest.raises(VimarApiError):
        raise VimarSQLError("Test")
