"""Authentication and session management for VIMAR.

This module handles HTTP adapter configuration and SSL setup for
communicating with VIMAR webservers that require old TLS versions.
"""

from __future__ import annotations

import logging
import ssl

from requests import adapters

_LOGGER = logging.getLogger(__name__)


class HTTPAdapter(adapters.HTTPAdapter):
    """Custom HTTP adapter supporting old TLS versions.

    VIMAR webservers require TLSv1 with AES256-SHA cipher.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the HTTPAdapter."""
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """Initialize connection pool with old SSL settings."""
        ssl_context = ssl.create_default_context()

        # Sets up old and insecure TLSv1 for VIMAR compatibility
        ssl_context.options &= ~ssl.OP_NO_TLSv1_3 & ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        ssl_context.check_hostname = False

        # VIMAR requires AES256-SHA cipher
        ssl_context.set_ciphers("AES256-SHA")

        kwargs["ssl_context"] = ssl_context
        return super().init_poolmanager(*args, **kwargs)


class VimarAuth:
    """Handle authentication and session management."""

    def __init__(
        self,
        schema: str,
        host: str,
        port: int,
        username: str,
        password: str,
        certificate: str | None = None,
    ):
        """Initialize authentication handler."""
        self._schema = schema
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._certificate = certificate
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        """Return current session ID."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None) -> None:
        """Set session ID."""
        self._session_id = value

    def is_logged(self) -> bool:
        """Check if session is available."""
        return self._session_id is not None

    @property
    def base_url(self) -> str:
        """Return base URL for VIMAR server."""
        return f"{self._schema}://{self._host}:{self._port}"

    @property
    def username(self) -> str:
        """Return username."""
        return self._username

    @property
    def password(self) -> str:
        """Return password."""
        return self._password

    @property
    def certificate(self) -> str | None:
        """Return certificate path."""
        return self._certificate
