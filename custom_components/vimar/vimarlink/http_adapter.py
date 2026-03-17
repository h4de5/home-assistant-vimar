"""Custom HTTP Adapter for old SSL/TLS support."""

from __future__ import annotations

import ssl
import urllib3
from requests import adapters

# Suppress InsecureRequestWarning when using self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HTTPAdapter(adapters.HTTPAdapter):
    """Override the default request method to support old SSL."""

    def __init__(self, *args, **kwargs):
        """Initialize the HTTPAdapter."""
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """Initialize the connection pool with TLSv1 support."""
        ssl_context = ssl.create_default_context()

        # Sets up old and insecure TLSv1
        ssl_context.options &= ~ssl.OP_NO_TLSv1_3 & ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        ssl_context.check_hostname = False
        ssl_context.set_ciphers("AES256-SHA")

        kwargs["ssl_context"] = ssl_context
        return super().init_poolmanager(*args, **kwargs)
