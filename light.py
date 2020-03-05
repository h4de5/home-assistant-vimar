"""Platform for light integration."""
# credits to https://github.com/GeoffAtHome/lightwaverf-home-assistant-lights/blob/master/lightwave.py

from homeassistant.components.light import (Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS)
from datetime import timedelta
from time import gmtime, strftime, localtime, mktime
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
import asyncio

# import variables set in __init__.py
# from . import vimarconnection
# from . import vimarlink
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Light platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Light started!")
    lights = []

    # _LOGGER.info("Vimar Plattform Config: ")
    # # _LOGGER.info(config)
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
    vimarconnection = hass.data[DOMAIN]['connection']
    
    # # load Main Groups
    # vimarconnection.getMainGroups()

    # # load devices
    # devices = vimarconnection.getDevices()
    # devices = hass.data[DOMAIN]['devices']
    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        # for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        # for device_id, device_config in devices.items():
        #     name = device_config['name']
        #     lights.append(VimarLight(name, device_id, vimarconnection))
        for device_id, device in devices.items():
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

# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

class VimarLight(Light):
    """ Provides a Vimar lights. """

    ICON = "mdi:ceiling-light"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the light."""
        self._device = device
        self._name = self._device['object_name']
        # change case
        self._name = self._name.title()
        self._device_id = device_id
        self._state = False
        self._brightness = 255
        self._reset_status()
        self._vimarconnection = vimarconnection

    ####### default properties

    @property
    def should_poll(self):
        """ polling is needed for a Vimar device. """
        return True

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def color(self):
        """ Returns the name of the device. """
        return "red"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if 'icon' in self._device and self._device['icon']:
            return self._device['icon']
        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device['device_class']

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._device_id
    
    @property
    def available(self):
        """Return True if entity is available."""
        return True

    ####### light properties
    
    @property
    def is_on(self):
        """ True if the device is on. """
        return self._state

    @property
    def brightness(self):
        """ Brightness of this light between 0..255. """
        return self._brightness

    @property
    def supported_features(self):
        """Flag supported features."""
        if 'status' in self._device and self._device['status']:
            if 'value' in self._device['status']:
                return SUPPORT_BRIGHTNESS
        return 0

    ####### async getter and setter
    
    # def update(self):
    # see: https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        starttime = localtime()
        # strftime("%Y-%m-%d %H:%M:%S",
        # self._light.update()
        # self._state = self._light.is_on()
        # self._brightness = self._light.brightness
        # self._device = self._vimarconnection.getDevice(self._device_id)
        # self._device['status'] = self._vimarconnection.getDeviceStatus(self._device_id)
        old_status = self._device['status']
        self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
        self._reset_status()
        if old_status != self._device['status']:
            self.async_schedule_update_ha_state()

        _LOGGER.info("Vimar Light update finished after "+ str(mktime(localtime()) - mktime(starttime)) + "s "+ self._name)

    async def async_turn_on(self, **kwargs):
        """ Turn the Vimar light on. """

        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = True
                self._device['status']['on/off']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
                # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
                
        if ATTR_BRIGHTNESS in kwargs:
            if 'status' in self._device and self._device['status']:
                if 'value' in self._device['status']:
                    self._brightness = kwargs[ATTR_BRIGHTNESS]
                    brightness_value = calculate_brightness(self._brightness)
                    self._device['status']['value']['status_value'] = brightness_value
                    # self._vimarconnection.set_device_status(self._device['status']['value']['status_id'], brightness_value)
                    await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['value']['status_id'], brightness_value)

        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the Vimar light off. """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = False
                self._device['status']['on/off']['status_value'] = '0'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 0)

                self.async_schedule_update_ha_state()


    ####### private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[self._device['status']['on/off']['status_value'] != '0']
            if 'value' in self._device['status']:
                self._brightness = recalculate_brightness(int(self._device['status']['value']['status_value']))
            

        
# end class VimarLight
