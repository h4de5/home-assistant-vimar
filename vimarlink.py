"""Platform for light integration."""

import logging
import voluptuous as vol
# import asyncio
import time
import logging
# for communicating with vimar webserver
import requests
from requests.exceptions import HTTPError
import xml.etree.cElementTree as xmlTree
# from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

class VimarLink():

    # the_queue = queue.Queue()
    # thread = None
    host = ''
    username = ''
    password = ''

    # private
    session_id = None
    maingroup_ids = None

    def __init__(self, host=None, username=None, password=None):
        _LOGGER.info("Vimar link started")

        if host is not None:
            VimarLink.host = host
        if username is not None:
            VimarLink.username = username
        if password is not None:
            VimarLink.password = password


    def login(self):
        loginurl = "https://%s/vimarbyweb/modules/system/user_login.php?sessionid=&username=%s&password=%s&remember=0&op=login" % (VimarLink.host, VimarLink.username, VimarLink.password)

        result = self.request(loginurl)

        if result is not None:
            _LOGGER.info("Vimar login result: " + result)
            xml = self.parseXML(result)
            logincode = xml.find('result')
            loginmessage= xml.find('message')
            if logincode is not None and logincode.text != "0":
                if loginmessage is not None:
                    _LOGGER.error("Error during login: " + loginmessage.text)
                else:
                    _LOGGER.error("Error during login: " + logincode.text)
            else:
                loginsession = xml.find('sessionid')
                _LOGGER.info("Got a new Session id: " + loginsession.text)

                VimarLink.session_id = loginsession.text

        return result

    def is_valid_login(self):
        if (VimarLink.session_id is None):
            self.login()

        return (VimarLink.session_id is not None)

    def updateStatus(self, object_id, status):
        post = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><service-runonelement xmlns="urn:xmethods-dpadws"><payload>%s</payload><hashcode>NO-HASHCODE</hashcode><optionals>NO-OPTIONALS</optionals><callsource>WEB-DOMUSPAD_SOAP</callsource><sessionid>%s</sessionid><waittime>10</waittime><idobject>%s</idobject><operation>SETVALUE</operation></service-runonelement></soapenv:Body></soapenv:Envelope>
		""" % (status, VimarLink.session_id, object_id)

        response = self.requestVimar(post)
        if response is not None:
            payload = response.find('.//payload')
            if payload is not None:
                parsed_data = self.parseSQLPayload(payload.text)

                _LOGGER.info("updateStatus")
                _LOGGER.info(parsed_data)

                return parsed_data
            
        _LOGGER.warning("Empty payload from Status")
        return None


    def getDevice(self, object_id):

        single_device = {}

        select = """SELECT GROUP_CONCAT(r2.PARENTOBJ_ID) AS room_ids, o2.ID AS object_id, o2.NAME AS object_name,
o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value, o3.OPTIONALP AS status_range
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX" AND o2.values_type NOT IN ("CH_Scene")
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ" AND o3.OPTIONALP IS NOT NULL
WHERE o2.ID IN (%s) AND r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
GROUP BY o2.ID, o2.NAME, o3.ID, o3.NAME, o3.CURRENT_VALUE, o3.OPTIONALP
ORDER BY o2.NAME;""" % (object_id)

        payload = self.requestVimarSQL(select)
        if payload is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in payload:
                if single_device == {}:
                    single_device = {
                        'room_ids': device['room_ids'].split(','),
                        'object_id': device['object_id'],
                        'object_name': device['object_name'],
                        'status': {
                            device['status_name']: {
                                'status_id': device['status_id'],
                                'status_value': device['status_value'],
                                'status_range': device['status_range'],
                            }
                        }
                    }
                else:
                    if device['status_name'] != '':
                        single_device['status'][device['status_name']] = {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            'status_range': device['status_range'],
                        }

            # _LOGGER.info("getDevice")
            # _LOGGER.info(single_device)
            
            return single_device
        else:
            return None

        return None

    def getDevices(self):

        if VimarLink.maingroup_ids is None:
            return None

        devices = {}

        select = """SELECT GROUP_CONCAT(r2.PARENTOBJ_ID) AS room_ids, o2.ID AS object_id, o2.NAME AS object_name,
o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value, o3.OPTIONALP AS status_range
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX" AND o2.values_type NOT IN ("CH_Scene")
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ" AND o3.OPTIONALP IS NOT NULL
WHERE r2.PARENTOBJ_ID IN (%s) AND r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION" AND o2.NAME LIKE "ROLL%%"
GROUP BY o2.ID, o2.NAME, o3.ID, o3.NAME, o3.CURRENT_VALUE, o3.OPTIONALP;""" % (VimarLink.maingroup_ids)

        payload = self.requestVimarSQL(select)
        if payload is not None:
            # there will be multible times the same device
            # each having a different status part (on/off + dimming etc.)
            for device in payload:
                if device['object_id'] not in devices:
                    devices[device['object_id']] = {
                        'room_ids': device['room_ids'].split(','),
                        'object_id': device['object_id'],
                        'object_name': device['object_name'],
                        'status': {
                            device['status_name']: {
                                'status_id': device['status_id'],
                                'status_value': device['status_value'],
                                'status_range': device['status_range'],
                            }
                        }
                    }
                else:
                    if device['status_name'] != '':
                        devices[device['object_id']]['status'][device['status_name']] = {
                            'status_id': device['status_id'],
                            'status_value': device['status_value'],
                            'status_range': device['status_range'],
                        }

            _LOGGER.info("getDevices")
            _LOGGER.info(devices)
            
            return devices
        else:
            return None

        return None

    def getMainGroups(self):
        if VimarLink.maingroup_ids is not None:
            return VimarLink.maingroup_ids

        select = """SELECT GROUP_CONCAT(o1.id) as MAIN_GROUPS FROM DPADD_OBJECT o0
INNER JOIN DPADD_OBJECT_RELATION r1 ON o0.ID = r1.PARENTOBJ_ID AND r1.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
INNER JOIN DPADD_OBJECT o1 ON r1.CHILDOBJ_ID = o1.ID AND o1.type = "GROUP"
WHERE o0.NAME = "_DPAD_DBCONSTANT_GROUP_MAIN";"""

        payload = self.requestVimarSQL(select)
        if payload is not None:
            VimarLink.maingroup_ids = payload[0]['MAIN_GROUPS']
            return VimarLink.maingroup_ids
        else:
            return None
    
    def requestVimarSQL(self, select):

        select = select.replace('\r\n', ' ').replace('\n', ' ').replace('"', '&apos;').replace('\'', '&apos;')

        post = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><service-databasesocketoperation xmlns="urn:xmethods-dpadws"><payload>NO-PAYLOAD</payload><hashcode>NO-HASCHODE</hashcode><optionals>NO-OPTIONAL</optionals><callsource>WEB-DOMUSPAD_SOAP</callsource><sessionid>%s</sessionid><waittime>5</waittime><function>DML-SQL</function><type>SELECT</type><statement>%s</statement><statement-len>%d</statement-len></service-databasesocketoperation></soapenv:Body></soapenv:Envelope>' % (VimarLink.session_id, select, len(select))

        # _LOGGER.info("in requestVimarSQL")
        # _LOGGER.info(post)
        response = self.requestVimar(post)
        # _LOGGER.info("response: ")
        # _LOGGER.info(response)
        if response is not None:
            payload = response.find('.//payload')
            if payload is not None:
                # _LOGGER.info("Got a new payload: " + payload.text)
                parsed_data = self.parseSQLPayload(payload.text)
                # TODO: we need to move parseSQLPayload over to pyton,
                # Response: DBMG-000
                # NextRows: 2
                # Row000001: 'MAIN_GROUPS'
                # Row000002: '435,439,454,458,473,494,505,532,579,587,605,613,628,641,649,660,682,690,703,731,739,752,760,794,802,817,828,836,868,883,898,906,921,929,1777,1778'
                # should be MAIN_GROUPS = '435,439,454,458,473,494,505,532,579,587,605,613,628,641,649,660,682,690,703,731,739,752,760,794,802,817,828,836,868,883,898,906,921,929,1777,1778'

                return parsed_data
            
        _LOGGER.warning("Empty payload from SQL")
        return None
    
    # def parseSQLPayload(self, string):
    #     lines = string.split('\n')
    #     return_dict = {}
    #     keys = []
    #     for line in lines:
    #         if line:
    #             prefix, values = line.split(':', 1)
    #             prefix = prefix.split('#', 1)[1].strip()
    #             values = values.strip()[1:-1].split('\',\'')
                
    #             if prefix == 'Response':
    #                 pass
    #             elif prefix == 'NextRows':
    #                 pass
    #             else:
    #                 idx = 0
    #                 for value in values:
    #                 if prefix == 'Row000001':
    #                     keys.append(value)
    #                     return_dict[value] = []
    #                 else:
    #                     return_dict[keys[idx]].append(value)
    #                 idx += 1

    #     print("magic_function1: ", return_dict)
    #     return return_dict


    def parseSQLPayload(self, string):
        lines = string.split('\n')
        return_list = []
        keys = []
        for line in lines:
            if line:
                prefix, values = line.split(':', 1)
                # prefix = prefix.split('#', 1)[1].strip()
                prefix = prefix.strip()
                values = values.strip()[1:-1].split('\',\'')

                if prefix == 'Response':
                    pass
                elif prefix == 'NextRows':
                    pass
                else:
                    idx = 0
                    row_dict = {}
                    for value in values:
                        if prefix == 'Row000001':
                            keys.append(value)
                        else:
                            row_dict[keys[idx]] = value
                            idx += 1

                        if len(row_dict):
                            return_list.append(row_dict)

        # _LOGGER.info("parseSQLPayload")
        # _LOGGER.info(return_list)
        return return_list

    def requestVimar(self, post):
        url = 'https://%s/cgi-bin/dpadws' % VimarLink.host
        headers = {
			'SOAPAction': 'dbSoapRequest',
			'SOAPServer': '',
			#'X-Requested-With' => 'XMLHttpRequest',
			'Content-Type': 'text/xml; charset="UTF-8"',
			# needs to be set to overcome: 'Expect' => '100-continue' header
			# otherwise header and payload is send in two requests if payload is bigger then 1024byte
			'Expect': ''
        }
        # _LOGGER.info("in requestVimar")
        # _LOGGER.info(post)
        response = self.request(url, post, headers)
        if response is not None:
            responsexml = self.parseXML(response)
            # _LOGGER.info("responsexml: ")
            # _LOGGER.info(responsexml)

            return responsexml
        else:
            return None
    
    def parseXML(self, xml):
        try:
            root = xmlTree.fromstring(xml)
        except Exception as err:
            _LOGGER.error("Error parsing XML: " + xml + " - " + err)
        else:
            return root
        return None

    def request(self, url, post = None, headers = None, timeout = 5, checkSSL = False):
        test = []

        # _LOGGER.info("request to " + url)

        try:

            if post is None:
                response = requests.get(url,
                    headers= headers,
                    verify= checkSSL)
            else:
                # _LOGGER.info("sending post: ")
                # _LOGGER.info(post)
                # _LOGGER.info(headers)
                # _LOGGER.info(checkSSL)

                response = requests.post(url,
                    data= post,
                    headers= headers,
                    verify= checkSSL)

            # If the response was successful, no Exception will be raised
            response.raise_for_status()
            

        except HTTPError as http_err:
            _LOGGER.error(f'HTTP error occurred: {http_err}') # Python 3.6
        except Exception as err:
            _LOGGER.error(f'Other error occurred: {err}') # Python 3.6
        else:
            # _LOGGER.info('request Successful!')
            # _LOGGER.info('RAW Response: ')
            # _LOGGER.info(response.text)
            # response.encoding = 'utf-8'
            return response.text

        return None

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