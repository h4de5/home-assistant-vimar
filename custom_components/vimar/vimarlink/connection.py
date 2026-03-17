"""Vimar connection and authentication module."""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as xmlTree

import requests
import urllib3

from .exceptions import VimarApiError, VimarConfigError, VimarConnectionError
from .http_adapter import HTTPAdapter
from requests.exceptions import HTTPError

_LOGGER = logging.getLogger(__name__)
# FIX #19: rimosso SSL_IGNORED module-level global. Come globale non veniva
# mai resettato tra reload della config-entry nello stesso processo, quindi
# il messaggio debug "ignoring ssl" veniva soppresso anche per nuove istanze.
# Spostato come attributo _ssl_ignore_logged per istanza.


class VimarConnection:
    """Handles HTTP connections and authentication to Vimar web server."""

    def __init__(
        self,
        schema: str,
        host: str,
        port: int,
        username: str,
        password: str,
        certificate: str | None = None,
        timeout: int = 6,
    ):
        """Initialize connection parameters."""
        self._schema = schema
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._certificate = certificate
        self._timeout = timeout
        self._session_id: str | None = None
        self.request_last_exception: Exception | None = None
        # FIX #19: per-instance flag (era SSL_IGNORED globale di modulo)
        self._ssl_ignore_logged: bool = False

    @property
    def session_id(self) -> str | None:
        """Get current session ID."""
        return self._session_id

    def install_certificate(self) -> bool:
        """Download CA certificate from web server."""
        cert_changed = False

        if not self._certificate:
            return False

        temp_certificate = self._certificate
        self._certificate = None

        download_url = (
            f"{self._schema}://{self._host}:{self._port}"
            "/vimarbyweb/modules/vimar-byme/script/rootCA.VIMAR.crt"
        )

        certificate_file = self._request(download_url)
        self._certificate = temp_certificate

        if certificate_file is None or certificate_file is False:
            raise VimarConnectionError(
                f"Certificate download failed: {self.request_last_exception}"
            )

        old_cert = None
        try:
            with open(self._certificate, 'r') as f:
                old_cert = f.read()
        except OSError:
            old_cert = None

        if old_cert != certificate_file:
            cert_changed = True
            try:
                with open(self._certificate, 'w') as f:
                    f.write(certificate_file)
                _LOGGER.debug("Downloaded Vimar CA certificate to: %s", self._certificate)
            except OSError as err:
                raise VimarApiError(f"Saving certificate failed: {err}")

        return cert_changed

    def login(self) -> str | None:
        """Authenticate and get session ID."""
        login_url = (
            f"{self._schema}://{self._host}:{self._port}"
            f"/vimarbyweb/modules/system/user_login.php?"
            f"sessionid=&username={self._username}&password={self._password}&remember=0&op=login"
        )

        use_cert = bool(self._certificate)

        if self._schema == "https" and use_cert and not os.path.isfile(self._certificate):
            self.install_certificate()

        result = self._request(login_url)

        if result is False and use_cert:
            curr_ex_str = str(self.request_last_exception)
            if "SSLError" in curr_ex_str or "TLS CA" in curr_ex_str:
                try:
                    if self.install_certificate():
                        result = self._request(login_url)
                except Exception:
                    pass

        if result is None:
            _LOGGER.warning("Empty response from webserver login")
            return None

        if result is False:
            raise VimarConnectionError(f"Error during login: {self.request_last_exception}")

        try:
            xml = self._parse_xml(result)
            if not xml:
                raise Exception("Login failed - check username, password and certificate path")
            logincode = xml.find("result")
            loginmessage = xml.find("message")
        except Exception as err:
            raise VimarConnectionError(f"Error parsing login response: {err} - {result}")

        if logincode is not None and logincode.text != "0":
            msg = loginmessage.text if loginmessage is not None else logincode.text
            raise VimarConfigError(f"Error during login: {msg}")

        _LOGGER.info("Vimar login ok")
        loginsession = xml.find("sessionid")

        if loginsession is not None and loginsession.text:
            _LOGGER.debug("Got new Vimar Session id: %s", loginsession.text)
            self._session_id = loginsession.text
        else:
            _LOGGER.warning("Missing Session id in login response: %s", result)

        return result

    def is_logged(self) -> bool:
        """Check if session is available."""
        return self._session_id is not None

    def check_login(self) -> bool:
        """Ensure we have a valid session."""
        if not self._session_id:
            self.login()
        return self._session_id is not None

    def _request(
        self,
        url: str,
        post: str | None = None,
        headers: dict | None = None,
        check_ssl: bool = False,
    ) -> str | bool | None:
        """Execute HTTP request."""
        try:
            timeouts = (int(self._timeout / 2), self._timeout)

            if self._certificate:
                check_ssl = self._certificate
            else:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                # FIX #19: attributo di istanza invece di globale di modulo
                if not self._ssl_ignore_logged:
                    _LOGGER.debug("Request ignores ssl certificate")
                    self._ssl_ignore_logged = True

            with requests.Session() as s:
                s.mount("https://", HTTPAdapter())

                if post is None:
                    response = s.get(url, headers=headers, verify=check_ssl, timeout=timeouts)
                else:
                    response = s.post(
                        url, data=post, headers=headers, verify=check_ssl, timeout=timeouts
                    )

            response.raise_for_status()
            return response.text

        except HTTPError as http_err:
            self.request_last_exception = http_err
            _LOGGER.error("HTTP error occurred: %s", str(http_err))
            return False
        except requests.exceptions.Timeout as ex:
            self.request_last_exception = ex
            _LOGGER.error("HTTP timeout occurred")
            return False
        except Exception as err:
            self.request_last_exception = err
            _LOGGER.error("Error occurred: %s", str(err))
            return False

    def _parse_xml(self, xml: str) -> xmlTree.Element | None:
        """Parse XML response."""
        try:
            return xmlTree.fromstring(xml)
        except Exception as err:
            _LOGGER.error("Error parsing XML: %s", err)
            _LOGGER.debug("Problematic XML: %s", str(xml))
            return None
