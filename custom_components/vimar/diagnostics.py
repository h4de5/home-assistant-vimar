from __future__ import annotations

from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import *
from .vimar_coordinator import VimarDataUpdateCoordinator


import json

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: VimarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = { }
    data["rooms"] = coordinator.vimarconnection._rooms
    data["devices"] = coordinator.vimarproject._devices
    data["last_get_room_devices"] = coordinator.vimarconnection._last_get_room_devices_result 
    data["last_get_remote_devices"] = coordinator.vimarconnection._last_get_remote_devices_result
    data["last_get_remote_devices_status"] = coordinator.vimarconnection._last_get_remote_devices_status_result
    json_str = json.dumps(serialize(data), default=str)
    #sensitive_values = { CONF_EMAIL, CONF_PASSWORD };
    #for key in sensitive_values:
    #    val = config[key]
    #    json_str = json_str.replace(val, "***" + key + "***" )
    masked_data = json.loads(json_str)
    return masked_data

def serialize(obj):
    from datetime import datetime
    """Convert dict, list, BaseModel into JSON-serializable structures."""
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize(v) for v in obj]
    elif hasattr(obj, "dict"):
        return serialize(obj.dict())  # ricorsivo anche dentro BaseModel annidati
    elif isinstance(obj, datetime):
        return obj.isoformat()  # datetime → string ISO
    else:
        return obj