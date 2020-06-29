"""Constant for Vimar component."""

# Home-Assistant specific consts
DOMAIN = "vimar_platform"

CONF_SCHEMA = "schema"
CONF_CERTIFICATE = "certificate"

DEFAULT_USERNAME = "admin"
DEFAULT_SCHEMA = "https"
DEFAULT_PORT = 443
DEFAULT_CERTIFICATE = "rootCA.VIMAR.crt"
DEFAULT_TIMEOUT = 6

# vimar integration specific const

DEVICE_TYPE_LIGHTS = "lights"
DEVICE_TYPE_COVERS = "covers"
DEVICE_TYPE_SWITCHES = "switches"
DEVICE_TYPE_CLIMATES = "climates"
DEVICE_TYPE_SCENES = "scenes"
DEVICE_TYPE_FANS = "fans"
DEVICE_TYPE_SENSORS = "sensors"
DEVICE_TYPE_OTHERS = "others"


VIMAR_CLIMATE_OFF_I = '0'
VIMAR_CLIMATE_AUTO_I = '8'
VIMAR_CLIMATE_MANUAL_I = '6'

VIMAR_CLIMATE_OFF_II = '6'
VIMAR_CLIMATE_AUTO_II = '0'
VIMAR_CLIMATE_MANUAL_II = '1'


VIMAR_CLIMATE_HEAT = '0'
VIMAR_CLIMATE_COOL = '1'
