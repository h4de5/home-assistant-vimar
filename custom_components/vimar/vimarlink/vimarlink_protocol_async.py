"""Async HTTP/SOAP/XML protocol handling for VIMAR.

This module provides async HTTP communication using aiohttp.
It can be used as an alternative to the sync protocol.
"""

from __future__ import annotations

import logging
import ssl

import aiohttp

_LOGGER = logging.getLogger(__name__)


class VimarProtocolAsync:
    """Async HTTP protocol handler using aiohttp."""

    def __init__(
        self,
        schema: str,
        host: str,
        port: int,
        certificate: str | None = None,
        timeout: int = 6,
    ):
        """Initialize async protocol handler."""
        self._schema = schema
        self._host = host
        self._port = port
        self._certificate = certificate
        self._timeout = timeout
        self.request_last_exception: Exception | None = None
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with VIMAR-compatible SSL."""
        if self._session is None or self._session.closed:
            # Match sync version's SSL settings for VIMAR compatibility
            ssl_context = ssl.create_default_context()
            ssl_context.options &= ~ssl.OP_NO_TLSv1_3 & ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1
            ssl_context.check_hostname = False
            ssl_context.set_ciphers("AES256-SHA")

            if self._certificate:
                ssl_context.load_verify_locations(self._certificate)
            else:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self._timeout, connect=int(self._timeout / 2))
            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)

        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        url: str,
        post: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> str | bool | None:
        """Make async HTTP request.

        Returns:
            Response text on success, False on error, None if no response
        """
        try:
            session = await self._get_session()

            if post is None:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    return await response.text()
            else:
                async with session.post(url, data=post, headers=headers) as response:
                    response.raise_for_status()
                    return await response.text()

        except aiohttp.ClientResponseError as http_err:
            self.request_last_exception = http_err
            _LOGGER.error("HTTP error %s: %s", http_err.status, str(http_err))
            return False
        except aiohttp.ClientConnectorError as ex:
            self.request_last_exception = ex
            _LOGGER.error("Connection error: %s", str(ex))
            return False
        except TimeoutError as ex:
            self.request_last_exception = ex
            _LOGGER.error("HTTP timeout after %ss", self._timeout)
            return False
        except aiohttp.ClientError as ex:
            self.request_last_exception = ex
            _LOGGER.error("Client error: %s", str(ex))
            return False
        except Exception as ex:
            self.request_last_exception = ex
            _LOGGER.error("Unexpected error: %s", str(ex))
            return False
