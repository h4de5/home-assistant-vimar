"""Platform for light integration."""
# credits to https://github.com/GeoffAtHome/lightwaverf-home-assistant-lights/blob/master/lightwave.py

from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
import asyncio
#import queue
#import threading
#import socket
import time
# import logging
# import variables set in __init__.py
# from . import vimarconnection
# from . import vimarlink
from . import DOMAIN

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

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Light platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Light started!")
    lights = []

    # _LOGGER.info("Vimar Plattform Config: ")
    # _LOGGER.info(config)
    _LOGGER.info("discovery_info")
    _LOGGER.info(discovery_info)
    # _LOGGER.info(hass.config)
    # this will give you overall hass config, not configuration.yml
    # hassconfig = hass.config.as_dict()

    # vimarconfig = config

    # _LOGGER.info(vimarconfig)

    # host = vimarconfig.get(CONF_HOST)
    # username = vimarconfig.get(CONF_USERNAME)
    # password = vimarconfig.get(CONF_PASSWORD)

    # vimarconnection = vimarlink.VimarLink(host, username, password)

    # # Verify that passed in configuration works
    # if not vimarconnection.is_valid_login():
    #     _LOGGER.error("Could not connect to Vimar Webserver "+ host)
    #     return False

    # _LOGGER.info(config)
    vimarconnection = hass.data[DOMAIN]
    
    # load Main Groups
    vimarconnection.getMainGroups()

    # load devices
    devices = vimarconnection.getDevices()

    if len(devices) != 0:
        # for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        # for device_id, device_config in devices.items():
        #     name = device_config['name']
        #     lights.append(VimarLight(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            lights.append(VimarLight(device, device_id, vimarconnection))


    # fallback
    if len(lights) == 0:
        # Config is empty so generate a default set of switches
        for room in range(1, 2):
            for device in range(1, 2):
                name = "Room " + str(room) + " Device " + str(device)
                device_id = "R" + str(room) + "D" + str(device)
                lights.append(VimarLight({'object_name': name}, device_id, link))

    async_add_entities(lights)
    _LOGGER.info("Vimar Light complete!")


def calculate_brightness(brightness):
    """Scale brightness from 0..255 to 0..100"""
    return round((brightness * 100) / 255)
# end dev calculate_brightness

def recalculate_brightness(brightness):
    """Scale brightness from 0..100 to 0..255"""
    return round((brightness * 255) / 100)
# end dev recalculate_brightness


class VimarLight(Light):
    """ Provides a Vimar light. """

    def __init__(self, device, device_id, vimarconnection):
        self._device = device
        self._name = self._device['object_name']
        self._device_id = device_id
        self._state = False
        self._brightness = 255
        self.reset_status()
        self._vimarconnection = vimarconnection

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def should_poll(self):
        """ polling needed for a Vimar light. """
        return True

    def update(self):
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        # self._light.update()
        # self._state = self._light.is_on()
        # self._brightness = self._light.brightness
        self._device = self._vimarconnection.getDevice(self._device_id)
        self.reset_status()
        
    @property
    def name(self):
        """ Returns the name of the LightWave light. """
        return self._name

    @property
    def brightness(self):
        """ Brightness of this light between 0..255. """
        return self._brightness

    @property
    def is_on(self):
        """ True if the LightWave light is on. """
        return self._state

    def reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[self._device['status']['on/off']['status_value'] != '0']
            if 'value' in self._device['status']:
                self._brightness = recalculate_brightness(int(self._device['status']['value']['status_value']))

    async def async_turn_on(self, **kwargs):
        """ Turn the Vimar light on. """

        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = True
                self._vimarconnection.updateStatus(self._device['status']['on/off']['status_id'], '1')
                
        if ATTR_BRIGHTNESS in kwargs:
            if 'status' in self._device:
                if 'value' in self._device['status']:
                    self._brightness = kwargs[ATTR_BRIGHTNESS]
                    brightness_value = calculate_brightness(self._brightness)
                    self._vimarconnection.updateStatus(self._device['status']['value']['status_id'], brightness_value)

        # if ATTR_BRIGHTNESS in kwargs:
        #     self._brightness = kwargs[ATTR_BRIGHTNESS]
        #     brightness_value = calculate_brightness(self._brightness)
        #     # F1 = Light on and F0 = light off. FdP[0..32] is brightness. 32 is
        #     # full. We want that when turning the light on.
        #     msg = '321,!%sFdP%d|Lights %d|%s' % (
        #         self._device_id, brightness_value, brightness_value, self._name)
        # else:
        #     msg = '321,!%sFdP32|Turn On|%s' % (self._device_id, self._name)

        # self._vimarconnection.send_message(msg)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the Vimar light off. """

        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = False
                self._vimarconnection.updateStatus(self._device['status']['on/off']['status_id'], '0')

        self.async_schedule_update_ha_state()

        
# end class VimarLight


# class AwesomeLight(Light):
#     """Representation of an Awesome Light."""

#     def __init__(self, light):
#         """Initialize an AwesomeLight."""
#         self._light = light
#         self._name = light.name
#         self._state = None
#         self._brightness = None

#     @property
#     def name(self):
#         """Return the display name of this light."""
#         return self._name

#     @property
#     def brightness(self):
#         """Return the brightness of the light.

#         This method is optional. Removing it indicates to Home Assistant
#         that brightness is not supported for this light.
#         """
#         return self._brightness

#     @property
#     def is_on(self):
#         """Return true if light is on."""
#         return self._state

#     def turn_on(self, **kwargs):
#         """Instruct the light to turn on.

#         You can skip the brightness part if your light does not support
#         brightness control.
#         """
#         self._light.brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
#         self._light.turn_on()

#     def turn_off(self, **kwargs):
#         """Instruct the light to turn off."""
#         self._light.turn_off()

#     def update(self):
#         """Fetch new state data for this light.

#         This is the only method that should fetch new data for Home Assistant.
#         """
#         # self._light.update()
#         self._state = self._light.is_on()
#         self._brightness = self._light.brightness
