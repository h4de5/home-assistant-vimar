"""Constant for Vimar component."""

# Home-Assistant specific consts
DOMAIN = "vimar_platform"

CONF_SCHEMA = "schema"
CONF_CERTIFICATE = "certificate"

DEFAULT_USERNAME = "admin"
DEFAULT_SCHEMA = "https"
DEFAULT_PORT = 443
DEFAULT_CERTIFICATE = "rootCA.VIMAR.crt"

# vimar integration specific const

DEVICE_TYPE_LIGHTS = "lights"
DEVICE_TYPE_COVERS = "covers"
DEVICE_TYPE_SWITCHES = "switches"
DEVICE_TYPE_CLIMATES = "climates"
DEVICE_TYPE_FANS = "fans"
DEVICE_TYPE_OTHERS = "others"


VIMAR_CLIMATE_AUTO = '8'
VIMAR_CLIMATE_MANUAL = '6'
VIMAR_CLIMATE_OFF = '0'

VIMAR_CLIMATE_HEAT = '0'
VIMAR_CLIMATE_COOL = '1'
