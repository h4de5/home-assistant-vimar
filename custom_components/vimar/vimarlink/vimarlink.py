"""Main Vimar Link module - refactored to use modular components."""

from __future__ import annotations

import logging
from collections.abc import Callable
from xml.etree import ElementTree

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
    DEVICE_TYPE_LIGHTS = "light"
    DEVICE_TYPE_COVERS = "cover"
    DEVICE_TYPE_SWITCHES = "switch"
    DEVICE_TYPE_CLIMATES = "climate"
    DEVICE_TYPE_MEDIA_PLAYERS = "media_player"
    DEVICE_TYPE_SCENES = "scene"
    DEVICE_TYPE_SENSORS = "sensor"
    DEVICE_TYPE_OTHERS = "other"

from .connection import VimarConnection
from .device_queries import (
    VimarDevice,
    get_device_status_query,
    get_remote_devices_query,
    get_room_devices_query,
    get_room_ids_query,
    get_sai2_area_values_query,
    get_sai2_groups_query,
    get_sai2_zone_to_group_query,
    get_sai2_zones_query,
    get_status_only_query,
)
from .exceptions import VimarApiError, VimarConnectionError
from .sql_parser import parse_sql_payload

_LOGGER = logging.getLogger(__name__)
MAX_ROWS_PER_REQUEST = 300

DEVICE_CLASS_OUTLET = "outlet"
DEVICE_CLASS_SWITCH = "switch"
DEVICE_CLASS_SHUTTER = "shutter"
DEVICE_CLASS_WINDOW = "window"
DEVICE_CLASS_POWER = "power"
DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_PRESSURE = "pressure"


class VimarLink:
    """Link to communicate with the Vimar webserver."""

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
        """Initialize Vimar link with connection parameters."""
        _LOGGER.info("Vimar link initialized")

        self._connection = VimarConnection(
            schema=schema or "https",
            host=host or "",
            port=port or 443,
            username=username or "",
            password=password or "",
            certificate=certificate,
            timeout=timeout or 6,
        )

        self._room_ids = None
        self._rooms = None

    @property
    def _session_id(self):
        """Get session ID from connection."""
        return self._connection.session_id

    @property
    def request_last_exception(self):
        """Get last request exception."""
        return self._connection.request_last_exception

    def install_certificate(self):
        """Download CA certificate from web server."""
        return self._connection.install_certificate()

    def login(self):
        """Authenticate and get session ID."""
        return self._connection.login()

    def is_logged(self):
        """Check if session is available."""
        return self._connection.is_logged()

    def check_login(self):
        """Ensure valid session exists."""
        return self._connection.check_login()

    def check_session(self):
        """Check if session is valid."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Expect": "",
        }
        post = (
            f"sessionid={self._session_id}"
            "&op=getjScriptEnvironment&context=runtime"
        )
        return self._request_vimar(post, "vimarbyweb/modules/system/dpadaction.php", headers)

    def set_device_status(self, object_id, status, optionals="NO-OPTIONALS"):
        """Set status for one device."""
        post = (
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soapenv:Body><service-runonelement xmlns="urn:xmethods-dpadws">'
            f"<payload>{status}</payload>"
            "<hashcode>NO-HASHCODE</hashcode>"
            f"<optionals>{optionals}</optionals>"
            "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
            f"<sessionid>{self._session_id}</sessionid><waittime>10</waittime>"
            f"<idobject>{object_id}</idobject>"
            "<operation>SETVALUE</operation>"
            "</service-runonelement></soapenv:Body></soapenv:Envelope>"
        )

        response = self._request_vimar_soap(post)
        if response is not None and response is not False:
            payload = response.find(".//payload")
            if payload is not None:
                _LOGGER.debug(
                    "set_device_status returned payload: %s from request: %s",
                    payload.text or "unknown error",
                    post,
                )
                return parse_sql_payload(payload.text)
        return None

    def set_sai2_status(
        self, command: int, area_index: int, pin: str
    ) -> bool:
        """Send SAI2 alarm command via dedicated SOAP service.

        Uses service-vimarsai2allgroupsset which includes the PIN
        explicitly in each request.

        Args:
            command: 0=OFF (disarm), 1=ON, 2=INT, 3=PAR
            area_index: 1-based area number (1, 2, 3, ...)
            pin: SAI alarm PIN code

        Returns:
            True if server accepted the command, False otherwise.
        """
        # Build bitmask: area 1 = "00000001", area 2 = "00000010", etc.
        bitmask = 1 << (area_index - 1)
        groups_str = format(bitmask, "08b")

        post = (
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soapenv:Body><service-vimarsai2allgroupsset xmlns="urn:xmethods-dpadws">'
            f"<command>{command}</command>"
            f"<groups>{groups_str}</groups>"
            f"<pin>{pin}</pin>"
            "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
            f"<sessionid>{self._session_id}</sessionid>"
            "<waittime>10</waittime>"
            "</service-vimarsai2allgroupsset></soapenv:Body></soapenv:Envelope>"
        )

        _LOGGER.debug(
            "SAI2 SOAP: command=%d groups=%s (area %d)",
            command, groups_str, area_index,
        )

        response = self._request_vimar_soap(post)
        if response is None or response is False:
            _LOGGER.error("SAI2: no response from server")
            return False

        # Log full response for debugging
        try:
            from xml.etree import ElementTree
            resp_str = ElementTree.tostring(response, encoding="unicode")
            _LOGGER.debug("SAI2 SOAP response: %s", resp_str)
        except Exception:
            pass

        return True

    def get_optionals_param(self, state):
        """Return SYNCDB for climate states."""
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
        return "NO-OPTIONALS"

    def get_device_status(self, object_id):
        """Get attribute status for a single device."""
        status_list = {}
        select = get_device_status_query(object_id)
        payload = self._request_vimar_sql(select)

        if payload is not None:
            for device in payload:
                if device["status_name"] != "":
                    status_list[device["status_name"]] = {
                        "status_id": device["status_id"],
                        "status_value": device["status_value"],
                    }
        return status_list

    def get_status_only(self, status_ids: list[int]) -> list[dict] | None:
        """Slim poll: fetch only CURRENT_VALUE for known status IDs.

        PATCH #1: Optimized polling method that avoids expensive JOINs.
        """
        if not status_ids:
            return []
        select = get_status_only_query(status_ids)
        return self._request_vimar_sql(select)

    def get_paged_results(
        self,
        method: Callable[
            [dict[str, VimarDevice], int | None, int | None],
            tuple[dict[str, VimarDevice], int] | None,
        ],
        objectlist: dict[str, VimarDevice] | None = None,
        start: int = 0,
    ):
        """Page results from a method automatically.

        FIX #7: iterative instead of recursive (no stack overflow risk).
        """
        if objectlist is None:
            objectlist = {}
        limit = MAX_ROWS_PER_REQUEST

        if not callable(method):
            raise VimarApiError(f"Invalid method for paged results: {method}")

        total_count = 0
        while True:
            result = method(objectlist, start, limit)
            if result is None:
                raise VimarApiError(f"Invalid method results: {method}")

            objectlist, state_count = result
            total_count += state_count

            if state_count < limit:
                break

            start += state_count

        return objectlist, total_count

    def get_room_devices(
        self,
        devices: dict[str, VimarDevice] | None = None,
        start: int | None = None,
        limit: int | None = None,
    ):
        """Load all devices that belong to a room."""
        if devices is None:
            devices = {}
        if self._room_ids is None:
            return None

        start, limit = self._sanitize_limits(start, limit)
        _LOGGER.debug("get_room_devices started - from %d to %d", start, start + limit)

        select = get_room_devices_query(self._room_ids, start, limit)
        return self._generate_device_list(select, devices, only_update=True)

    def get_remote_devices(
        self,
        devices: dict[str, VimarDevice] | None = None,
        start: int | None = None,
        limit: int | None = None,
    ):
        """Get all devices that can be triggered remotely (includes scenes)."""
        if devices is None:
            devices = {}
        if len(devices) == 0:
            _LOGGER.debug(
                "get_remote_devices started - from %d to %d",
                start,
                (start or 0) + (limit or 0),
            )

        start, limit = self._sanitize_limits(start, limit)
        select = get_remote_devices_query(start, limit)
        return self._generate_device_list(select, devices)

    def _sanitize_limits(self, start: int | None, limit: int | None):
        """Check for sane values in start and limit."""
        if limit is None or limit > MAX_ROWS_PER_REQUEST or limit <= 0:
            limit = MAX_ROWS_PER_REQUEST
        if start is None or start < 0:
            start = 0
        return start, limit

    def _generate_device_list(
        self,
        select: str,
        devices: dict[str, VimarDevice] | None = None,
        only_update: bool = False,
    ):
        """Generate device list from SQL query."""
        if devices is None:
            devices = {}

        payload = self._request_vimar_sql(select)
        if payload is None:
            return None

        for device in payload:
            object_id = device["object_id"]

            if object_id not in devices:
                if only_update:
                    continue

                deviceItem: VimarDevice = {
                    "room_ids": [],
                    "room_names": [],
                    "room_name": "",
                    "object_id": object_id,
                    "object_name": device["object_name"],
                    "object_type": device["object_type"],
                    "status": {},
                    "device_type": "",
                    "device_class": "",
                    "device_friendly_name": "",
                    "icon": "",
                }
                devices[object_id] = deviceItem
            else:
                deviceItem = devices[object_id]

            if device["status_name"] != "":
                deviceItem["status"][device["status_name"]] = {
                    "status_id": device["status_id"],
                    "status_value": device["status_value"],
                }
                if "status_range" in device:
                    deviceItem["status"][device["status_name"]]["status_range"] = (
                        device["status_range"]
                    )

            if device["room_ids"] is not None and device["room_ids"] != "":
                room_ids = []
                room_names = []
                for roomId in device["room_ids"].split(","):
                    if roomId and self._rooms and roomId in self._rooms:
                        room = self._rooms[roomId]
                        room_ids.append(roomId)
                        room_names.append(room["name"])

                deviceItem["room_ids"] = room_ids
                deviceItem["room_names"] = room_names
                deviceItem["room_name"] = room_names[0] if room_names else ""

        return devices, len(payload)

    def get_room_ids(self):
        """Load main rooms - later used in get_room_devices."""
        if self._room_ids is not None:
            return self._room_ids

        _LOGGER.debug("get_main_groups start")
        select = get_room_ids_query()
        payload = self._request_vimar_sql(select)

        if payload is None:
            return None

        _LOGGER.debug("get_room_ids ends - payload: %s", str(payload))
        roomIds = []
        rooms = {}

        for group in payload:
            room_id = str(group["id"])
            roomIds.append(room_id)
            rooms[room_id] = {
                "id": room_id,
                "name": str(group["name"]),
            }

        self._rooms = rooms
        self._room_ids = ",".join(roomIds)
        _LOGGER.info("get_room_ids ends - found %d rooms", len(roomIds))

        return self._room_ids

    # ------------------------------------------------------------------
    # SAI2 alarm data retrieval
    # ------------------------------------------------------------------

    def get_sai2_devices(self) -> dict | None:
        """Fetch SAI2 alarm areas (groups) with their child states.

        Returns dict keyed by group ID:
        {
            "7560": {
                "name": "Reparto Giorno",
                "children": {
                    "Disinserito": {"cid": "7561", "value": "0"},
                    "Inserito INT": {"cid": "7562", "value": "0"},
                    ...
                }
            }
        }
        """
        select = get_sai2_groups_query()
        payload = self._request_vimar_sql(select)
        if not payload:
            _LOGGER.debug("SAI2: no group data returned")
            return None

        groups: dict = {}
        for row in payload:
            gid = row["GID"]
            gname = row["GNAME"]
            if not gname:  # skip unnamed groups
                continue
            if gid not in groups:
                groups[gid] = {"name": gname, "children": {}}
            # Extract state label from CNAME: "Reparto Giorno (Disinserito)" -> "Disinserito"
            cname = row["CNAME"]
            label = cname.split("(")[-1].rstrip(")").strip() if "(" in cname else cname
            groups[gid]["children"][label] = {
                "cid": row["CID"],
                "value": row["CURRENT_VALUE"],
            }

        _LOGGER.info("SAI2: found %d named alarm areas", len(groups))
        return groups if groups else None

    def get_sai2_zones(self) -> dict | None:
        """Fetch SAI2 alarm zones with their child states.

        Returns dict keyed by zone ID with same structure as groups.
        """
        select = get_sai2_zones_query()
        payload = self._request_vimar_sql(select)
        if not payload:
            _LOGGER.debug("SAI2: no zone data returned")
            return None

        zones: dict = {}
        for row in payload:
            zid = row["ZID"]
            zname = row["GNAME"]
            if not zname:
                continue
            if zid not in zones:
                zones[zid] = {"name": zname, "children": {}}
            cname = row["CNAME"]
            label = cname.split("(")[-1].rstrip(")").strip() if "(" in cname else cname
            zones[zid]["children"][label] = {
                "cid": row["CID"],
                "value": row["CURRENT_VALUE"],
            }

        _LOGGER.info("SAI2: found %d alarm zones", len(zones))
        return zones if zones else None

    def get_sai2_zone_to_group(self) -> dict[str, str] | None:
        """Fetch mapping of SAI2 zone IDs to their parent group IDs.

        Returns dict {zone_id: group_id} or None on error.
        Uses DPAD_SAI2GATEWAY_SAI2ZONEINTOGROUPS view.
        """
        select = get_sai2_zone_to_group_query()
        payload = self._request_vimar_sql(select)
        if not payload:
            _LOGGER.debug("SAI2: no zone-to-group mapping returned")
            return None

        mapping: dict[str, str] = {}
        for row in payload:
            zid = str(row.get("ZID", ""))
            gid = str(row.get("GID", ""))
            if zid and gid:
                mapping[zid] = gid

        _LOGGER.info("SAI2: mapped %d zones to groups", len(mapping))
        return mapping if mapping else None

    def get_sai2_status_ids(self, sai2_groups: dict | None, sai2_zones: dict | None) -> list[int]:
        """Collect all SAI2 child CIDs for slim polling."""
        ids = []
        for source in (sai2_groups, sai2_zones):
            if source:
                for item in source.values():
                    for child in item.get("children", {}).values():
                        try:
                            ids.append(int(child["cid"]))
                        except (ValueError, KeyError):
                            pass
        return ids

    def get_sai2_area_values(self, group_ids: list[str]) -> dict[str, str] | None:
        """Fetch live SAI2 area state from DPADD_OBJECT.CURRENT_VALUE.

        Unlike DPAD_SAI2GATEWAY_SAI2GROUPCHILDREN (whose CURRENT_VALUE does
        not update after commands), the SAI2 group object rows in DPADD_OBJECT
        reflect the real-time alarm state immediately after a command.

        Returns dict {group_id: current_value_bitmask_string} or None on error.
        e.g. {'7560': '00000000', '7615': '00000000', '7663': '00001001'}
        """
        if not group_ids:
            return {}
        select = get_sai2_area_values_query(group_ids)
        payload = self._request_vimar_sql(select)
        if payload is None:
            return None
        return {
            str(row["gid"]): str(row.get("current_value") or "00000000")
            for row in payload
        }

    def update_sai2_from_slim(
        self, sai2_groups: dict | None, sai2_zones: dict | None, slim_results: list[dict]
    ) -> None:
        """Update SAI2 data from slim poll results."""
        if not slim_results:
            return
        # Build lookup: status_id -> value
        lookup = {}
        for row in slim_results:
            sid = str(row.get("status_id", ""))
            val = row.get("status_value", "")
            if sid:
                lookup[sid] = val

        for source in (sai2_groups, sai2_zones):
            if source:
                for item in source.values():
                    for child in item.get("children", {}).values():
                        cid = child.get("cid", "")
                        if cid in lookup:
                            child["value"] = lookup[cid]

    def _request_vimar_sql(self, select: str):
        """Build and execute SQL request."""
        select = (
            select.replace("\r\n", " ")
            .replace("\n", " ")
            .replace('"', "&apos;")
            .replace("'", "&apos;")
        )

        post = (
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soapenv:Body><service-databasesocketoperation xmlns="urn:xmethods-dpadws">'
            "<payload>NO-PAYLOAD</payload>"
            "<hashcode>NO-HASCHODE</hashcode>"
            "<optionals>NO-OPTIONAL</optionals>"
            "<callsource>WEB-DOMUSPAD_SOAP</callsource>"
            f"<sessionid>{self._session_id}</sessionid>"
            "<waittime>5</waittime>"
            "<function>DML-SQL</function><type>SELECT</type>"
            f"<statement>{select}</statement><statement-len>{len(select)}</statement-len>"
            "</service-databasesocketoperation></soapenv:Body></soapenv:Envelope>"
        )

        response = self._request_vimar_soap(post)
        if response is None:
            _LOGGER.warning("Unparseable response from SQL")
            _LOGGER.info("Erroneous SQL: %s", select)
            return None

        if response is False:
            return None

        payload = response.find(".//payload")
        if payload is None:
            _LOGGER.warning("Empty payload from SQL")
            return None

        parsed_data = parse_sql_payload(payload.text)
        if parsed_data is None:
            _LOGGER.warning(
                "Received invalid data from SQL: %s from post: %s",
                ElementTree.tostring(response, encoding="unicode"),
                post,
            )
        return parsed_data

    def _request_vimar_soap(self, post: str):
        """Execute SOAP request."""
        headers = {
            "SOAPAction": "dbSoapRequest",
            "SOAPServer": "",
            "Content-Type": 'text/xml; charset="UTF-8"',
            "Expect": "",
        }
        return self._request_vimar(post, "cgi-bin/dpadws", headers)

    def _request_vimar(self, post: str, path: str, headers: dict):
        """Prepare call to Vimar webserver."""
        url = (
            f"{self._connection._schema}://{self._connection._host}"
            f":{self._connection._port}/{path}"
        )
        response = self._connection._request(url, post, headers)

        if response is None or response is False:
            return response

        return self._connection._parse_xml(response)


class VimarProject:
    """Container that holds all Vimar devices and states."""

    def __init__(self, link: VimarLink, device_customizer_action=None):
        """Create new container to hold all states."""
        self._link = link
        self._device_customizer_action = device_customizer_action
        # FIX: class-level mutable defaults rimossi; inizializzati per-istanza
        self._devices: dict[str, VimarDevice] = {}
        self._platforms_exists: dict[str, int] = {}
        self.global_channel_id = None
        # SAI2 alarm data
        self.sai2_groups: dict | None = None
        self.sai2_zones: dict | None = None
        # Mapping: {zone_id: group_id} - which area each zone belongs to
        self.sai2_zone_to_group: dict[str, str] | None = None
        # Live SAI2 area/zone bitmask values from DPADD_OBJECT
        self.sai2_area_values: dict[str, str] | None = None
        self.sai2_zone_values: dict[str, str] | None = None
        # Guard: {group_id: monotonic_deadline} - prevents slim poll from
        # overwriting optimistic values while a command is being processed.
        self.sai2_optimistic_until: dict[str, float] = {}

    @property
    def devices(self):
        """Return all devices in current project."""
        return self._devices

    def update(self, forced=False):
        """Get all devices from Vimar webserver, update states only."""
        if self._devices is None:
            self._devices = {}

        devices_count = len(self._devices)

        self._devices, state_count = self._link.get_paged_results(
            self._link.get_remote_devices, self._devices
        )

        if devices_count != len(self._devices) or forced:
            self._link.get_room_ids()
            self._link.get_paged_results(self._link.get_room_devices, self._devices)
            # Fetch SAI2 alarm structure (names, children)
            self.sai2_groups = self._link.get_sai2_devices()
            self.sai2_zones = self._link.get_sai2_zones()
            self.sai2_zone_to_group = self._link.get_sai2_zone_to_group()
            # Fetch initial live area values
            if self.sai2_groups:
                self.sai2_area_values = self._link.get_sai2_area_values(
                    list(self.sai2_groups.keys())
                )
            # Fetch initial live zone values
            if self.sai2_zones:
                self.sai2_zone_values = self._link.get_sai2_area_values(
                    list(self.sai2_zones.keys())
                )
            self.check_devices()

        return self._devices

    def check_devices(self):
        """Parse device types and names to determine correct platform."""
        if not self._devices:
            return False

        for device_id, device in self._devices.items():
            self.parse_device_type(device)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("check_devices end. Devices: %s", str(self._devices))
        return True

    def get_by_device_type(self, platform):
        """Filter devices by platform type."""
        return {k: v for (k, v) in self._devices.items() if v["device_type"] == platform}

    def platform_exists(self, platform):
        """Check if there are devices for a given platform."""
        return self._platforms_exists.get(platform, False)

    def parse_device_type(self, device):
        """Classify devices into supported groups based on types and names."""
        device_type = DEVICE_TYPE_OTHERS
        device_class = None
        icon = "mdi:home-assistant"
        obj_type = device["object_type"]
        obj_name = device["object_name"].upper()

        if obj_type == "CH_Main_Automation":
            if any(x in obj_name for x in ["VENTILATOR", "FANCOIL"]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:fan", "mdi:fan-off"]
            elif "LAMPE" in obj_name:
                device_type = DEVICE_TYPE_LIGHTS
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:lightbulb-on", "mdi:lightbulb-off"]
            elif any(x in obj_name for x in ["STECKDOSE", "PULSANTE"]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_OUTLET
                icon = ["mdi:power-plug", "mdi:power-plug-off"]
            elif any(x in obj_name for x in ["HEIZUNG", "HEIZK\u00d6RPER"]):
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:radiator", "mdi:radiator-off"]
            elif " IR " in obj_name:
                device_type = DEVICE_TYPE_SWITCHES
                device_class = DEVICE_CLASS_SWITCH
                icon = ["mdi:motion-sensor", "mdi:motion-sensor-off"]
                _LOGGER.debug("IR Sensor: %s / %s", obj_type, device["object_name"])
            else:
                device_type = DEVICE_TYPE_LIGHTS
                icon = "mdi:ceiling-light"

        elif obj_type in [
            "CH_KNX_GENERIC_ONOFF",
            "CH_KNX_GENERIC_TIME_S",
            "CH_KNX_RELE",
            "CH_KNX_GENERIC_ENABLE",
            "CH_KNX_GENERIC_RESET",
        ]:
            device_type = DEVICE_TYPE_SWITCHES
            device_class = DEVICE_CLASS_SWITCH
            icon = ["mdi:toggle-switch", "mdi:toggle-switch-off"]

        elif obj_type in [
            "CH_Dimmer_Automation",
            "CH_Dimmer_RGB",
            "CH_Dimmer_White",
            "CH_Dimmer_Hue",
        ]:
            device_type = DEVICE_TYPE_LIGHTS
            icon = ["mdi:speedometer", "mdi:speedometer-slow"]

        elif obj_type in [
            "CH_ShutterWithoutPosition_Automation",
            "CH_ShutterBlindWithoutPosition_Automation",
            "CH_Shutter_Automation",
            "CH_Shutter_Slat_Automation",
            "CH_ShutterBlind_Automation",
        ]:
            if "FERNBEDIENUNG" in obj_name:
                device_type = DEVICE_TYPE_COVERS
                device_class = DEVICE_CLASS_WINDOW
                icon = ["mdi:window-closed-variant", "mdi:window-open-variant"]
            else:
                device_type = DEVICE_TYPE_COVERS
                device_class = DEVICE_CLASS_SHUTTER
                icon = ["mdi:window-shutter", "mdi:window-shutter-open"]

        elif obj_type in [
            "CH_Clima",
            "CH_HVAC_NoZonaNeutra",
            "CH_HVAC_RiscaldamentoNoZonaNeutra",
            "CH_Fancoil",
            "CH_HVAC",
            "CH_HVAC_FanCoil",
            "CH_HVAC_FanCoilWithNeutralZone",
        ]:
            device_type = DEVICE_TYPE_CLIMATES
            icon = "mdi:thermometer-lines"
            _LOGGER.debug("Climate: %s / %s", obj_type, device["object_name"])

        elif obj_type == "CH_Scene":
            device_type = DEVICE_TYPE_SCENES
            icon = "hass:palette"
            _LOGGER.debug("Scene: %s / %s", obj_type, device["object_name"])

        elif obj_type in [
            "CH_Misuratore",
            "CH_Carichi_Custom",
            "CH_Carichi",
            "CH_Carichi_3F",
            "CH_KNX_GENERIC_POWER_KW",
        ]:
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_POWER
            icon = "mdi:chart-bell-curve-cumulative"

        elif "CH_CONTATORE_" in obj_type.upper():
            device_type = DEVICE_TYPE_SENSORS
            icon = "mdi:pulse"

        elif obj_type == "CH_KNX_GENERIC_TEMPERATURE_C":
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_TEMPERATURE
            icon = "mdi:thermometer"

        elif obj_type == "CH_KNX_GENERIC_WINDSPEED":
            device_type = DEVICE_TYPE_SENSORS
            device_class = DEVICE_CLASS_PRESSURE
            icon = "mdi:windsock"

        elif obj_type == "CH_WEATHERSTATION":
            device_type = DEVICE_TYPE_SENSORS
            icon = "mdi:weather-partly-snowy-rainy"

        elif obj_type == "CH_Audio":
            device_type = DEVICE_TYPE_MEDIA_PLAYERS
            icon = ["mdi:radio", "mdi:radio-off"]
            _LOGGER.debug("Audio: %s / %s", obj_type, device["object_name"])

        elif obj_type in ["CH_SAI", "CH_Event", "CH_KNX_GENERIC_TIMEPERIODMIN"]:
            _LOGGER.debug("SAI_DEBUG: %s / %s / states: %s", obj_type, device["object_name"], device.get("status", {}))
        else:
            _LOGGER.debug("Unknown: %s / %s", obj_type, device["object_name"])

        friendly_name = self.format_name(device["object_name"])
        device["device_type"] = device_type
        device["device_class"] = device_class
        device["device_friendly_name"] = friendly_name
        device["icon"] = icon

        if self._device_customizer_action:
            self._device_customizer_action(device)

        device_type = device["device_type"]
        self._platforms_exists[device_type] = self._platforms_exists.get(device_type, 0) + 1

    def format_name(self, name):
        """Format device name to remove unused terms.

        FIX #21: la logica precedente con loop replace() e continue per
        LUCE/LICHT era sbagliata: il continue saltava solo l'iterazione LUCE
        ma non proteggeva il replace LICHT->''. Ripristinata la catena
        replace() sequenziale del master con guard esplicito per LICHT.
        """
        parts = name.split(" ")

        if len(parts) >= 4:
            device_type = parts[0]
            entity_number = parts[1]
            room_name = parts[2]
            level_name = " ".join(parts[3:])
        elif len(parts) >= 2:
            device_type = parts[0]
            entity_number = ""
            room_name = ""
            level_name = " ".join(parts[1:])
        else:
            device_type = parts[0] if parts else ""
            entity_number = ""
            room_name = ""
            level_name = ""

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

        parts_out = [level_name, room_name, device_type, entity_number]
        name = " ".join(p for p in parts_out if p)
        return name.title().strip()
