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

DOMAIN = 'vimar_platform'

_LOGGER = logging.getLogger(__name__)

# vimarconnection = None

# Validation of the user's configuration
# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Required(CONF_USERNAME, default='admin'): cv.string,
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
#     vol.Required(CONF_USERNAME, default='admin'): cv.string,
#     vol.Required(CONF_PASSWORD): cv.string
# })

# CONFIG_SCHEMA = CONFIG_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Required(CONF_USERNAME, default='admin'): cv.string,
#     vol.Required(CONF_PASSWORD): cv.string
# })


# Import the device class from the component that you want to support
# DEVICE_SCHEMA = vol.Schema({
#     vol.Required(CONF_NAME): cv.string
# })

@asyncio.coroutine
def async_setup(hass, config):
# def setup(hass, config):
    """Setup our skeleton component."""
    """Your controller/hub specific code."""

    # Data that you want to share with your platforms
    # hass.data[DOMAIN] = {
    #     'temperature': 23
    # }

    # hass.helpers.discovery.load_platform('sensor', DOMAIN, {}, config)

    # _LOGGER.info("Vimar Config: ")
    # _LOGGER.info(config)

    vimarconfig = config[DOMAIN]

    host = vimarconfig.get(CONF_HOST)
    username = vimarconfig.get(CONF_USERNAME)
    password = vimarconfig.get(CONF_PASSWORD)

    vimarconnection = vimarlink.VimarLink(host, username, password)

    # Verify that passed in configuration works
    if not vimarconnection.is_valid_login():
        _LOGGER.error("Could not connect to Vimar Webserver "+ host)
        return False

    # save vimar connection into hass data to share it with outer platforms
    hass.data[DOMAIN] = vimarconnection

    # States are in the format DOMAIN.OBJECT_ID.
    # hass.states.async_set('vimar_platform.Hello_World', 'Works!')   
    
    # vimarconnection = vimarlink.VimarLink(host, username, password)

    # # Verify that passed in configuration works
    # if not vimarconnection.is_valid_login():
    #     _LOGGER.error("Could not connect to Vimar Webserver "+ host)
    #     return False

    hass.helpers.discovery.load_platform('light', DOMAIN, {}, config)
    hass.helpers.discovery.load_platform('cover', DOMAIN, {}, config)
    hass.helpers.discovery.load_platform('switch', DOMAIN, {}, config)

    # Return boolean to indicate that initialization was successfully.
    return True
