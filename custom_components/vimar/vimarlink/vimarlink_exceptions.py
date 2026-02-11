"""Vimar API exceptions.

Custom exception hierarchy for better error handling.
"""


class VimarApiError(Exception):
    """Base exception for Vimar API errors."""

    def __init__(self, *args, **kwargs):
        """Initialize exception."""
        self.err_args = args
        super().__init__(*args)

    def __str__(self):
        """Stringify exception."""
        if self.err_args:
            return f"{self.__class__.__name__}: {self.err_args[0]}"
        return self.__class__.__name__


class VimarConfigError(VimarApiError):
    """Configuration error."""


class VimarConnectionError(VimarApiError):
    """Connection error."""


class VimarAuthenticationError(VimarApiError):
    """Authentication failed."""


class VimarXMLParseError(VimarApiError):
    """XML parsing failed."""


class VimarSQLError(VimarApiError):
    """SQL query error."""


class VimarTimeoutError(VimarApiError):
    """Request timeout error."""
