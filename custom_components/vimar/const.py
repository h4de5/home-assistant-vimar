"""Constant for Vimar component."""

import logging

_LOGGER = logging.getLogger(__package__)
PACKAGE_NAME = __package__

# Home-Assistant specific consts
DOMAIN = "vimar"
DOMAIN_CONFIG_YAML = "vimar_default_config"

CONF_TITLE = "title"
CONF_SCHEMA = "schema"
CONF_SECURE = "secure"
CONF_CERTIFICATE = "certificate"
CONF_GLOBAL_CHANNEL_ID = "global_channel_id"
CONF_IGNORE_PLATFORM = "ignore"
CONF_SAI_PIN = "sai_pin"

DEFAULT_USERNAME = "admin"
DEFAULT_SCHEMA = "https"
DEFAULT_SECURE = True
DEFAULT_PORT = 443
DEFAULT_CERTIFICATE = "rootCA.VIMAR.crt"
DEFAULT_VERIFY_SSL = True
DEFAULT_TIMEOUT = 6
DEFAULT_SCAN_INTERVAL = 8

# Energy meters refresh: the VIMAR firmware updates DPADD_OBJECT.CURRENT_VALUE
# for energy meter statuses only when someone explicitly calls runonelement
# GETVALUE on the status object id (the VIMAR UI does this from the energy
# management screen). Without that call, SELECT polling returns stale values.
CONF_ENERGY_REFRESH_INTERVAL = "energy_refresh_interval"
DEFAULT_ENERGY_REFRESH_INTERVAL = 30  # seconds; 0 disables the refresh

# Status names that need explicit GETVALUE on energy meter devices.
ENERGY_REFRESH_STATUS_NAMES = frozenset(
    {
        "energia_assoluta",
        "energia_parziale",
        "potenza_attiva",
        "potenza_reattiva",
    }
)

# Object types of energy meter devices (kept in sync with vimarlink.parse_device_type).
ENERGY_METER_OBJECT_TYPES = frozenset(
    {
        "CH_Misuratore",
        "CH_Carichi",
        "CH_Carichi_Custom",
        "CH_Carichi_3F",
        "CH_KNX_GENERIC_POWER_KW",
    }
)


# Device overrides
CONF_OVERRIDE = "device_override"

CONF_ENTITY_PREFIX = "entity_prefix"

CONF_USE_VIMAR_NAMING = "use_vimar_naming"
CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN = "friendly_name_room_name_at_begin"
CONF_DEVICES_LIGHTS_RE = "devices_as_lights_re"
CONF_DEVICES_BINARY_SENSOR_RE = "devices_as_binary_sensor_re"
CONF_DELETE_AND_RELOAD_ALL_ENTITIES = "delete_and_reload_all_entities"

# Cover position mode
CONF_COVER_POSITION_MODE = "cover_position_mode"
COVER_POSITION_MODE_AUTO = "auto"
COVER_POSITION_MODE_NATIVE = "native"
COVER_POSITION_MODE_TIME_BASED = "time_based"
COVER_POSITION_MODE_LEGACY = "legacy"  # Original master branch behavior
DEFAULT_COVER_POSITION_MODE = COVER_POSITION_MODE_AUTO

COVER_POSITION_MODES = [
    COVER_POSITION_MODE_AUTO,
    COVER_POSITION_MODE_NATIVE,
    COVER_POSITION_MODE_TIME_BASED,
    COVER_POSITION_MODE_LEGACY,
]

# vimar integration specific const

DEVICE_TYPE_LIGHTS = "light"
DEVICE_TYPE_COVERS = "cover"
DEVICE_TYPE_SWITCHES = "switch"
DEVICE_TYPE_CLIMATES = "climate"
DEVICE_TYPE_MEDIA_PLAYERS = "media_player"
DEVICE_TYPE_SCENES = "scene"
DEVICE_TYPE_FANS = "fan"
DEVICE_TYPE_SENSORS = "sensor"
DEVICE_TYPE_OTHERS = "other"
DEVICE_TYPE_ALARM = "alarm_control_panel"


VIMAR_CLIMATE_OFF = "VIMAR_CLIMATE_OFF"
VIMAR_CLIMATE_AUTO = "VIMAR_CLIMATE_AUTO"
VIMAR_CLIMATE_MANUAL = "VIMAR_CLIMATE_MANUAL"
VIMAR_CLIMATE_HEAT = "VIMAR_CLIMATE_HEAT"
VIMAR_CLIMATE_COOL = "VIMAR_CLIMATE_COOL"
VIMAR_CLIMATE_RIDUZIONE = "VIMAR_CLIMATE_RIDUZIONE"
VIMAR_CLIMATE_ASSENZA = "VIMAR_CLIMATE_ASSENZA"
VIMAR_CLIMATE_PROTEZIONE = "VIMAR_CLIMATE_PROTEZIONE"

# HA preset mode strings for VIMAR-specific modes
PRESET_CLIMATE_AUTO = "auto"
PRESET_CLIMATE_PROTECTION = "protezione"


VIMAR_CLIMATE_OFF_I = "0"
VIMAR_CLIMATE_AUTO_I = "8"
VIMAR_CLIMATE_MANUAL_I = "6"

VIMAR_CLIMATE_HEAT_I = "0"
VIMAR_CLIMATE_COOL_I = "1"

VIMAR_CLIMATE_RIDUZIONE_I = "4"
VIMAR_CLIMATE_PROTEZIONE_I = "3"

VIMAR_CLIMATE_OFF_II = "6"
VIMAR_CLIMATE_AUTO_II = "0"
VIMAR_CLIMATE_MANUAL_II = "1"
VIMAR_CLIMATE_RIDUZIONE_II = "2"
VIMAR_CLIMATE_ASSENZA_II = "3"
VIMAR_CLIMATE_PROTEZIONE_II = "4"

VIMAR_CLIMATE_NEUTRAL_II = "0"
VIMAR_CLIMATE_HEAT_II = "2"
VIMAR_CLIMATE_COOL_II = "1"

AVAILABLE_PLATFORMS = {
    DEVICE_TYPE_LIGHTS: "light",
    DEVICE_TYPE_COVERS: "cover",
    DEVICE_TYPE_SWITCHES: "switch",
    DEVICE_TYPE_CLIMATES: "climate",
    DEVICE_TYPE_MEDIA_PLAYERS: "media_player",
    DEVICE_TYPE_SCENES: "scene",
    # DEVICE_TYPE_FANS: 'fan',
    DEVICE_TYPE_SENSORS: "sensor",
    # DEVICE_TYPE_OTHERS: ''
}
DEVICE_TYPE_BINARY_SENSOR = "binary_sensor"
PLATFORMS = [
    DEVICE_TYPE_ALARM,
    DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_LIGHTS,
    DEVICE_TYPE_COVERS,
    DEVICE_TYPE_SWITCHES,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_MEDIA_PLAYERS,
    DEVICE_TYPE_SCENES,
    DEVICE_TYPE_SENSORS,
]


# VIMAR_UNIQUE_ID = "vimar_unique_id"
