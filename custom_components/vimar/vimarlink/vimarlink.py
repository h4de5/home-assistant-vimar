"""Connection to vimar web server."""

from __future__ import annotations

import time
import logging
import os
import ssl
import sys
import json
import xml.etree.ElementTree as xmlTree
from collections.abc import Callable
from typing import TypedDict
from xml.etree import ElementTree

import requests
import urllib3
from requests import adapters
from requests.exceptions import HTTPError

# Suppress InsecureRequestWarning when using self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import device type constants - fallback to local definitions for standalone use
try:
    from ..const import (
        DEVICE_TYPE_CLIMATES,
        DEVICE_TYPE_COVERS,
        DEVICE_TYPE_LIGHTS,
        DEVICE_TYPE_MEDIA_PLAYERS,
        DEVICE_TYPE_OTHERS,
        DEVICE_TYPE_SCENES,
        DEVICE_TYPE_SENSORS,
        DEVICE_TYPE_SWITCHES,
    )
except ImportError:
    # Standalone mode (e.g., examples/example.py) - define constants locally
    DEVICE_TYPE_LIGHTS = "light"
    DEVICE_TYPE_COVERS = "cover"
    DEVICE_TYPE_SWITCHES = "switch"
    DEVICE_TYPE_CLIMATES = "climate"
    DEVICE_TYPE_MEDIA_PLAYERS = "media_player"
    DEVICE_TYPE_SCENES = "scene"
    DEVICE_TYPE_SENSORS = "sensor"
    DEVICE_TYPE_OTHERS = "other"

_LOGGER = logging.getLogger(__name__)
_LOGGER_isDebug = _LOGGER.isEnabledFor(logging.DEBUG)
MAX_ROWS_PER_REQUEST = 300

# from homeassistant/components/switch/__init__.py
DEVICE_CLASS_OUTLET = "outlet"
DEVICE_CLASS_SWITCH = "switch"
# from homeassistant/components/cover/__init__.py
DEVICE_CLASS_SHUTTER = "shutter"
DEVICE_CLASS_WINDOW = "window"
# from homeassistant/const.py
DEVICE_CLASS_POWER = "power"
DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_PRESSURE = "pressure"

SSL_IGNORED = False


class HTTPAdapter(adapters.HTTPAdapter):
    """Override the default request method to support old SSL."""

    # see: https://www.reddit.com/r/learnpython/comments/hw6ann/using_requests_to_access_a_website_that_only/

    def __init__(self, *args, **kwargs):
        """Initialize the HTTPAdapter."""
        super().__init__(*args, **kwargs)

    # def init_poolmanager(self, *args, **kwargs):
    #     """Initialize the connection pool."""
    #     ssl_context = ssl.create_default_context()
    #     ssl_context.minimum_version = ssl.TLSVersion.TLSv1
    #     kwargs["ssl_context"] = ssl_context
    #     return super().init_poolmanager(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """Initialize the connection pool."""
        ssl_context = ssl.create_default_context()

        # Sets up old and insecure TLSv1.
        ssl_context.options &= ~ssl.OP_NO_TLSv1_3 & ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        ssl_context.check_hostname = False

        # Also you could try to set ciphers manually as it was in my case.
        # On other ciphers their server was reset the connection with:
        # [Errno 104] Connection reset by peer
        # ssl_context.set_ciphers("ECDHE-RSA-AES256-SHA")
        # https://stackoverflow.com/questions/38715570/restrieve-up-to-date-tls-cipher-suite-with-python
        # table https://testssl.sh/openssl-iana.mapping.html
        ssl_context.set_ciphers("AES256-SHA")

        # See urllib3.poolmanager.SSL_KEYWORDS for all available keys.
        kwargs["ssl_context"] = ssl_context
        # kwargs["assert_hostname"] = False
        return super().init_poolmanager(*args, **kwargs)


class VimarApiError(Exception):
    """Vimar API General Exception."""

    err_args = []

    def __init__(self, *args, **kwargs):
        """Init a default Vimar api exception."""
        self.err_args = args
        super().__init__(*args)

    def __str__(self):
        """Stringify exception text."""
        return f"{self.__class__.__name__}: {self.err_args[0]}" % self.err_args[1:]


class VimarConfigError(VimarApiError):
    """Vimar API Configuration Exception."""

    pass


class VimarConnectionError(VimarApiError):
    """Vimar API Connection Exception."""

    pass


# single device
#   'room_ids': number[] (maybe empty, ids of rooms)
#   'object_id': number (unique id of entity)
#   'object_name': str (name of the device, reformated in format_name)
#   'object_type': str (CH_xx channel name of vimar)
#   'status':  dict{dict{'status_id': number, 'status_value': str }}
#   'device_type': str (mapped type: light, switch, climate, cover, sensor)
#   'device_class': str (mapped class, based on name or attributes: fan, outlet, window, power)
class VimarDevice(TypedDict):
    """Single Vimar device for typing"""

    object_id: str
    room_ids: list[int]
    room_names: list[str]
    room_name: str
    object_name: str
    object_type: str
    status: dict[str, dict[str, str]]

    device_type: str
    device_class: str
    device_friendly_name: str
    icon: str
    pass


class VimarLink:
    """Link to communicate with the Vimar webserver."""

    # private
    _host = ""
    _schema = ""
    _port = 443
    _username = ""
    _password = ""
    _session_id = None
    _certificate = None
    _timeout = 6
    _status_timeout = 4

    _last_devices_status = None
    _last_devices_info = None
    _last_devices_status_cnt = 0
    _devices_status_mapping = {}
    _devices_update_date = 0

    _fetch_only_status = False

    #during configuration , create a new token, than the current instance try to recreate a token, and is in a loop :)
    _session_key = None
    _sessions = {}
    @classmethod
    def set_session_id(cls, key: str, session_id: str):
        cls._sessions[key] = session_id
    @classmethod
    def get_session_id(cls, key: str) -> str | None:
        return cls._sessions.get(key, None)

    def __init__(
        self,
        schema=None,
        host=None,
        port=None,
        username=None,
        password=None,
        certificate=None,
        timeout=None,
    ):
        """Prepare connections instance for vimar webserver."""
        _LOGGER.info("Vimar link initialized")

        # TODO - change static variables to normal instance variables
        # self._host = ''        
        if schema is not None:
            self._schema = schema
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port
        if username is not None:
            self._username = username
        if password is not None:
            self._password = password
        if certificate is not None:
            self._certificate = certificate
        if timeout is not None:
            self._timeout = timeout
            self._status_timeout = timeout * 0.5
        self._session_key = "%s%s|%s|%s" % (
            self._schema,
            self._host,
            self._username,
            self._password,
        )

    def install_certificate(self):
        """Download the CA certificate from the web server to be used for the next calls."""
        cert_changed = False
        # temporarily disable certificate requests
        if self._certificate is not None and len(self._certificate) != 0:
            temp_certificate = self._certificate
            self._certificate = None

            downloadPath = "%s://%s:%s/vimarbyweb/modules/vimar-byme/script/rootCA.VIMAR.crt" % (
                self._schema,
                self._host,
                self._port,
            )
            
            options = { "source": "install_certificate" }
            certificate_file = self._request(downloadPath, options=options)
            # get it back
            self._certificate = temp_certificate

            if certificate_file is None or certificate_file is False:
                raise VimarConnectionError(
                    "Certificate download failed: %s" % str(self.request_last_exception)
                )

            # compare current cert with downloaded cert, prevent saving if not changed
            old_cert = None
            try:
                file = open(self._certificate)
                old_cert = file.read()
                file.close()
            except OSError:
                old_cert = None

            if old_cert != certificate_file:
                cert_changed = True
                try:
                    file = open(self._certificate, "w")
                    file.write(certificate_file)
                    file.close()
                except OSError as err:
                    raise VimarApiError("Saving certificate failed: %s" % str(err))

                _LOGGER.debug("Downloaded Vimar CA certificate to: %s", self._certificate)

        return cert_changed

    def login(self):
        """Call login and store the session id."""

        # self._port = "444"
        loginurl = (
            "%s://%s:%s/vimarbyweb/modules/system/user_login.php?sessionid=&username=%s&password=%s&remember=0&op=login"
            % (
                self._schema,
                self._host,
                self._port,
                self._username,
                self._password,
            )
        )

        use_cert = self._certificate is not None and len(self._certificate) != 0
        # if first time, cert not exists
        if (
            self._schema == "https"
            and use_cert
            and self._certificate is not None
            and os.path.isfile(self._certificate) is False
        ):
            self.install_certificate()
        
        options = { "source": "login" }
        result = self._request(loginurl, options=options)

        if result is False and use_cert:  # if problem is of certificate, download it again
            curr_ex = self.request_last_exception
            curr_ex_str = str(curr_ex)
            # if certified not valid:
            # SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get issuer certificate (_ssl.c:1129)
            # SSLError(SSLError(136, '[X509: NO_CERTIFICATE_OR_CRL_FOUND] no certificate or crl found
            # if file not found
            # Could not find a suitable TLS CA certificate bundle, invalid path: rootCA.VIMAR.crt
            if "SSLError" in curr_ex_str or "TLS CA" in curr_ex_str:
                try:
                    # return downloaded only if changed, then, if is expired
                    cert_downloaded = self.install_certificate()
                    # self.request_last_exception = curr_ex
                    if cert_downloaded:
                        result = self._request(loginurl, options=options)
                except BaseException:
                    # self.request_last_exception = curr_ex
                    pass

        if result is not None:
            if result is False:
                raise VimarConnectionError(
                    "Error during login. Error: %s", self.request_last_exception
                )

            try:
                xml = self._parse_xml(result)
                if xml:
                    logincode = xml.find("result")
                    loginmessage = xml.find("message")
                else:
                    raise Exception("Login failed - check username, password and certificate path")
            except BaseException as err:
                raise VimarConnectionError(
                    "Error parsing login response: %s - %s", err, str(result)
                )

            if logincode is not None and logincode.text != "0":
                if loginmessage is not None:
                    raise VimarConfigError("Error during login: %s", loginmessage.text)
                else:
                    raise VimarConnectionError("Error during login. Code: %s", logincode.text)
            else:
                _LOGGER.info("Vimar login ok")
                loginsession = xml.find("sessionid")
                if loginsession is not None and loginsession.text != "":
                    _LOGGER.debug("Got a new Vimar Session id: %s", loginsession.text)
                    self._session_id = loginsession.text
                    self.set_session_id(self._session_key, loginsession.text)
                else:
                    _LOGGER.warning("Missing Session id in login response: %s", result)

        else:
            _LOGGER.warning("Empty Response from webserver login")

        return result

    def is_logged(self):
        """Check if session is available"""
        return self._session_id is not None

    def check_login(self):
        """Check if session is available - if not, aquire a new one."""
        if not self._session_id:
            self.login()

        return self._session_id is not None

    def check_session(self):
        """Check if session is valid - if not, clear session id."""
        # _LOGGER.error("calling url: " + url)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            # needs to be set to overcome:
            # 'Expect' => '100-continue'
            # otherwise header and payload is send in two requests if payload
            # is bigger then 1024byte
            "Expect": "",
        }

        post = ("sessionid=%s&" "op=getjScriptEnvironment&" "context=runtime") % self._session_id        
        
        options = { "source": "check_session" }
        return self._request_vimar(post, "vimarbyweb/modules/system/dpadaction.php", headers, options=options)

    def set_device_status(self, object_id, status, optionals="NO-OPTIONALS"):
        """Set a given status for one device."""
        post = (
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soapenv:Body><service-runonelement xmlns="urn:xmethods-dpadws">'
            "<payload>%s</payload>"
            "<hashcode>NO-HASHCODE</hashcode>"
            "<optionals>%s</optionals>"
            "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
            "<sessionid>%s</sessionid><waittime>10</waittime>"
            "<idobject>%s</idobject>"
            "<operation>SETVALUE</operation>"
            "</service-runonelement></soapenv:Body></soapenv:Envelope>"
        ) % (status, optionals, self._session_id, object_id)

        options = { "source": "set_device_status", "object_id": object_id, "new_status": status }
        response = self._request_vimar_soap(post, options=options)
        if response is not None and response is not False:

            payload = response.find(".//payload")

            # usually set_status should not return a payload
            if payload is not None:
                _LOGGER.warning(
                    "set_device_status returned a payload: "
                    + (payload.text or "unknown error")
                    + " from post request: "
                    + post
                )
                parsed_data = self._parse_sql_payload(payload.text)
                return parsed_data

        return None

    def get_optionals_param(self, state):
        """Return SYNCDB for climates states."""
        # if (state in ['setpoint', 'stagione', 'unita', 'centralizzato', 'funzionamento', 'temporizzazione', 'channel', 'source', 'global_channel']):
        if state in [
            "setpoint",
            "stagione",
            "unita",
            "temporizzazione",
            "channel",
            "source",
            "global_channel",
            "centralizzato",
        ]:
            return "SYNCDB"
        else:
            return "NO-OPTIONALS"

    # Device example:
    #   'room_id' => string '439' (length=3)
    #   'object_id' => string '768' (length=3)
    #   'object_name' => string 'DIMMER 11 WOHNZIMMER ERDGESCHOSS' (length=32)
    #   'ID' => string '768' (length=3)
    #   'NAME' => string 'DIMMER 11 WOHNZIMMER ERDGESCHOSS' (length=32)
    #   'DESCRIPTION' => string 'DIMMER 11 WOHNZIMMER ERDGESCHOSS' (length=32)
    #   'TYPE' => string 'BYMEIDX' (length=7)
    #   'MIN_VALUE' => string '434' (length=3)
    #   'MAX_VALUE' => string '391' (length=3)
    #   'CURRENT_VALUE' => string '' (length=0)
    #   'STATUS_ID' => string '-1' (length=2)
    #   'RENDERING_ID' => string '141' (length=3)
    #   'IMAGE_PATH' => string 'on_off/ICN_DV_LuceGenerale_on.png' (length=33)
    #   'IS_STOPPABLE' => string '0' (length=1)
    #   'MSP' => string '158' (length=3)
    #   'OPTIONALP' => string 'index_id=158|category=1' (length=23)
    #   'PHPCLASS' => string 'dpadVimarBymeIdx' (length=16)
    #   'COMMUNICATIONSECTION_ID' => string '6' (length=1)
    #   'IS_BOOLEAN' => string '0' (length=1)
    #   'WITH_PERMISSION' => string '1' (length=1)
    #   'TRACK_FLAG' => string '0' (length=1)
    #   'IS_REMOTABLE' => string '0' (length=1)
    #   'REMOTABLE_FILTER' => string '*' (length=1)
    #   'OWNED_BY' => string 'LOCAL' (length=5)
    #   'HAS_GRANT' => string '0' (length=1)
    #   'GRANT_HASHCODE' => string '' (length=0)
    #   'AUTOMATIC_REFRESH_FLAG' => string '0' (length=1)
    #   'TRACK_FLAG_ONREAD' => string '0' (length=1)
    #   'IS_DISCOVERABLE' => string '1' (length=1)

    #   'VALUES_TYPE' => string 'CH_Dimmer_Automation' (length=20)
    #   'ENABLE_FLAG' => string '1' (length=1)
    #   'IS_READABLE' => string '1' (length=1)
    #   'IS_WRITABLE' => string '1' (length=1)
    #   'IS_VISIBLE' => string '1' (length=1)

    def get_devices_info(
        self
    ):
        _LOGGER.debug("get_devices_info started")
        select = f"""SELECT r2.PARENTOBJ_ID AS room_id, oRoom.name as room_name, o2.ID AS object_id, o2.NAME AS object_name, o2.VALUES_TYPE as object_type, o2.OPTIONALP as object_optionalp, o3.Id as status_id, o3.NAME AS status_name, o3.OPTIONALP as status_range
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX"
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ" AND o3.NAME != ""
INNER JOIN DPADD_OBJECT oRoom ON r2.PARENTOBJ_ID = oRoom.ID AND oRoom.type = "GROUP"
WHERE  r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
ORDER BY r2.PARENTOBJ_ID, o2.ID, o3.Id
LIMIT %d, %d;"""
        options = { "source": "get_devices_info" }
        payload = self._request_vimar_sql_paginated(select, options)
        if len(payload) == 0:
            raise VimarApiError("No results for get_devices_info. Query: %s", query)
        self._last_devices_info = payload
        self._devices_update_date = self._devices_update_date + 1
        return payload

    def get_devices_status(
        self
    ):
        # get all data in about 0.2 s
        select = f"""SELECT o3.ID AS status_id, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT o3 
where o3.type IN ('BYMETVAL','BYMEOBJ') AND o3.NAME != ""
ORDER BY o3.ID 
LIMIT %d, %d;"""
        options = { "source": "get_devices_status" }
        options["timeout"] = self._status_timeout if self._status_timeout > 0 else self._timeout / 2
        options["retry_max_timeout"] = self._timeout if self._timeout > self._status_timeout else self._status_timeout
        options["retry_max_count"] = max(3, int(options["retry_max_timeout"] / (options["timeout"] * 0.5)))
        payload = self._request_vimar_sql_paginated(select, options)
        if len(payload) == 0:
            raise VimarApiError("No results for get_devices_info. Query: %s", query)
        self._last_devices_status = payload
        return payload
    

    def get_remote_devices(
        self,
        devices: dict[str, VimarDevice] | None = None,
    ):
        """Get all devices that can be triggered remotly (includes scenes)."""
        if devices is None:
            devices = {}
        if len(devices) == 0:
            _LOGGER.debug("get_remote_devices started")
        
        shared_session_id = self.get_session_id(self._session_key)
        if shared_session_id and shared_session_id != self._session_id:
            self._session_id = shared_session_id
            
        status = self.get_devices_status()
        if self._last_devices_status_cnt != len(status) or not self._fetch_only_status or len(devices) == 0:
            _LOGGER.debug(
                "Device status check: last_devices_status_cnt=%s, status_len=%s, "
                "fetch_only_status=%s, devices_len=%s",
                self._last_devices_status_cnt,
                len(status),
                self._fetch_only_status,
                len(devices),
            )
            devices_info = self.get_devices_info()
            devices.clear()
            self._generate_device_list(devices_info, devices)
            self._devices_update_date = self._devices_update_date + 1
            self._last_devices_status_cnt = len(status)
        
        for status_item in status:
            if status_item["status_id"] in self._devices_status_mapping:
                status_mapping = self._devices_status_mapping[status_item["status_id"]]
                deviceItem = devices[status_mapping["object_id"]]
                deviceItem["status"][status_mapping["status_name"]]["status_value"] = status_item["status_value"]
        
        self._fetch_only_status = True
        return devices

    def _generate_device_list(
        self, devices_info, devices: dict[str, VimarDevice] | None = None
    ):
        """Generate device list from given sql statements."""
        if devices_info is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in devices_info:
                deviceItem: VimarDevice | None = None
                if device["object_id"] not in devices:
                    optionalp = device["object_optionalp"]
                    #condition previus in query, now filter in memory
                    if optionalp is None or "category=" not in optionalp or "restricted" in optionalp:
                        continue
                    deviceItem = {
                        "room_ids": [],
                        "room_names": [],
                        "room_name": "",
                        "object_id": device["object_id"],
                        "object_name": device["object_name"],
                        "object_type": device["object_type"],
                        "status": {},
                        "device_type": "",
                        "device_class": "",
                        "device_friendly_name": "",
                        "icon": "",
                    }
                    devices[device["object_id"]] = deviceItem
                else:
                    # if object_id is already in the device list, we only update the state
                    deviceItem = devices[device["object_id"]]

                if "status_name" in device and device["status_name"] != "":
                    status_id = device["status_id"]
                    status_name = device["status_name"]
                    #saving mapping for fast update only values
                    self._devices_status_mapping[status_id] = {
                        "status_name": status_name,
                        "object_id": device["object_id"]
                    }
                    deviceItem["status"][status_name] = {
                        "status_id": status_id
                    }
                    if "status_range" in device:
                        deviceItem["status"][status_name]["status_range"] = device[
                            "status_range"
                        ]

                if device["room_name"] is not None and str(device["room_name"]) != "" and str(device["room_id"]) not in deviceItem["room_ids"]:
                    deviceItem["room_ids"].append(str(device["room_id"]))
                    deviceItem["room_names"].append(str(device["room_name"]))
                    deviceItem["room_name"] = deviceItem["room_names"][0]


    def _request_vimar_sql_paginated(self, select: str, options = None):
        """Execute SQL query with automatic pagination."""
        results = []
        limit = MAX_ROWS_PER_REQUEST
        start: int = 0

        while True:
            query = select % (start, limit)
            payload = self._request_vimar_sql(query, options)
            if not payload:
                raise VimarApiError("Error in Sql Paginated: %s - Request: %s", query, json.dumps(self.request_last_info))
                return None
            results.extend(payload)
            if len(payload) < limit:
                break
            start += limit
        return results

    def _request_vimar_sql(self, select, options = None):
        """Build sql request."""
        select = (
            select.replace("\r\n", " ")
            .replace("\n", " ")
            .replace('"', "&apos;")
            .replace("'", "&apos;")
        )

        # optionals is set to NO-OPTIONAL (singular) for sql only
        post = (
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soapenv:Body><service-databasesocketoperation xmlns="urn:xmethods-dpadws">'
            "<payload>NO-PAYLOAD</payload>"
            "<hashcode>NO-HASCHODE</hashcode>"
            "<optionals>NO-OPTIONAL</optionals>"
            "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
            "<sessionid>%s</sessionid>"
            "<waittime>5</waittime>"
            "<function>DML-SQL</function><type>SELECT</type>"
            "<statement>%s</statement><statement-len>%d</statement-len>"
            "</service-databasesocketoperation></soapenv:Body></soapenv:Envelope>"
        ) % (self._session_id, select, len(select))

        response = self._request_vimar_soap(post, options)
        if response is not None and response is not False:

            # print('Response XML', xmlTree.tostring(response, method='xml'), 'POST: ', post)

            payload = response.find(".//payload")
            if payload is not None:
                parsed_data = self._parse_sql_payload(payload.text)

                if parsed_data is None:
                    _LOGGER.warning(
                        "Received invalid data from SQL: "
                        + ElementTree.tostring(response, encoding="unicode")
                        + " from post: "
                        + post
                        + " - LastRequest: "
                        + json.dumps(self.request_last_info)
                    )

                return parsed_data
            else:
                _LOGGER.warning("Empty payload from SQL. Request %s", json.dumps(self.request_last_info))
                return None
        elif response is None:
            _LOGGER.warning("Unparseable response from SQL. Request %s", json.dumps(self.request_last_info))
            _LOGGER.info("Errorous SQL: %s", select)
        return None

    def _parse_sql_payload(self, string):
        """Split string payload into dictionary array."""
        # DONE: we need to move parseSQLPayload over to pyton
        # Example payload string:
        # Response: DBMG-000
        # NextRows: 2
        # Row000001: 'MAIN_GROUPS'
        # Row000002: '435,439,454,458,473,494,505,532,579,587,605,613,628,641,649,660,682,690,703,731,739,752,760,794,802,817,828,836,868,883,898,906,921,929,1777,1778'
        # should be MAIN_GROUPS =
        # '435,439,454,458,473,494,505,532,579,587,605,613,628,641,649,660,682,690,703,731,739,752,760,794,802,817,828,836,868,883,898,906,921,929,1777,1778'

        return_list = []

        try:
            lines = string.split("\n")
            keys = []
            for line in lines:
                if line:
                    if line.find(":") == -1:
                        raise Exception("Missing :-character in response line: %s" % line)

                    # split prefix from values
                    prefix, values = line.split(":", 1)
                    prefix = prefix.strip()

                    # skip unused prefixes
                    if prefix in ["Response", "NextRows"]:
                        pass
                    else:
                        # remove outer quotes, split each quoted string
                        values = values.strip()[1:-1].split("','")

                        idx = 0
                        row_dict = {}
                        for value in values:
                            # line with Row000001 holds the name of the fields
                            if prefix == "Row000001":
                                keys.append(value)
                            else:
                                # all other rows have values
                                row_dict[keys[idx]] = value
                                idx += 1

                        if row_dict and len(row_dict) > 0:
                            return_list.append(row_dict)

        except BaseException as err:
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            _, _, exc_tb = sys.exc_info()
            _LOGGER.error(
                "Error parsing SQL: %s in line: %d - payload: %s - request: %s"
                % (err, exc_tb.tb_lineno if exc_tb is not None else 0, string, json.dumps(self.request_last_info))
            )
            # enforce relogin
            #if already logged from other class (from configuration for example), use the new session key
            shared_session_id = self.get_session_id(self._session_key)
            if shared_session_id and shared_session_id != self._session_id:
                self._session_id = shared_session_id
            else:
                old_info = self.request_last_info
                _LOGGER.info("Start to relogin..")
                self._session_id = None
                self.login()
                self.request_last_info = old_info
            # raise VimarConnectionError(
            #     "Error parsing SQL: %s in line: %d - payload: %s" % (err, exc_tb.tb_lineno, string))

        return return_list

    def _request_vimar_soap(self, post, options=None):
        headers = {
            "SOAPAction": "dbSoapRequest",
            "SOAPServer": "",
            # 'X-Requested-With' => 'XMLHttpRequest',
            "Content-Type": 'text/xml; charset="UTF-8"',
            # needs to be set to overcome:
            # 'Expect' => '100-continue'
            # otherwise header and payload is send in two requests if payload
            # is bigger then 1024byte
            "Expect": "",
        }

        return self._request_vimar(post, "cgi-bin/dpadws", headers, options)

    def _request_vimar(self, post, path, headers, options=None):
        """Prepare call to vimar webserver."""
        url = "%s://%s:%s/%s" % (self._schema, self._host, self._port, path)

        # _LOGGER.error("calling url: " + url)
        # _LOGGER.info("in _request_vimar")
        # _LOGGER.info(post)
        response = self._request(url, post, headers, False, options)
        if response is not None and response is not False:
            responsexml = self._parse_xml(response)
            # _LOGGER.info("responsexml: ")
            # _LOGGER.info(responsexml)

            return responsexml

        return response

    def _parse_xml(self, xml):
        """Parse xml response from webserver to array."""
        try:
            root = xmlTree.fromstring(xml)
        except BaseException as err:
            _LOGGER.error("Error parsing XML: %s - LastRequest %s", err, json.dumps(self.request_last_info))
            _LOGGER.debug("Problematic XML: %s", str(xml))

        else:
            return root
        return None

    request_last_info = {}
    request_last_exception: BaseException | None = None
    _last_request_successful = True

    def _request(self, url, post=None, headers=None, check_ssl=False, options=None):
        """Call web server using post variables."""
        options = options or {}
        info = {}
        self.request_last_info = info
        timeout = options.get("timeout", self._timeout)
        attempt_totals_count = options.get("retry_max_count", 3) if self._last_request_successful else 1
        attempt_totals_count = attempt_totals_count if attempt_totals_count > 0 else 1
        info["source"] = options.get("source", "")
        info["url"] = url
        info["result"] = False
        options_str = json.dumps(options)
        _LOGGER.debug("Begin HTTP Request to %s. Options: %s", url, options_str)

        first_request_start = time.perf_counter()
        for attempt in range(attempt_totals_count):
            request_start = time.perf_counter()            
            info["retry_attempt"] = attempt
            try:
                self._last_request_successful = False
                # connection, read timeout
                timeouts = (timeout / 2, timeout)

                if self._certificate is not None:
                    check_ssl = self._certificate
                else:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    global SSL_IGNORED
                    if not SSL_IGNORED:
                        _LOGGER.debug("Request ignores ssl certificate")
                        SSL_IGNORED = True

                with requests.Session() as s:
                    s.mount("http://" if self._schema == "http" else "https://", HTTPAdapter())
                    # s.verify = False

                    if post is None:
                        response = s.get(url, headers=headers, verify=check_ssl, timeout=timeouts)
                    else:
                        response = s.post(
                            url,
                            data=post,
                            headers=headers,
                            verify=check_ssl,
                            timeout=timeouts,
                        )

                request_time = round(time.perf_counter() - request_start, 2)
                request_total_time = round(time.perf_counter() - first_request_start, 2)
                info["total_time"] = request_total_time
                info["request_time"] = request_time

                # If the response was successful, no Exception will be raised
                response.raise_for_status()
                self._last_request_successful = True
                if attempt > 0:
                    _LOGGER.info("HTTP request success after retry. Total retry time %.2f s, Request executed in %.2f seconds. Attempt %d/%d. Options: %s", request_total_time, request_time, attempt + 1, attempt_totals_count, options_str)

                info["error"] = None
                info["result"] = True

            except HTTPError as http_err:
                self.request_last_exception = http_err
                info["error"] = str(http_err)
                _LOGGER.error("HTTP error occurred: %s - Options: %s", str(http_err), options_str)
                return False
            # except ReadTimeoutError:
            except requests.exceptions.Timeout as ex:
                self.request_last_exception = ex
                info["error"] = str(ex)
                request_time = round(time.perf_counter() - request_start, 2)
                request_total_time = round(time.perf_counter() - first_request_start, 2)
                can_retry = True if attempt + 1 < attempt_totals_count else False
                if can_retry:
                    retry_max_timeout = options.get("retry_max_timeout", 0)
                    if retry_max_timeout > 0 and request_total_time > retry_max_timeout:
                        can_retry = False
                if can_retry:
                    _LOGGER.debug("HTTP timeout occurred in %.2f seconds (total %.2f) (attempt %d/%d).%s Retrying request... Error: %s - Options: %s", request_time, request_total_time, attempt + 1, attempt_totals_count, str(ex), options_str)
                    continue
                _LOGGER.error("HTTP timeout after %.2f seconds (last request %.2f) (attempt %d/%d). Error: %s - Options: %s", request_total_time, request_time, attempt + 1, attempt_totals_count, str(ex), options_str)
                return False
            except BaseException as err:
                self.request_last_exception = err
                info["error"] = str(err)
                _LOGGER.error("Error occurred: %s - Options: %s", str(err), options_str)
                return False
            else:
                _LOGGER.debug("HTTP Request to %s completed. Info: %s", url, json.dumps(info))
                info["response"] = response.text                
                return response.text
        
        raise Exception("Request error: exitede from retry")


class VimarProject:
    """Container that holds all vimar devices and its states."""

    _devices: dict[str, VimarDevice] = {}
    _link: VimarLink
    _platforms_exists = {}
    global_channel_id = None
    _device_customizer_action = None
    _devices_update_date = 0

    def __init__(self, link: VimarLink, device_customizer_action=None):
        """Create new container to hold all states."""
        self._link = link
        self._device_customizer_action = device_customizer_action

    @property
    def devices(self):
        """Return all devices in current project."""
        return self._devices

    def update(self, forced=False):
        """Get all devices from the vimar webserver, if object list is already there, only update states."""
        if self._devices is None:
            self._devices = {}
        # DONE - only update the state - not the actual devices, so we do not need to parse device types again
        if (forced is not None and forced is True):
            self._link._fetch_only_status = False

        self._devices = self._link.get_remote_devices(self._devices)

        # for now we run parse device types and set classes after every update
        if self._devices_update_date != self._link._devices_update_date:
            self.check_devices()
            self._devices_update_date = self._link._devices_update_date

        return self._devices

    def check_devices(self):
        """On first run of update, all device types and names are parsed to determin the correct platform."""
        if self._devices is not None and len(self._devices) > 0:
            for device_id, device in self._devices.items():
                self.parse_device_type(device)
            if _LOGGER_isDebug:
                _LOGGER.debug("check_devices end. Devices: %s", str(self._devices))
            return True
        else:
            return False

    def get_by_device_type(self, platform):
        """Do dictionary comprehension."""
        return {k: v for (k, v) in self._devices.items() if v["device_type"] == platform}

    def platform_exists(self, platform):
        """Check if there are devices for a given platform."""
        if platform in self._platforms_exists:
            return self._platforms_exists[platform]
        else:
            return False

    def parse_device_type(self, device):
        """Split up devices into supported groups based on their names."""
        device_type = DEVICE_TYPE_OTHERS
        device_class = None
        icon = "mdi:home-assistant"

        if device["object_type"] == "CH_Main_Automation":
            # if device["object_name"].find("VENTILATOR") != -1 or device["object_name"].find("FANCOIL") != -1 or device["object_name"].find("VENTILATORE") != -1:
            # if "VENTILATOR" in device["object_name"] or "FANCOIL" in device["object_name"] or "VENTILATORE" in device["object_name"]:
            if any(x in device["object_name"].upper() for x in ["VENTILATOR", "FANCOIL"]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:fan", "mdi:fan-off"]

            # elif device["object_name"].find("LAMPE") != -1:
            elif any(x in device["object_name"].upper() for x in ["LAMPE"]):
                device_type = DEVICE_TYPE_LIGHTS
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:lightbulb-on", "mdi:lightbulb-off"]
            # elif device["object_name"].find("STECKDOSE") != -1 or device["object_name"].find("PULSANTE") != -1:
            # elif "STECKDOSE" in device["object_name"] or "PULSANTE" in device["object_name"]:
            elif any(x in device["object_name"].upper() for x in ["STECKDOSE", "PULSANTE"]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_OUTLET
                icon = ["mdi:power-plug", "mdi:power-plug-off"]
            # elif device["object_name"].find("HEIZUNG") != -1:
            # elif "HEIZUNG" in device["object_name"].upper():
            elif any(x in device["object_name"].upper() for x in ["HEIZUNG", "HEIZKÖRPER"]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:radiator", "mdi:radiator-off"]
            # elif device["object_name"].find(" IR ") != -1:
            # elif " IR " in device["object_name"].upper():
            elif any(x in device["object_name"].upper() for x in [" IR "]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:motion-sensor", "mdi:motion-sensor-off"]

                _LOGGER.debug(
                    "IR Sensor object returned from web server: "
                    + device["object_type"]
                    + " / "
                    + device["object_name"]
                )
                _LOGGER.debug("IR Sensor object has states: " + str(device["status"]))

            else:
                # fallback to lights
                device_type = DEVICE_TYPE_LIGHTS
                icon = "mdi:ceiling-light"

        elif device["object_type"] in [
            "CH_KNX_GENERIC_ONOFF",
            "CH_KNX_GENERIC_TIME_S",
            "CH_KNX_RELE",
            "CH_KNX_GENERIC_ENABLE",
            "CH_KNX_GENERIC_RESET",
        ]:
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20

            device_type = DEVICE_TYPE_SWITCHES
            device_class = DEVICE_CLASS_SWITCH
            # icon = ["mdi:electric-switch", "mdi:electric-switch-closed"]
            icon = ["mdi:toggle-switch", "mdi:toggle-switch-closed"]

            # _LOGGER.debug(
            #     "KNX object returned from web server: "
            #     + device["object_type"]
            #     + " / "
            #     + device["object_name"])
            # _LOGGER.debug(
            #     "KNX object has states: "
            #     + str(device["status"]))

        elif device["object_type"] in [
            "CH_Dimmer_Automation",
            "CH_Dimmer_RGB",
            "CH_Dimmer_White",
            "CH_Dimmer_Hue",
        ]:
            device_type = DEVICE_TYPE_LIGHTS
            icon = ["mdi:speedometer", "mdi:speedometer-slow"]

        elif device["object_type"] in [
            "CH_ShutterWithoutPosition_Automation",
            "CH_ShutterBlindWithoutPosition_Automation",
            "CH_Shutter_Automation",
            "CH_Shutter_Slat_Automation",
            "CH_ShutterBlind_Automation",
        ]:
            # if device["object_name"].find("F-FERNBEDIENUNG") != -1:
            # if device["object_name"].find("F-FERNBEDIENUNG") != -1:
            if any(x in device["object_name"].upper() for x in ["FERNBEDIENUNG"]):
                device_type = DEVICE_TYPE_COVERS
                device_class = DEVICE_CLASS_WINDOW
                icon = ["mdi:window-closed-variant", "mdi:window-open-variant"]
            else:
                # could be: shade, blind, window
                # see: https://www.home-assistant.io/integrations/cover/
                device_type = DEVICE_TYPE_COVERS
                device_class = DEVICE_CLASS_SHUTTER
                icon = ["mdi:window-shutter", "mdi:window-shutter-open"]

        elif device["object_type"] in [
            "CH_Clima",
            "CH_HVAC_NoZonaNeutra",
            "CH_HVAC_RiscaldamentoNoZonaNeutra",
            "CH_Fancoil",
            "CH_HVAC",
        ]:
            device_type = DEVICE_TYPE_CLIMATES
            icon = "mdi:thermometer-lines"

            _LOGGER.debug(
                "Climate object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"]
            )
            _LOGGER.debug("Climate object has states: " + str(device["status"]))

        elif device["object_type"] == "CH_Scene":
            device_type = DEVICE_TYPE_SCENES
            # device_class = DEVICE_CLASS_SWITCH
            # icon = "mdi:google-pages"
            icon = "hass:palette"

            _LOGGER.debug(
                "Scene returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"]
            )
            _LOGGER.debug("Scene object has states: " + str(device["status"]))

        elif device["object_type"] in [
            "CH_Misuratore",
            "CH_Carichi_Custom",
            "CH_Carichi",
            "CH_Carichi_3F",
            "CH_KNX_GENERIC_POWER_KW",
        ]:
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_POWER
            # icon = "mdi:battery-charging-high"
            icon = "mdi:chart-bell-curve-cumulative"

            # _LOGGER.debug(
            #     "Sensor object returned from web server: "
            #     + device["object_type"]
            #     + " / "
            #     + device["object_name"])
            # _LOGGER.debug(
            #     "Sensor object has states: "
            #     + str(device["status"]))
        elif any(x in device["object_type"].upper() for x in ["CH_Contatore_"]):
            device_type = DEVICE_TYPE_SENSORS
            # icon = "mdi:battery-charging-high"
            icon = "mdi:pulse"

        elif device["object_type"] in ["CH_KNX_GENERIC_TEMPERATURE_C"]:
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_TEMPERATURE
            icon = "mdi:thermometer"
        elif device["object_type"] in ["CH_KNX_GENERIC_WINDSPEED"]:
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_PRESSURE
            icon = "mdi:windsock"
        elif device["object_type"] in ["CH_WEATHERSTATION"]:
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20
            device_type = DEVICE_TYPE_SENSORS
            icon = "mdi:weather-partly-snowy-rainy"

        elif device["object_type"] in ["CH_Audio"]:
            device_type = DEVICE_TYPE_MEDIA_PLAYERS
            icon = ["mdi:radio", "mdi:radio-off"]

            _LOGGER.debug(
                "Audio object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"]
            )
            _LOGGER.debug("Audio object has states: " + str(device["status"]))

        elif device["object_type"] in [
            "CH_SAI",
            "CH_Event",
            "CH_KNX_GENERIC_TIMEPERIODMIN",
        ]:
            _LOGGER.debug(
                "Unsupported object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"]
            )
            _LOGGER.debug("Unsupported object has states: " + str(device["status"]))
        else:
            _LOGGER.warning(
                "Unknown object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"]
            )
            _LOGGER.debug("Unknown object has states: " + str(device["status"]))

        object_name = device["object_name"]
        friendly_name = self.format_name(object_name)

        # see https://github.com/h4de5/home-assistant-vimar/pull/31
        # vimar_name = device["object_name"]
        # DONE - make format name configurable
        # object_name = self.format_name(device["object_name"])

        # for device_override in self._device_overrides:
        #     filter = device_override.get("filter_vimar_name", "").upper()
        #     match = filter == "*" or vimar_name.upper() == filter
        #     # _LOGGER.debug("Overriding: filter: '" + filter + "' - vimar_name: '" + vimar_name + "' - Match: " + str(match))
        #     if not match:
        #         continue
        #     if device_override.get("object_name_as_vimar"):
        #         object_name = vimar_name.title().strip()
        #     if device_override.get("device_type", device_type) != device_type:
        #         _LOGGER.debug(
        #             "Overriding device_type: object_name: '"
        #             + object_name
        #             + "' - device_type: '"
        #             + str(device_type)
        #             + "' -> '"
        #             + str(device_override.get("device_type"))
        #             + "'"
        #         )
        #         device_type = str(device_override.get("device_type"))
        #     if device_override.get("device_class", device_class) != device_class:
        #         _LOGGER.debug(
        #             "Overriding device_class: object_name: '"
        #             + object_name
        #             + "' - device_class: '"
        #             + str(device_class)
        #             + "' -> '"
        #             + str(device_override.get("device_class"))
        #             + "'"
        #         )
        #         device_class = str(device_override.get("device_class"))
        #     if device_override.get("icon") is not None:
        #         oldIcon = icon
        #         icon = device_override.get("icon")
        #         if isinstance(icon, str) and "," in icon:
        #             icon = icon.split(",")
        #         if isinstance(icon, str) and icon == "":
        #             icon = None
        #         if not str(icon) == str(oldIcon):
        #             _LOGGER.debug(
        #                 "Overriding icon: object_name: '"
        #                 + object_name
        #                 + "' - icon: '"
        #                 + str(oldIcon)
        #                 + "' -> '"
        #                 + str(icon)
        #                 + "'"
        #             )

        # send https://github.com/h4de5/home-assistant-vimar/pull/31

        device["device_type"] = device_type
        device["device_class"] = device_class
        device["device_friendly_name"] = friendly_name
        device["icon"] = icon
        # device["object_name"] = object_name

        if self._device_customizer_action:
            self._device_customizer_action(device)

        # reload device_type: can be changed from customizer
        device_type = device["device_type"]

        # _LOGGER.debug("Object returned from web server: " + device["object_type"] + " / " + device["object_name"])
        # _LOGGER.debug("Object has states: " + str(device["status"]))

        if device_type in self._platforms_exists:
            self._platforms_exists[device_type] += 1
        else:
            self._platforms_exists[device_type] = 1

    def format_name(self, name):
        """Format device name to get rid of unused terms."""
        parts = name.split(" ")
        level_name = ""
        room_name = ""
        device_type = ""
        entity_number = ""

        if len(parts) > 0:
            if len(parts) >= 4:
                device_type = parts[0]
                entity_number = parts[1]
                room_name = parts[2]
                level_name = parts[3]

                for i in range(4, len(parts)):
                    level_name += " " + parts[i]
            elif len(parts) >= 2:
                device_type = parts[0]
                entity_number = ""
                room_name = ""
                level_name = parts[1]

                for i in range(2, len(parts)):
                    level_name += " " + parts[i]
            else:
                # _LOGGER.debug(
                #     "Found a device with an uncommon naming schema: %s", name)

                device_type = parts[0]
                entity_number = ""
                room_name = ""
                # level_name = 'LEVEL'
                level_name = ""

                for i in range(2, len(parts)):
                    level_name += " " + parts[i]

        device_type = device_type.replace("LUCE", "")
        device_type = device_type.replace("TAPPARELLA", "")

        if device_type != "LICHT":
            device_type = device_type.replace("LICHT", "")

        device_type = device_type.replace("ROLLLADEN", "")
        device_type = device_type.replace("F-FERNBEDIENUNG", "FENSTER")
        device_type = device_type.replace("VENTILATORE", "")
        device_type = device_type.replace("VENTILATOR", "")
        device_type = device_type.replace("STECKDOSE", "")
        device_type = device_type.replace("THERMOSTAT", "")

        if len(level_name) != 0:
            level_name += " "
        if len(room_name) != 0:
            room_name += " "
        if len(device_type) != 0:
            device_type += " "

        # Erdgeschoss Wohnzimmer Licht 3
        name = "%s%s%s%s" % (level_name, room_name, device_type, entity_number)

        # change case
        return name.title().strip()
