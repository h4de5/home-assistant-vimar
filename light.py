"""Platform for light integration."""
# credits to https://github.com/GeoffAtHome/lightwaverf-home-assistant-lights/blob/master/lightwave.py

from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
import asyncio

# import variables set in __init__.py
# from . import vimarconnection
# from . import vimarlink
from . import DOMAIN

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
    # _LOGGER.info("discovery_info")
    # _LOGGER.info(discovery_info)
    # _LOGGER.info(hass.config)
    # this will give you overall hass config, not configuration.yml
    # hassconfig = hass.config.as_dict()

    # vimarconfig = config

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
            if (device['object_name'].find("ROLLLADEN") == -1 and 
                device['object_name'].find("STECKDOSE") == -1 and 
                device['object_name'].find("FERNBEDINUNG") == -1):
                lights.append(VimarLight(device, device_id, vimarconnection))


    # fallback
    # if len(lights) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             lights.append(VimarLight({'object_name': name}, device_id, link))

    if len(lights) != 0:
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
    """ Provides a Vimar lights. """

    ICON = "mdi:ceiling-light"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the light."""
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
        if 'status' in self._device:
            if 'value' in self._device['status']:
                return SUPPORT_BRIGHTNESS
        return 0

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
        """ Returns the name of the light. """
        return self._name

    @property
    def brightness(self):
        """ Brightness of this light between 0..255. """
        return self._brightness

    @property
    def is_on(self):
        """ True if the LightWave light is on. """
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._name.find("VENTILATOR") != -1:
            return "mdi:fan"
        elif self._name.find("DIMMER") != -1:
            return "mdi:speedometer"
        elif self._name.find("LAMPE") != -1:
            return "mdi:lightbulb"
        return self.ICON

        # return self.ICON

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
                self._vimarconnection.updateStatus(self._device['status']['on/off']['status_id'], 1)
                
        if ATTR_BRIGHTNESS in kwargs:
            if 'status' in self._device:
                if 'value' in self._device['status']:
                    self._brightness = kwargs[ATTR_BRIGHTNESS]
                    brightness_value = calculate_brightness(self._brightness)
                    self._vimarconnection.updateStatus(self._device['status']['value']['status_id'], brightness_value)

        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the Vimar light off. """
        if 'status' in self._device:
            if 'on/off' in self._device['status']:
                self._state = False
                self._vimarconnection.updateStatus(self._device['status']['on/off']['status_id'], 0)

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
