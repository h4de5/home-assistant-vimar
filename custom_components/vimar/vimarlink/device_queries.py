"""SQL queries for Vimar device discovery and status."""

from __future__ import annotations

import logging
from typing import TypedDict

_LOGGER = logging.getLogger(__name__)


class VimarDevice(TypedDict):
    """Single Vimar device type definition."""

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


def get_room_devices_query(room_ids: str, start: int, limit: int) -> str:
    """Generate SQL query to fetch devices belonging to rooms."""
    return f"""SELECT GROUP_CONCAT(r2.PARENTOBJ_ID) AS room_ids, o2.ID AS object_id,
o2.NAME AS object_name, o2.VALUES_TYPE as object_type,
o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT_RELATION r2
INNER JOIN DPADD_OBJECT o2 ON r2.CHILDOBJ_ID = o2.ID AND o2.type = "BYMEIDX"
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ" AND o3.NAME != ""
WHERE r2.PARENTOBJ_ID IN ({room_ids}) AND r2.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
GROUP BY o2.ID, o2.NAME, o2.VALUES_TYPE, o3.ID, o3.NAME, o3.CURRENT_VALUE
LIMIT {start}, {limit};"""


def get_remote_devices_query(start: int, limit: int) -> str:
    """Generate SQL query to fetch remotely triggerable devices.

    FIX #4: removed duplicate columns object_name and object_type that appeared
    twice in the SELECT due to a copy-paste residue. The parser would silently
    overwrite the first value with the second; now each column appears once.
    """
    return f"""SELECT '' AS room_ids, o2.id AS object_id, o2.name AS object_name, o2.VALUES_TYPE AS object_type,
o3.ID AS status_id, o3.NAME AS status_name, o3.OPTIONALP as status_range, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT AS o2
INNER JOIN (SELECT CLASSNAME,IS_EVENT,IS_EXECUTABLE FROM DPAD_WEB_PHPCLASS) AS D_WP ON o2.PHPCLASS=D_WP.CLASSNAME
INNER JOIN DPADD_OBJECT_RELATION r3 ON o2.ID = r3.PARENTOBJ_ID AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type IN ('BYMETVAL','BYMEOBJ') AND o3.NAME != ""
WHERE o2.OPTIONALP NOT LIKE "%%restricted%%" AND o2.IS_VISIBLE=1 AND o2.OWNED_BY!="SYSTEM" AND o2.OPTIONALP LIKE "%%category=%%"
LIMIT {start}, {limit};"""


def get_device_status_query(object_id: str) -> str:
    """Generate SQL query to fetch status for a single device."""
    return f"""SELECT o3.ID AS status_id, o3.NAME AS status_name, o3.CURRENT_VALUE AS status_value
FROM DPADD_OBJECT_RELATION r3
INNER JOIN DPADD_OBJECT o3 ON r3.CHILDOBJ_ID = o3.ID AND o3.type = "BYMEOBJ"
WHERE r3.PARENTOBJ_ID IN ({object_id}) AND r3.RELATION_WEB_TIPOLOGY = "BYME_IDXOBJ_RELATION"
ORDER BY o3.ID;"""


def get_status_only_query(status_ids: list[int]) -> str:
    """Generate lightweight SQL query to fetch only current values.

    This is optimized for polling - only fetches CURRENT_VALUE without JOINs.
    """
    if not status_ids:
        return ""
    ids_csv = ",".join(str(int(sid)) for sid in status_ids)
    return f"SELECT ID AS status_id, CURRENT_VALUE AS status_value FROM DPADD_OBJECT WHERE ID IN ({ids_csv});"


def get_room_ids_query() -> str:
    """Generate SQL query to fetch main room groups."""
    return """SELECT o1.id as id, o1.name as name
FROM DPADD_OBJECT o0
INNER JOIN DPADD_OBJECT_RELATION r1 ON o0.ID = r1.PARENTOBJ_ID AND r1.RELATION_WEB_TIPOLOGY = "GENERIC_RELATION"
INNER JOIN DPADD_OBJECT o1 ON r1.CHILDOBJ_ID = o1.ID AND o1.type = "GROUP"
WHERE o0.NAME = "_DPAD_DBCONSTANT_GROUP_MAIN";"""


# ---------------------------------------------------------------------------
# SAI2 alarm diagnostic queries (temporary – remove after integration)
# ---------------------------------------------------------------------------

def get_sai2_groups_query() -> str:
    """Fetch all SAI2 alarm areas (groups) with their child states.

    Uses the existing DPAD_SAI2GATEWAY_SAI2GROUPCHILDREN view which JOINs
    SAI2_GROUP -> SAI2_GROUP_CHILD via SAI2_GROUP_CHILD_RELATION.
    """
    return """SELECT GID, GNAME, CID, CNAME, CURRENT_VALUE
FROM DPAD_SAI2GATEWAY_SAI2GROUPCHILDREN
ORDER BY GID, CID;"""


def get_sai2_zones_query() -> str:
    """Fetch all SAI2 alarm zones with their child states.

    Uses the existing DPAD_SAI2GATEWAY_SAI2ZONECHILDREN view which JOINs
    SAI2_ZONE -> SAI2_ZONE_CHILD via SAI2_ZONE_CHILD_RELATION.
    """
    return """SELECT ZID, GNAME, CID, CNAME, CURRENT_VALUE
FROM DPAD_SAI2GATEWAY_SAI2ZONECHILDREN
ORDER BY ZID, CID;"""


def get_sai2_area_values_query(group_ids: list[str]) -> str:
    """Fetch live SAI2 area state from DPADD_OBJECT.CURRENT_VALUE.

    Unlike DPAD_SAI2GATEWAY_SAI2GROUPCHILDREN (whose CURRENT_VALUE never
    updates after commands), the SAI2 group object rows in DPADD_OBJECT
    are updated immediately by the Vimar web server after each command.
    The value is an 8-character binary bitmask, e.g. '00001001' for PAR.
    """
    ids_csv = ",".join(str(int(gid)) for gid in group_ids)
    return (
        f"SELECT ID as gid, CURRENT_VALUE as current_value "
        f"FROM DPADD_OBJECT WHERE ID IN ({ids_csv});"
    )


def get_sai2_zone_to_group_query() -> str:
    """Fetch the mapping of SAI2 zones to their parent groups (areas).

    Uses DPAD_SAI2GATEWAY_SAI2ZONEINTOGROUPS view which JOINs
    group children to zones via SAI2_GROUP_CHILD_ZONE_RELATION.
    Returns GID (group/area ID), GNAME (area name), ZID (zone ID),
    ZNAME (zone name).
    """
    return """SELECT DISTINCT GID, GNAME, ZID, ZNAME
FROM DPAD_SAI2GATEWAY_SAI2ZONEINTOGROUPS
ORDER BY GID, ZID;"""
