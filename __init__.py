"""Vimar Platform integration."""
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PORT, CONF_HOST, CONF_PASSWORD, CONF_USERNAME)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.cover import (
    DEVICE_CLASS_SHUTTER, DEVICE_CLASS_WINDOW, DEVICE_CLASS_SHADE)
from datetime import timedelta
import homeassistant.helpers.config_validation as cv
import logging
import asyncio
import os
import voluptuous as vol
from . import vimarlink
from .const import (
    DOMAIN, CONF_SCHEMA, CONF_CERTIFICATE, DEFAULT_USERNAME, DEFAULT_SCHEMA, DEFAULT_PORT
)

# from . import vimarlink
# see some examples: https://github.com/pnbruckner/homeassistant-config/blob/master/custom_components/amcrest/__init__.py
# https://github.com/peterbuga/HASS-sonoff-ewelink/blob/master/sonoff/__init__.py

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SCHEMA, default=DEFAULT_SCHEMA): cv.string,
        vol.Optional(CONF_CERTIFICATE): cv.string,

    })
}, extra=vol.ALLOW_EXTRA)


# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
# PLATFORM_SCHEMA = vol.Schema(
#     {
#         vol.Required(CONF_HOST): cv.string,
#         vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
#         vol.Required(CONF_PASSWORD): cv.string,
#     }
# )


# CONFIG_SCHEMA = vol.extend({
#     DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
#         vol.Required(CONF_HOST): cv.string,
#         vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
#         vol.Required(CONF_PASSWORD): cv.string,
#         vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
#         vol.Optional(CONF_SCHEMA, default=DEFAULT_SCHEMA): cv.schema,
#     })])
# }, extra=vol.ALLOW_EXTRA)
# CONFIG_SCHEMA = CONFIG_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Required(CONF_USERNAME, default="admin"): cv.string,
#     vol.Required(CONF_PASSWORD): cv.string
# })
# Import the device class from the component that you want to support
# DEVICE_SCHEMA = vol.Schema({
#     vol.Required(CONF_NAME): cv.string
# })

@asyncio.coroutine
async def async_setup(hass: HomeAssistantType, config: ConfigType):
    # def setup(hass, config):
    """Connect to the Vimar Webserver, verify login and read all devices."""
    """Split up devices into supported groups based on their names."""

    # Data that you want to share with your platforms
    # hass.data[DOMAIN] = {
    #     "temperature": 23
    # }

    # hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)

    # _LOGGER.info("Vimar Config: ")
    # _LOGGER.info(config)

    devices = {}
    vimarconfig = config[DOMAIN]

    schema = vimarconfig.get(CONF_SCHEMA)
    host = vimarconfig.get(CONF_HOST)
    port = vimarconfig.get(CONF_PORT)
    username = vimarconfig.get(CONF_USERNAME)
    password = vimarconfig.get(CONF_PASSWORD)
    certificate = vimarconfig.get(CONF_CERTIFICATE)

    # initialize a new VimarLink object
    vimarconnection = vimarlink.VimarLink(
        schema, host, port, username, password, certificate)

    # if certificate is set, but file is not there - download it from the webserver
    if len(certificate) != 0 and os.path.isfile(certificate) == False:
        _LOGGER.error("Could not connect to Vimar Webserver " + host)
        if vimarconnection.installCertificate() == False:
            raise PlatformNotReady

    # Verify that passed in configuration works
    # starting it outside MainThread
    valid_login = await hass.async_add_executor_job(vimarconnection.check_login)

    if not valid_login:
        _LOGGER.error("Could not connect to Vimar Webserver " + host)
        raise PlatformNotReady

    # save vimar connection into hass data to share it with other platforms
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["connection"] = vimarconnection

    maingroups = await hass.async_add_executor_job(vimarconnection.get_main_groups)

    if not maingroups or len(maingroups) == 0:
        _LOGGER.error(
            "Could not find any groups or rooms on Vimar Webserver " + host)
        return False

    # load devices
    devices = await hass.async_add_executor_job(vimarconnection.get_devices)

    if not devices or len(devices) == 0:
        _LOGGER.error("Could not find any devices on Vimar Webserver " + host)
        return False

    lights = {}
    covers = {}
    switches = {}
    climates = {}
    others = {}

    if len(devices) != 0:
        for device_id, device in devices.items():
            device_type, device_class, icon = parse_device_type(device)

            device["device_type"] = device_type
            device["device_class"] = device_class
            device["icon"] = icon
            if device_type == "lights":
                lights[device_id] = device
            elif device_type == "covers":
                covers[device_id] = device
            elif device_type == "switches":
                switches[device_id] = device
            elif device_type == "climates":
                climates[device_id] = device
            else:
                others[device_id] = device

    # save devices into hass data to share it with other platforms
    hass.data[DOMAIN]["lights"] = lights
    hass.data[DOMAIN]["covers"] = covers
    hass.data[DOMAIN]["switches"] = switches
    # there should not be too many requests per second
    # limit scan_interval depending on items
    scan_interval = max(3, int(len(devices) / 500 * 60))
    hass.data[DOMAIN]["scan_interval"] = timedelta(seconds=scan_interval)

    # if len(devices) != 0:
    #     # for device_id, device_config in config.get(CONF_DEVICES, {}).items():
    #     # for device_id, device_config in devices.items():
    #     #     name = device_config["name"]
    #     #     lights.append(VimarLight(name, device_id, vimarconnection))
    #     for device_id, device in devices.items():

    # States are in the format DOMAIN.OBJECT_ID.
    # hass.states.async_set("vimar_platform.Hello_World", "Works!")

    # vimarconnection = vimarlink.VimarLink(host, username, password)

    # # Verify that passed in configuration works
    # if not vimarconnection.is_valid_login():
    #     _LOGGER.error("Could not connect to Vimar Webserver "+ host)
    #     return False

# Use `listen_platform` to register a callback for these events.

    # homeassistant.helpers.discovery.async_load_platform(hass, component, platform, discovered, hass_config)

    if lights and len(lights) > 0:
        hass.async_create_task(hass.helpers.discovery.async_load_platform(
            "light", DOMAIN, {"hass_data_key": "lights"}, config))
    if covers and len(covers) > 0:
        hass.async_create_task(hass.helpers.discovery.async_load_platform(
            "cover", DOMAIN, {"hass_data_key": "covers"}, config))
    if switches and len(switches) > 0:
        hass.async_create_task(hass.helpers.discovery.async_load_platform(
            "switch", DOMAIN, {"hass_data_key": "switches"}, config))

    # hass.helpers.discovery.load_platform("light", DOMAIN, {}, config)
    # hass.helpers.discovery.load_platform("cover", DOMAIN, {}, config)
    # hass.helpers.discovery.load_platform("switch", DOMAIN, {}, config)

    # Return boolean to indicate that initialization was successfully.
    return True


# async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigEntry):
#     """Unload a UPnP/IGD device from a config entry."""
#     udn = config_entry.data["udn"]
#     device = hass.data[DOMAIN]["devices"][udn]

#     # remove port mapping
#     _LOGGER.debug("Deleting port mappings")
#     await device.async_delete_port_mappings()

#     # remove sensors
#     _LOGGER.debug("Deleting sensors")
#     dispatcher.async_dispatcher_send(hass, SIGNAL_REMOVE_SENSOR, device)

#     return True


def parse_device_type(device):
    device_type = "others"
    # see: https://www.home-assistant.io/docs/configuration/customizing-devices/#device-class
    device_class = None
    # see: https://materialdesignicons.com/cdn/2.0.46/
    icon = None

    # mdi:garage - mdi:garage-open
    # mdi:lamp
    # mdi:border-all mdi:border-outside
    # mdi:lock mdi:lock-open-outline

    # mdi-lightbulb
    # mdi-lightbulb-on
    # mdi-lightbulb-on-outline
    # mdi-lightbulb-outline
    # mdi-ceiling-light
    # mdi-sunglasses
    # mdi-fan
    # mdi-power-plug
    # mdi-power-plug-off
    # mdi-speedometer - DIMMER
    # mdi-timelapse - DIMMER

    if device["object_type"] == "CH_Main_Automation":
        if device["object_name"].find("VENTILATOR") != -1:
            device_type = "switches"
            icon = "mdi:fan"
        elif device["object_name"].find("LAMPE") != -1:
            device_type = "lights"
            icon = "mdi:lightbulb"
        elif device["object_name"].find("LICHT") != -1:
            device_type = "lights"
            icon = "mdi:ceiling-light"
        elif device["object_name"].find("STECKDOSE") != -1:
            device_type = "switches"
            device_class = "plug"
            icon = "mdi:power-plug"
        # else:
        #     device_type = "lights"
        #     icon = "mdi:ceiling-light"

    elif device["object_type"] == "CH_Dimmer_Automation":
        device_type = "lights"
        icon = "mdi:speedometer"  # mdi:rotate-right
    elif device["object_type"] == "CH_ShutterWithoutPosition_Automation":
        if device["object_name"].find("F-FERNBEDIENUNG") != -1:
            device_class = DEVICE_CLASS_WINDOW
            device_type = "covers"
        else:
            # could be: shade, blind, window
            # see: https://www.home-assistant.io/integrations/cover/
            device_class = DEVICE_CLASS_SHUTTER
            device_type = "covers"
    elif device["object_type"] == "CH_Clima":
        device_type = "climates"
    else:
        _LOGGER.warning(
            "Unknown object_type returned from the web server: " + device["object_type"])

    return device_type, device_class, icon


def format_name(name):

    # _LOGGER.info("Splitting name: " + name)

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
            room_name = 'ALL'
            level_name = parts[1]

            for i in range(2, len(parts)):
                level_name += " " + parts[i]
        else:
            device_type = parts[0]
            entity_number = ''
            room_name = 'ALL'
            level_name = 'LEVEL'

            for i in range(2, len(parts)):
                level_name += " " + parts[i]

    # device_type, entity_number, room_name, *level_name = name.split(' ')

    device_type = device_type.replace('LUCE', '')
    device_type = device_type.replace('TAPPARELLA', '')

    device_type = device_type.replace('LICHT', '')
    device_type = device_type.replace('ROLLLADEN', '')
    device_type = device_type.replace('F-FERNBEDIENUNG', 'FENSTER')
    device_type = device_type.replace('VENTILATOR', '')
    device_type = device_type.replace('STECKDOSE', '')

    name = "%s %s %s %s" % (level_name, room_name,
                            device_type, entity_number)

    # change case
    return name.title()
