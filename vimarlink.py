"""Connection to vimar web server."""

import logging
import sys
# for communicating with vimar webserver
import xml.etree.cElementTree as xmlTree
from xml.etree import ElementTree
import requests
from requests.exceptions import HTTPError

from .const import (
    DEVICE_TYPE_LIGHTS,
    DEVICE_TYPE_COVERS,
    DEVICE_TYPE_SWITCHES,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_MEDIA_PLAYERS,
    # DEVICE_TYPE_SCENES,
    # DEVICE_TYPE_FANS,
    DEVICE_TYPE_SENSORS,
    DEVICE_TYPE_OTHERS)

_LOGGER = logging.getLogger(__name__)
MAX_ROWS_PER_REQUEST = 300

# from homeassistant/components/switch/__init__.py
DEVICE_CLASS_OUTLET = "outlet"
DEVICE_CLASS_SWITCH = "switch"
# from homeassistant/components/cover/__init__.py
DEVICE_CLASS_SHUTTER = "shutter"
DEVICE_CLASS_WINDOW = "window"
# from homeassistant/const.py
DEVICE_CLASS_POWER = "power"


class VimarApiError(Exception):
    """Vimar API General Exception."""

    err_args = []

    def __init__(self, *args, **kwargs):
        """Init a default Vimar api exception."""
        self.err_args = args
        super().__init__(*args)

    def __str__(self):
        """Stringify exception text."""
        return f'{self.__class__.__name__}: {self.err_args[0]}' % self.err_args[1:]


class VimarConfigError(VimarApiError):
    """Vimar API Configuration Exception."""

    pass


class VimarConnectionError(VimarApiError):
    """Vimar API Connection Exception."""

    pass


class VimarLink():
    """Link to communicate with the Vimar webserver."""

    # private
    _host = ''
    _schema = ''
    _port = 443
    _username = ''
    _password = ''
    _session_id = None
    _room_ids = None
    _certificate = None
    _timeout = 6

    def __init__(
            self,
            schema=None,
            host=None,
            port=None,
            username=None,
            password=None,
            certificate=None,
            timeout=None):
        """Prepare connections instance for vimar webserver."""
        _LOGGER.info("Vimar link initialized")

        if schema is not None:
            VimarLink._schema = schema
        if host is not None:
            VimarLink._host = host
        if port is not None:
            VimarLink._port = port
        if username is not None:
            VimarLink._username = username
        if password is not None:
            VimarLink._password = password
        if certificate is not None:
            VimarLink._certificate = certificate
        if timeout is not None:
            VimarLink._timeout = timeout

    def install_certificate(self):
        """Download the CA certificate from the web server to be used for the next calls."""
        # temporarily disable certificate requests
        if len(self._certificate) != 0:
            temp_certificate = self._certificate
            self._certificate = None

            temp_certificate = "%s://%s:%s/vimarbyweb/modules/vimar-byme/script/rootCA.VIMAR.crt" % (
                VimarLink._schema, VimarLink._host, VimarLink._port)
            certificate_file = self._request(temp_certificate)

            if certificate_file is None:
                raise VimarConnectionError("Certificate download failed")

            # get it back
            self._certificate = temp_certificate

            try:
                file = open(self._certificate, "w")
                file.write(certificate_file)
                file.close()

            except IOError as err:
                raise VimarApiError("Saving certificate failed: %s" % err)

            _LOGGER.debug("Downloaded Vimar CA certificate to: %s",
                          self._certificate)

        return True

    def login(self):
        """Call login and store the session id."""
        loginurl = "%s://%s:%s/vimarbyweb/modules/system/user_login.php?sessionid=&username=%s&password=%s&remember=0&op=login" % (
            VimarLink._schema, VimarLink._host, VimarLink._port, VimarLink._username, VimarLink._password)

        result = self._request(loginurl)

        if result is not None:
            try:
                xml = self._parse_xml(result)
                logincode = xml.find('result')
                loginmessage = xml.find('message')
            except BaseException as err:
                raise VimarConnectionError("Error parsing login response: %s - %s", err, str(result))

            if logincode is not None and logincode.text != "0":
                if loginmessage is not None:
                    raise VimarConfigError("Error during login: %s", loginmessage.text)
                else:
                    raise VimarConnectionError("Error during login. Code: %s", logincode.text)
            else:
                _LOGGER.info("Vimar login ok")
                loginsession = xml.find('sessionid')
                if loginsession.text != "":
                    _LOGGER.debug("Got a new Vimar Session id: %s",
                                  loginsession.text)
                    VimarLink._session_id = loginsession.text
                else:
                    _LOGGER.warning(
                        "Missing Session id in login response: %s", result)

        else:
            _LOGGER.warning("Empty Response from webserver login")

        return result

    def check_login(self):
        """Check if session is available - if not, aquire a new one."""
        if VimarLink._session_id is None:
            self.login()

        return VimarLink._session_id is not None

    def set_device_status(self, object_id, status, optionals="NO-OPTIONALS"):
        """Set a given status for one device."""
        post = ("<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">"
                "<soapenv:Body><service-runonelement xmlns=\"urn:xmethods-dpadws\">"
                "<payload>%s</payload>"
                "<hashcode>NO-HASHCODE</hashcode>"
                "<optionals>%s</optionals>"
                "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
                "<sessionid>%s</sessionid><waittime>10</waittime>"
                "<idobject>%s</idobject>"
                "<operation>SETVALUE</operation>"
                "</service-runonelement></soapenv:Body></soapenv:Envelope>") % (
            status,
            optionals,
            VimarLink._session_id,
            object_id)

        response = self._request_vimar(post)
        if response is not None and response is not False:

            payload = response.find('.//payload')

            # usually set_status should not return a payload
            if payload is not None:
                _LOGGER.warning(
                    "set_device_status returned a payload: "
                    + payload.text
                    + " from post request: "
                    + post)
                parsed_data = self._parse_sql_payload(payload.text)
                return parsed_data

        return None

    def get_optionals_param(self, state):
        """Return SYNCDB for climates states."""
        if (state in ['setpoint', 'stagione', 'unita', 'temporizzazione', 'channel']):
            return 'SYNCDB'
        else:
            return 'NO-OPTIONALS'

    def get_device_status(self, object_id):
        """Get attribute status for a single device."""
        status_list = {}

# , o3.OPTIONALP AS status_range
        select = """SELECT o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT_RELATION r3
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ"
WHERE r3.PARENTOBJ_ID IN (%s) AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
ORDER BY o3.ID;""" % (object_id)

        payload = self._request_vimar_sql(select)
        if payload is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in payload:
                if status_list == {}:
                    status_list = {
                        device['status_name']: {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            # 'status_range': device['status_range'],
                        }
                    }
                else:
                    if device['status_name'] != '':
                        status_list[device['status_name']] = {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            # 'status_range': device['status_range'],
                        }

            return status_list

        return {}

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

    def get_paged_results(self, method, objectlist={}, start=0):
        """Page results from a method automatically."""
        # define a page size
        limit = MAX_ROWS_PER_REQUEST

        if callable(method):
            objectlist, state_count = method(objectlist, start, limit)
            # if method returns excatly page size results - we check for another page
            if state_count == limit:
                objectlist, state_count = self.get_paged_results(method, objectlist, start + state_count)
            return objectlist, start + state_count
        else:
            raise VimarApiError("Calling invalid method for paged results: %s", method)

    def get_room_devices(self, devices={}, start: int = None, limit: int = None):
        """Load all devices that belong to a room."""
        if VimarLink._room_ids is None:
            return None

        start, limit = self._sanitaze_limits(start, limit)

        _LOGGER.debug("get_room_devices started - from %d to %d", start, start + limit)

        select = """SELECT GROUP_CONCAT(r2.PARENTOBJ_ID) AS room_ids, o2.ID AS object_id,
o2.NAME AS object_name, o2.VALUES_TYPE as object_type,
o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX"
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ" AND o3.NAME != ""
WHERE r2.PARENTOBJ_ID IN (%s) AND r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
GROUP BY o2.ID, o2.NAME, o2.VALUES_TYPE, o3.ID, o3.NAME, o3.CURRENT_VALUE
LIMIT %d, %d;""" % (VimarLink._room_ids, start, limit)

        # o3.OPTIONALP AS status_range
        # AND o3.OPTIONALP IS NOT NULL
        #
        # AND
        # o2.ENABLE_FLAG = "1" AND o2.IS_READABLE = "1" AND o2.IS_WRITABLE =
        # "1" AND o2.IS_VISIBLE = "1"

        return self._generate_device_list(select, devices)

    def get_remote_devices(self, devices={}, start: int = None, limit: int = None):
        """Get all devices that can be triggered remotly (includes scenes)."""
        if len(devices) == 0:
            _LOGGER.debug("get_remote_devices started - from %d to %d", start, start + limit)

        start, limit = self._sanitaze_limits(start, limit)

        select = """SELECT '' AS room_ids, o2.id AS object_id, o2.name AS object_name, o2.VALUES_TYPE AS object_type,
o2.NAME AS object_name, o2.VALUES_TYPE AS object_type,
o3.ID AS status_id, o3.NAME AS status_name, o3.OPTIONALP as status_range, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT AS o2
INNER JOIN (SELECT CLASSNAME,IS_EVENT,IS_EXECUTABLE FROM DPAD_WEB_PHPCLASS) AS D_WP ON o2.PHPCLASS=D_WP.CLASSNAME
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type IN ('BYMETVAL','BYMEOBJ') AND o3.NAME != ""
WHERE o2.OPTIONALP NOT LIKE "%%restricted%%" AND o2.IS_VISIBLE=1 AND o2.OWNED_BY!="SYSTEM" AND o2.OPTIONALP LIKE "%%category=%%"
LIMIT %d, %d;""" % (start, limit)

        return self._generate_device_list(select, devices)

    def _sanitaze_limits(self, start: int, limit: int):
        """Check for sane values in start and limit."""
        # upper limit is hardcoded - too many results will kill webserver
        if limit is None or limit > MAX_ROWS_PER_REQUEST or limit <= 0:
            limit = MAX_ROWS_PER_REQUEST
        if start is None or start < 0:
            start = 0
        return start, limit

    def _generate_device_list(self, select, devices={}):
        """Generate device list from given sql statements."""
        payload = self._request_vimar_sql(select)
        if payload is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in payload:
                if device['object_id'] not in devices:
                    devices[device['object_id']] = {
                        'room_ids': device['room_ids'].split(','),
                        'object_id': device['object_id'],
                        'object_name': device['object_name'],
                        'object_type': device['object_type'],
                        'status': {
                            device['status_name']: {
                                'status_id': device['status_id'],
                                'status_value': device['status_value'],
                                'status_range': device['status_range'],
                            }
                        }
                    }
                else:
                    # if object_id is already in the device list, we only update the state
                    if device['status_name'] != '':
                        devices[device['object_id']]['status'][device['status_name']] = {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            'status_range': device['status_range'],
                        }
            return devices, len(payload)

        return None

    def get_room_ids(self):
        """Load main rooms - later used in get_room_devices."""
        if VimarLink._room_ids is not None:
            return VimarLink._room_ids

        _LOGGER.debug("get_main_groups start")

        select = """SELECT GROUP_CONCAT(o1.id) as MAIN_GROUPS FROM DPADD_OBJECT o0
INNER JOIN DPADD_OBJECT_RELATION r1 ON o0.ID = r1.PARENTOBJ_ID AND r1.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
INNER JOIN DPADD_OBJECT o1 ON r1.CHILDOBJ_ID = o1.ID AND o1.type = "GROUP"
WHERE o0.NAME = "_DPAD_DBCONSTANT_GROUP_MAIN";"""

        payload = self._request_vimar_sql(select)
        if payload is not None:
            VimarLink._room_ids = payload[0]['MAIN_GROUPS']
            _LOGGER.info("get_room_ids ends - found %d rooms", len(VimarLink._room_ids.split(',')))

            return VimarLink._room_ids
        else:
            return None

    def _request_vimar_sql(self, select):
        """Build sql request."""
        select = select.replace('\r\n', ' ').replace(
            '\n', ' ').replace('"', '&apos;').replace('\'', '&apos;')

        post = ("<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">"
                "<soapenv:Body><service-databasesocketoperation xmlns=\"urn:xmethods-dpadws\">"
                "<payload>NO-PAYLOAD</payload>"
                "<hashcode>NO-HASCHODE</hashcode>"
                "<optionals>NO-OPTIONAL</optionals>"
                "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
                "<sessionid>%s</sessionid>"
                "<waittime>5</waittime>"
                "<function>DML-SQL</function><type>SELECT</type>"
                "<statement>%s</statement><statement-len>%d</statement-len>"
                "</service-databasesocketoperation></soapenv:Body></soapenv:Envelope>") % (
            VimarLink._session_id, select, len(select))

        response = self._request_vimar(post)
        if response is not None and response is not False:

            payload = response.find('.//payload')
            if payload is not None:
                parsed_data = self._parse_sql_payload(payload.text)

                if parsed_data is None:
                    _LOGGER.warning(
                        "Received invalid data from SQL: "
                        + ElementTree.tostring(
                            response,
                            encoding='unicode')
                        + " from post: "
                        + post)

                return parsed_data
            else:
                _LOGGER.warning("Empty payload from SQL")
                return None
        elif response is None:
            _LOGGER.warning("Unparseable response from SQL")
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
            lines = string.split('\n')
            keys = []
            for line in lines:
                if line:
                    if line.find(':') == -1:
                        raise Exception('Missing :-character in response line: %s' % line)

                    # split prefix from values
                    prefix, values = line.split(':', 1)
                    prefix = prefix.strip()

                    # skip unused prefixes
                    if prefix in ['Response', 'NextRows']:
                        pass
                    else:
                        # remove outer quotes, split each quoted string
                        values = values.strip()[1:-1].split('\',\'')

                        idx = 0
                        row_dict = {}
                        for value in values:
                            # line with Row000001 holds the name of the fields
                            if prefix == 'Row000001':
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
            raise VimarConnectionError(
                "Error parsing SQL: %s in line: %d - payload: %s" % (err, exc_tb.tb_lineno, string))

        return return_list

    def _request_vimar(self, post):
        """Prepare call to vimar webserver."""
        url = '%s://%s:%s/cgi-bin/dpadws' % (
            VimarLink._schema, VimarLink._host, VimarLink._port)

        # _LOGGER.error("calling url: " + url)
        headers = {
            'SOAPAction': 'dbSoapRequest',
            'SOAPServer': '',
            # 'X-Requested-With' => 'XMLHttpRequest',
            'Content-Type': 'text/xml; charset="UTF-8"',
            # needs to be set to overcome:
            # 'Expect' => '100-continue'
            # otherwise header and payload is send in two requests if payload
            # is bigger then 1024byte
            'Expect': ''
        }
        # _LOGGER.info("in _request_vimar")
        # _LOGGER.info(post)
        response = self._request(url, post, headers)
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
            _LOGGER.error("Error parsing XML: %s", err)
            _LOGGER.debug("Problematic XML: %s", str(xml))

        else:
            return root
        return None

    def _request(
            self,
            url,
            post=None,
            headers=None,
            check_ssl=False):
        """Call web server using post variables."""
        # _LOGGER.info("request to " + url)
        try:
            # connection, read timeout
            timeouts = (int(VimarLink._timeout / 2), VimarLink._timeout)

            if self._certificate is not None:
                check_ssl = self._certificate
            else:
                _LOGGER.debug("Request ignores ssl certificate")

            if post is None:
                response = requests.get(url,
                                        headers=headers,
                                        verify=check_ssl,
                                        timeout=timeouts)
            else:
                response = requests.post(url,
                                         data=post,
                                         headers=headers,
                                         verify=check_ssl,
                                         timeout=timeouts)

            # If the response was successful, no Exception will be raised
            response.raise_for_status()

        except HTTPError as http_err:
            _LOGGER.error('HTTP error occurred: %s', str(http_err))
            return False
        # except ReadTimeoutError:
        except requests.exceptions.Timeout:
            return False
        except BaseException as err:
            _LOGGER.error('Error occurred: %s', str(err))
            return False
        else:
            return response.text

        return None


class VimarProject():
    """Container that holds all vimar devices and its states."""

    _devices = {}
    _link = None
    _platforms_exists = {}

    # single device
    #   'room_ids': number[] (maybe empty, ids of rooms)
    #   'object_id': number (unique id of entity)
    #   'object_name': str (name of the device, reformated in format_name)
    #   'object_type': str (CH_xx channel name of vimar)
    #   'status':  dict{dict{'status_id': number, 'status_value': str }}
    #   'device_type': str (mapped type: lights, switches, climates, covers, sensors)
    #   'device_class': str (mapped class, based on name or attributes: fan, outlet, window, power)

    def __init__(self, link: VimarLink):
        """Create new container to hold all states."""
        self._link = link

    @property
    def devices(self):
        """Return all devices in current project."""
        return self._devices

    def update(self):
        """Get all devices from the vimar webserver, if object list is already there, only update states."""
        first_run = True

        # DONE - only update the state - not the actual devices, so we do not need to parse device types again
        if self._devices is not None and len(self._devices) > 0:
            first_run = False

        # TODO - check which device states has changed and call device updates
        self._devices, state_count = self._link.get_paged_results(self._link.get_remote_devices, self._devices)

        # for now we run parse device types and set classes after every update
        if first_run:
            self.check_devices()

        return self._devices

    def check_devices(self):
        """On first run of update, all device types and names are parsed to determin the correct platform."""
        if self._devices is not None and len(self._devices) > 0:
            for device_id, device in self._devices.items():
                self.parse_device_type(device)
            return True
        else:
            return False

    def get_by_device_type(self, platform):
        """Do dictionary comprehension."""
        return {k: v for (k, v) in self._devices.items() if v['device_type'] == platform}

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
            if device["object_name"].find("VENTILATOR") != -1 or device["object_name"].find("FANCOIL") != -1 or device["object_name"].find("VENTILATORE") != -1:
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:fan", "mdi:fan-off"]

                # device_type = DEVICE_TYPE_MEDIA_PLAYERS
                # icon = ["mdi:radio", "mdi:radio-off"]

            elif device["object_name"].find("LAMPE") != -1:
                device_type = DEVICE_TYPE_LIGHTS
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:lightbulb-on", "mdi:lightbulb-off"]
            elif device["object_name"].find("STECKDOSE") != -1 or device["object_name"].find("PULSANTE") != -1:
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_OUTLET
                icon = ["mdi:power-plug", "mdi:power-plug-off"]
            else:
                # fallback to lights
                device_type = DEVICE_TYPE_LIGHTS
                icon = "mdi:ceiling-light"

        elif device["object_type"] in ["CH_KNX_GENERIC_ONOFF", "CH_KNX_GENERIC_TIME_S", "CH_KNX_RELE"]:
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

        elif device["object_type"] in ["CH_Dimmer_Automation", "CH_Dimmer_RGB", "CH_Dimmer_White", "CH_Dimmer_Hue"]:
            device_type = DEVICE_TYPE_LIGHTS
            icon = ["mdi:speedometer", "mdi:speedometer-slow"]

        elif device["object_type"] in ["CH_ShutterWithoutPosition_Automation", "CH_Shutter_Automation"]:
            if device["object_name"].find("F-FERNBEDIENUNG") != -1:
                device_type = DEVICE_TYPE_COVERS
                device_class = DEVICE_CLASS_WINDOW
                icon = ["mdi:window-closed-variant", "mdi:window-open-variant"]
            else:
                # could be: shade, blind, window
                # see: https://www.home-assistant.io/integrations/cover/
                device_type = DEVICE_TYPE_COVERS
                device_class = DEVICE_CLASS_SHUTTER
                icon = ["mdi:window-shutter", "mdi:window-shutter-open"]

        elif device["object_type"] in ["CH_Clima", "CH_HVAC_NoZonaNeutra", "CH_HVAC_RiscaldamentoNoZonaNeutra", "CH_Fancoil"]:
            device_type = DEVICE_TYPE_CLIMATES
            icon = "mdi:thermometer-lines"

        elif device["object_type"] == "CH_Scene":
            device_type = DEVICE_TYPE_SWITCHES
            device_class = DEVICE_CLASS_SWITCH
            icon = "mdi:home-assistant"

        elif device["object_type"] in ["CH_Misuratore", "CH_Carichi_Custom", "CH_Carichi", "CH_Carichi_3F", "CH_KNX_GENERIC_POWER_KW"]:
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_POWER
            icon = "mdi:home-analytics"

            # _LOGGER.debug(
            #     "Sensor object returned from web server: "
            #     + device["object_type"]
            #     + " / "
            #     + device["object_name"])
            # _LOGGER.debug(
            #     "Sensor object has states: "
            #     + str(device["status"]))

        elif device["object_type"] in ["CH_Audio"]:
            device_type = DEVICE_TYPE_MEDIA_PLAYERS
            icon = ["mdi:radio", "mdi:radio-off"]

            _LOGGER.debug(
                "Audio object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"])
            _LOGGER.debug(
                "Audio object has states: "
                + str(device["status"]))

        elif device["object_type"] in ["CH_SAI", "CH_Event"]:
            _LOGGER.debug(
                "Unsupported object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"])
            _LOGGER.debug(
                "Unsupported object has states: "
                + str(device["status"]))
        else:
            _LOGGER.warning(
                "Unknown object returned from web server: "
                + device["object_type"]
                + " / "
                + device["object_name"])
            _LOGGER.debug(
                "Unknown object has states: "
                + str(device["status"]))

        device["device_type"] = device_type
        device["device_class"] = device_class
        device["icon"] = icon
        # TODO - make format name configurable
        device["object_name"] = self.format_name(device["object_name"])

        if device_type in self._platforms_exists:
            self._platforms_exists[device_type] += 1
        else:
            self._platforms_exists[device_type] = 1

    def format_name(self, name):
        """Format device name to get rid of unused terms."""
        parts = name.split(' ')

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
                entity_number = ''
                room_name = ''
                level_name = parts[1]

                for i in range(2, len(parts)):
                    level_name += " " + parts[i]
            else:
                # _LOGGER.debug(
                #     "Found a device with an uncommon naming schema: %s", name)

                device_type = parts[0]
                entity_number = ''
                room_name = ''
                # level_name = 'LEVEL'
                level_name = ''

                for i in range(2, len(parts)):
                    level_name += " " + parts[i]

        device_type = device_type.replace('LUCE', '')
        device_type = device_type.replace('TAPPARELLA', '')

        if device_type != 'LICHT':
            device_type = device_type.replace('LICHT', '')

        device_type = device_type.replace('ROLLLADEN', '')
        device_type = device_type.replace('F-FERNBEDIENUNG', 'FENSTER')
        device_type = device_type.replace('VENTILATORE', '')
        device_type = device_type.replace('VENTILATOR', '')
        device_type = device_type.replace('STECKDOSE', '')
        device_type = device_type.replace('THERMOSTAT', '')

        if len(level_name) != 0:
            level_name += " "
        if len(room_name) != 0:
            room_name += " "
        if len(device_type) != 0:
            device_type += " "

        # Erdgeschoss Wohnzimmer Licht 3
        name = "%s%s%s%s" % (level_name, room_name,
                             device_type, entity_number)

        # change case
        return name.title().strip()
