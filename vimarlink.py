"""Platform for light integration."""

import logging
# import asyncio
# import time
# for communicating with vimar webserver
import requests
from requests.exceptions import HTTPError
import xml.etree.cElementTree as xmlTree
import sys
from xml.etree import ElementTree
# from . import DOMAIN

# import queue
# import threading
# import socket

_LOGGER = logging.getLogger(__name__)


class VimarLink():

    # the_queue = queue.Queue()
    # thread = None

    # private
    _host = ''
    _schema = ''
    _port = 443
    _username = ''
    _password = ''
    _session_id = None
    _maingroup_ids = None
    _certificate = None

    def __init__(
            self,
            schema=None,
            host=None,
            port=None,
            username=None,
            password=None,
            certificate=None):
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

    def installCertificate(self):
        # temporarily disable certificate requests
        if len(self._certificate) != 0:
            tempCertificate = self._certificate
            self._certificate = None

            certificateUrl = "%s://%s:%s/vimarbyweb/modules/vimar-byme/script/rootCA.VIMAR.crt" % (
                VimarLink._schema, VimarLink._host, VimarLink._port)
            certificateFile = self._request(certificateUrl)

            if certificateFile is None:
                _LOGGER.error("Certificate download failed")
                return False

            # get it back
            self._certificate = tempCertificate

            try:
                file = open(self._certificate, "w")
                file.write(certificateFile)
                file.close()
            except BaseException:
                _LOGGER.error("Saving certificate failed")
                return False

            _LOGGER.info("Downloaded Vimar CA certificate to: " +
                         self._certificate)

        return True

    def login(self):
        loginurl = "%s://%s:%s/vimarbyweb/modules/system/user_login.php?sessionid=&username=%s&password=%s&remember=0&op=login" % (
            VimarLink._schema, VimarLink._host, VimarLink._port, VimarLink._username, VimarLink._password)

        result = self._request(loginurl)

        if result is not None:
            xml = self._parse_xml(result)
            logincode = xml.find('result')
            loginmessage = xml.find('message')
            if logincode is not None and logincode.text != "0":
                if loginmessage is not None:
                    _LOGGER.error("Error during login: " + loginmessage.text)
                else:
                    _LOGGER.error("Error during login: " + logincode.text)
            else:
                _LOGGER.info("Vimar login ok")
                loginsession = xml.find('sessionid')
                if loginsession.text != "":
                    _LOGGER.debug("Got a new Vimar Session id: " +
                                  loginsession.text)
                    VimarLink._session_id = loginsession.text
                else:
                    _LOGGER.warning(
                        "Missing Session id in login response:" + result)

        return result

    def check_login(self):
        if (VimarLink._session_id is None):
            self.login()

        return (VimarLink._session_id is not None)

    def set_device_status(self, object_id, status, optionals="NO-OPTIONALS"):
        """ when setting climates optionals should be set to SYNCDB """

        post = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><service-runonelement xmlns="urn:xmethods-dpadws"><payload>%s</payload><hashcode>NO-HASHCODE</hashcode><optionals>%s</optionals><callsource>WEB-DOMUSPAD_SOAP</callsource><sessionid>%s</sessionid><waittime>10</waittime><idobject>%s</idobject><operation>SETVALUE</operation></service-runonelement></soapenv:Body></soapenv:Envelope>
        """ % (status,
               optionals,
               VimarLink._session_id,
               object_id)

        response = self._request_vimar(post)
        if response is not None and response is not False:

            payload = response.find('.//payload')

            # usually set_status should not return a payload
            if payload is not None:
                _LOGGER.warning(
                    "set_device_status returned a payload: " +
                    payload.text +
                    " from post request: " +
                    post)
                parsed_data = self._parse_sql_payload(payload.text)
                # _LOGGER.info("parsed payload: "+ parsed_data)
                return parsed_data

        # _LOGGER.warning("Empty payload from Status")
        return None

    def get_device_status(self, object_id, status_id=None):

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

            # _LOGGER.info("getDevice")
            # _LOGGER.info(single_device)

            return status_list
        else:
            return {}

        return {}

    def get_device(self, object_id):

        single_device = {}

# , o3.OPTIONALP AS status_range
        select = """SELECT GROUP_CONCAT(r2.PARENTOBJ_ID) AS room_ids, o2.ID AS object_id, o2.NAME AS object_name, o2.VALUES_TYPE as object_type,
o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX" AND o2.values_type NOT IN ("CH_Scene")
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ"
WHERE o2.ID IN (%s) AND r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
GROUP BY o2.ID, o2.NAME, o2.VALUES_TYPE, o3.ID, o3.NAME, o3.CURRENT_VALUE
ORDER BY o2.NAME, o3.ID;""" % (object_id)

        payload = self._request_vimar_sql(select)
        if payload is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in payload:
                if single_device == {}:
                    single_device = {
                        'room_ids': device['room_ids'].split(','),
                        'object_id': device['object_id'],
                        'object_name': device['object_name'],
                        'object_type': device['object_type'],
                        'status': {
                            device['status_name']: {
                                'status_id': device['status_id'],
                                'status_value': device['status_value'],
                                # 'status_range': device['status_range'],
                            }
                        }
                    }
                else:
                    if device['status_name'] != '':
                        single_device['status'][device['status_name']] = {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            # 'status_range': device['status_range'],
                        }

            # _LOGGER.info("getDevice")
            # _LOGGER.info(single_device)

            return single_device
        else:
            return None

        return None

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

    def get_devices(self):

        _LOGGER.info("getDevices started")

        if VimarLink._maingroup_ids is None:
            return None

        devices = {}

        # o3.OPTIONALP AS status_range
        # AND o3.OPTIONALP IS NOT NULL
        #
        #
        # AND
        # o2.ENABLE_FLAG = "1" AND o2.IS_READABLE = "1" AND o2.IS_WRITABLE =
        # "1" AND o2.IS_VISIBLE = "1"

        select = """SELECT GROUP_CONCAT(r2.PARENTOBJ_ID) AS room_ids, o2.ID AS object_id,
o2.NAME AS object_name, o2.VALUES_TYPE as object_type,
o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX" AND o2.values_type NOT IN ("CH_Scene")
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ"
WHERE r2.PARENTOBJ_ID IN (%s) AND r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
GROUP BY o2.ID, o2.NAME, o2.VALUES_TYPE, o3.ID, o3.NAME, o3.CURRENT_VALUE
ORDER BY o2.NAME, o3.ID;""" % (VimarLink._maingroup_ids)

        payload = self._request_vimar_sql(select)
        if payload is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in payload:
                # device['status_name'] = device['status_name'].replace('/', '_')
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
                                # 'status_range': device['status_range'],
                            }
                        }
                    }
                else:
                    if device['status_name'] != '':
                        devices[device['object_id']]['status'][device['status_name']] = {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            # 'status_range': device['status_range'],
                        }

            _LOGGER.info("getDevices ends - found " +
                         str(len(devices)) + " devices")
            # _LOGGER.info("getDevices")
            # _LOGGER.info(devices)

            return devices
        else:
            return None

        return None

    def get_main_groups(self):
        if VimarLink._maingroup_ids is not None:
            return VimarLink._maingroup_ids

        select = """SELECT GROUP_CONCAT(o1.id) as MAIN_GROUPS FROM DPADD_OBJECT o0
INNER JOIN DPADD_OBJECT_RELATION r1 ON o0.ID = r1.PARENTOBJ_ID AND r1.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
INNER JOIN DPADD_OBJECT o1 ON r1.CHILDOBJ_ID = o1.ID AND o1.type = "GROUP"
WHERE o0.NAME = "_DPAD_DBCONSTANT_GROUP_MAIN";"""

        payload = self._request_vimar_sql(select)
        if payload is not None:
            VimarLink._maingroup_ids = payload[0]['MAIN_GROUPS']
            return VimarLink._maingroup_ids
        else:
            return None

    def _request_vimar_sql(self, select):

        select = select.replace('\r\n', ' ').replace(
            '\n', ' ').replace('"', '&apos;').replace('\'', '&apos;')

        post = ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body>'
                '<service-databasesocketoperation xmlns="urn:xmethods-dpadws">'
                '<payload>NO-PAYLOAD</payload><hashcode>NO-HASCHODE</hashcode><optionals>NO-OPTIONAL</optionals>'
                '<callsource>WEB-DOMUSPAD_SOAP</callsource><sessionid>%s</sessionid><waittime>5</waittime>'
                '<function>DML-SQL</function><type>SELECT</type><statement>%s</statement><statement-len>%d</statement-len>'
                '</service-databasesocketoperation></soapenv:Body></soapenv:Envelope>') % (
            VimarLink._session_id, select, len(select))

        # _LOGGER.info("in _request_vimar_sql")
        # _LOGGER.info(post)
        response = self._request_vimar(post)
        # _LOGGER.info("response: ")
        # _LOGGER.info(response)
        if response is not None and response is not False:
            payload = response.find('.//payload')
            if payload is not None:
                # _LOGGER.info("Got a new payload: " + payload.text)
                parsed_data = self._parse_sql_payload(payload.text)

                if parsed_data is None:
                    _LOGGER.warning(
                        "Received invalid data from SQL: " +
                        ElementTree.tostring(
                            response,
                            encoding='unicode') +
                        " from post: " +
                        post)

                return parsed_data
            else:
                _LOGGER.warning("Empty payload from SQL")
                return None
        elif response is None:
            _LOGGER.warning("Empty response from SQL")
            _LOGGER.info("Errorous SQL: " + select)
        return None

    def _parse_sql_payload(self, string):
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
                    # split prefix from values
                    prefix, values = line.split(':', 1)
                    # prefix = prefix.split('#', 1)[1].strip()
                    prefix = prefix.strip()

                    # skip unused prefixes
                    if prefix == 'Response' or prefix == 'NextRows':
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

                            if len(row_dict):
                                return_list.append(row_dict)
        except Exception as err:
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            _, _, exc_tb = sys.exc_info()

            _LOGGER.error(
                "Error parsing SQL: " +
                repr(err) +
                " in line: " +
                exc_tb.tb_lineno +
                " - payload: " +
                string)
            return None

        # _LOGGER.info("parseSQLPayload")
        # _LOGGER.info(return_list)
        return return_list

    def _request_vimar(self, post):
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
        else:
            return response

    def _parse_xml(self, xml):
        try:
            root = xmlTree.fromstring(xml)
        except Exception as err:
            _LOGGER.error("Error parsing XML: " + xml + " - " + repr(err))
        else:
            return root
        return None

    def _request(
            self,
            url,
            post=None,
            headers=None,
            timeout=5,
            checkSSL=False):
        # _LOGGER.info("request to " + url)
        try:
            # connection, read timeout
            timeouts = (3, 6)

            if self._certificate is not None:
                checkSSL = self._certificate
            else:
                _LOGGER.debug("Request ignores ssl certificate")

            if post is None:
                response = requests.get(url,
                                        headers=headers,
                                        verify=checkSSL,
                                        timeout=timeouts)
            else:
                # _LOGGER.info("sending post: ")
                # _LOGGER.info(post)
                # _LOGGER.info(headers)
                # _LOGGER.info(checkSSL)

                response = requests.post(url,
                                         data=post,
                                         headers=headers,
                                         verify=checkSSL,
                                         timeout=timeouts)

            # If the response was successful, no Exception will be raised
            response.raise_for_status()

        except HTTPError as http_err:
            # _LOGGER.error(f'HTTP error occurred: {http_err}') # Python 3.6
            _LOGGER.error('HTTP error occurred: ' + str(http_err))
            return False
        except Exception as err:
            # _LOGGER.error(f'Other error occurred: {err}') # Python 3.6
            _LOGGER.error('Other error occurred: ' + repr(err))
            return False
        else:
            # _LOGGER.info('request Successful!')
            # _LOGGER.info('RAW Response: ')
            # _LOGGER.info(response.text)
            # response.encoding = 'utf-8'
            return response.text

        return None

    # read out schedule: <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><service-vimarclimateeventgettimeschedule xmlns="urn:xmethods-dpadws"><payload>NO-PAYLOAD</payload><hashcode>NO-HASCHODE</hashcode><optionals>NO-OPTIONAL</optionals><callsource>WEB-DOMUSPAD_SOAP</callsource><sessionid>5e8a5aa99db78</sessionid><waittime>300</waittime><idobject>939</idobject><mode>CLIMATE</mode><type>WEEKLY</type><weekday>2</weekday><season>0</season></service-vimarclimateeventgettimeschedule></soapenv:Body></soapenv:Envelope>
    # read out all climate details: SELECT * FROM DPADD_OBJECT_RELATION WHERE PARENTOBJ_ID IN (939) OR CHILDOBJ_ID IN (939) ORDER BY ORDER_NUM,ID ;
    # read out climate values t1,t2,t3: SELECT ID,NAME,STATUS_ID,CURRENT_VALUE
    # FROM DPADD_OBJECT WHERE ID IN (9187,9188,9189);

    # methods for async sending and thread
    # problem: how do i get the response...
    # def send_message(self, msg):
    #     VimarLink.the_queue.put_nowait(msg)
    #     if VimarLink.thread is None or not self.thread.isAlive():
    #         VimarLink.thread = threading.Thread(target=self._startSending)
    #         VimarLink.thread.start()

    # def _startSending(self):
    #     while not VimarLink.the_queue.empty():
    #         self._send_reliable_message(VimarLink.the_queue.get_nowait())

    # def _send_reliable_message(self, msg):
    #     return True
    #     """ Send msg to LightwaveRF hub and only returns after:
    #          an OK is received | timeout | exception | max_retries """
    #     result = False
    #     max_retries = 15
    #     try:
    #         with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as write_sock:
    #             write_sock.setsockopt(
    #                 socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #             with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as read_sock:
    #                 read_sock.setsockopt(
    #                     socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    #                 read_sock.settimeout(VimarLink.SOCKET_TIMEOUT)
    #                 read_sock.bind(('0.0.0.0', VimarLink.RX_PORT))
    #                 while max_retries:
    #                     max_retries -= 1
    #                     write_sock.sendto(msg.encode(
    #                         'UTF-8'), (VimarLink.link_ip, VimarLink.TX_PORT))
    #                     result = False
    #                     while True:
    #                         response, dummy = read_sock.recvfrom(1024)
    #                         response = response.decode('UTF-8').split(',')[1]
    #                         if response.startswith('OK'):
    #                             result = True
    #                             break
    #                         if response.startswith('ERR'):
    #                             break

    #                     if result:
    #                         break

    #                     time.sleep(0.25)

    #     except socket.timeout:
    #         return result

    #     return result
# end class Vimar
