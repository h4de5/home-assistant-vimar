"""Vimar Platform integration."""
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
import logging
import asyncio
import voluptuous as vol
from . import vimarlink

# from . import vimarlink
# see some examples: https://github.com/pnbruckner/homeassistant-config/blob/master/custom_components/amcrest/__init__.py
# https://github.com/peterbuga/HASS-sonoff-ewelink/blob/master/sonoff/__init__.py

DOMAIN = "vimar_platform"

_LOGGER = logging.getLogger(__name__)

# vimarconnection = None

# Validation of the user"s configuration
# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Required(CONF_USERNAME, default="admin"): cv.string,
#     vol.Required(CONF_PASSWORD): cv.string
# })
# CONFIG_SCHEMA = vol.extend({
#     DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
#         vol.Required(CONF_HOST): cv.string,
#         vol.Required(CONF_USERNAME): cv.string,
#         vol.Required(CONF_PASSWORD): cv.string,
#         # vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
#         # vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
#         # vol.Optional(CONF_AUTHENTICATION, default=HTTP_BASIC_AUTHENTICATION):
#         #     vol.All(vol.In(AUTHENTICATION_LIST)),
#     })])
# }, extra=vol.ALLOW_EXTRA)

# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Required(CONF_USERNAME, default="admin"): cv.string,
#     vol.Required(CONF_PASSWORD): cv.string
# })

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
async def async_setup(hass, config):
# def setup(hass, config):
    """Setup our skeleton component."""
    """Your controller/hub specific code."""

    # Data that you want to share with your platforms
    # hass.data[DOMAIN] = {
    #     "temperature": 23
    # }

    # hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)

    # _LOGGER.info("Vimar Config: ")
    # _LOGGER.info(config)

    devices = {}
    vimarconfig = config[DOMAIN]

    host = vimarconfig.get(CONF_HOST)
    username = vimarconfig.get(CONF_USERNAME)
    password = vimarconfig.get(CONF_PASSWORD)

    # initialize a new VimarLink object
    vimarconnection = vimarlink.VimarLink(host, username, password)
    
    # Verify that passed in configuration works
    # starting it outside MainThread
    valid_login = await hass.async_add_executor_job(vimarconnection.check_login)
    
    if not valid_login:
        _LOGGER.error("Could not connect to Vimar Webserver "+ host)
        return False

    # save vimar connection into hass data to share it with other platforms
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["connection"] = vimarconnection

    maingroups = await hass.async_add_executor_job(vimarconnection.get_main_groups)

    if not maingroups or len(maingroups) == 0:
        _LOGGER.error("Could not find any groups or rooms on Vimar Webserver "+ host)
        return False

    # load devices
    devices = await hass.async_add_executor_job(vimarconnection.get_devices)

    if not devices or len(devices) == 0:
        _LOGGER.error("Could not find any devices on Vimar Webserver "+ host)
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
        hass.async_create_task(hass.helpers.discovery.async_load_platform("light", DOMAIN, {"hass_data_key" : "lights"}, config))
    if covers and len(covers) > 0:
        hass.async_create_task(hass.helpers.discovery.async_load_platform("cover", DOMAIN, {"hass_data_key" : "covers"}, config))
    if switches and len(switches) > 0:
        hass.async_create_task(hass.helpers.discovery.async_load_platform("switch", DOMAIN, {"hass_data_key" : "switches"}, config))

    # hass.helpers.discovery.load_platform("light", DOMAIN, {}, config)
    # hass.helpers.discovery.load_platform("cover", DOMAIN, {}, config)
    # hass.helpers.discovery.load_platform("switch", DOMAIN, {}, config)

    # Return boolean to indicate that initialization was successfully.
    return True


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
            icon =  "mdi:lightbulb"
        elif device["object_name"].find("LICHT") != -1:
            device_type = "lights"
            icon =  "mdi:ceiling-light"
        elif device["object_name"].find("STECKDOSE") != -1:
            device_type = "switches"
            device_class = "plug"
            icon =  "mdi:power-plug"
        # else:
        #     device_type = "lights"
        #     icon = "mdi:ceiling-light"

    elif device["object_type"] == "CH_Dimmer_Automation":
        device_type = "lights"
        icon = "mdi:speedometer" # mdi:rotate-right
    elif device["object_type"] == "CH_ShutterWithoutPosition_Automation":
        if device["object_name"].find("F-FERNBEDIENUNG") != -1:
            device_class = "window"
            device_type = "covers"
        else:
            # could be: shade, blind, window
            # see: https://www.home-assistant.io/integrations/cover/
            device_class = "shutter" 
            device_type = "covers"
    elif device["object_type"] == "CH_Clima":
        device_type = "climates"
    
    return device_type, device_class, icon