"""Platform for light integration."""
# credits to
# https://github.com/GeoffAtHome/lightwaverf-home-assistant-lights/blob/master/lightwave.py

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS)
try:
    from homeassistant.components.light import LightEntity
except ImportError:
    from homeassistant.components.light import Light as LightEntity
from datetime import timedelta
# from time import gmtime, strftime, localtime, mktime
from homeassistant.util import Throttle
# import homeassistant.helpers.config_validation as cv
import logging
# import asyncio

from .const import DOMAIN
from . import format_name

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
PARALLEL_UPDATES = 5


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
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
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


class VimarLight(LightEntity):
    """ Provides a Vimar lights. """

    ICON = "mdi:ceiling-light"

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    """ Return True if the state is based on our assumption instead of reading it from the device."""
    # assumed_state = False

    """ set entity_id, object_id manually due to possible duplicates """
    entity_id = "light." + "unset"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the light."""
        self._device = device
        self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        self._state = False
        self._brightness = 255
        self._reset_status()
        self._vimarconnection = vimarconnection

        # self.entity_id = "light." + self._device_id + "_" + \
        #     re.sub("[^0-9a-z_]+", "_", self._name.lower())

        self.entity_id = "light." + self._name.lower() + "_" + self._device_id

        # _LOGGER.info(
        #     "init new light: " + device_id + "/" + self._name + " => " + device["object_type"] + " / " + (self._device['device_class'] if self._device['device_class'] else "-") + "/" + device["object_name"])

    # default properties

    @property
    def should_poll(self):
        """ Poll for a Vimar device. """
        return True

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    # @property
    # def color(self):
    #     """ Returns the name of the device. """
    #     return "white"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if 'icon' in self._device and self._device['icon']:
            return self._device['icon']
        return self.ICON

    # @property
    # def entity_picture(self):
    #     """Return the entity picture to use in the frontend, if any."""
    #     return None

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device['device_class']

    @property
    def unique_id(self):
        """Return the ID of this device."""

        # _LOGGER.info("get unique id: " + self._device_id)

        return self._device_id

    # @property
    # def entity_id(self):
    #     """Return the ID of this device."""
    # return DOMAIN + "." + self._device_id + "_" + re.sub("[^0-9a-z\_]+",
    # "_", self._name.lower())

    @property
    def available(self):
        """Return True if entity is available."""
        return True

    # light properties

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

    # async getter and setter

    # def update(self):
    # see:
    # https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        # starttime = localtime()
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
        # _LOGGER.debug("Vimar Light update finished after " +
        # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

        # for status_name, status_dict in self._device['status'].items():
        #     _LOGGER.info("Vimar light update id: " +
        # status_name + " = " + status_dict['status_value'] + " / " +
        # status_dict['status_id'])

    async def async_turn_on(self, **kwargs):
        """ Turn the Vimar light on. """

        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = True
                self._device['status']['on/off']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
                # await
                # self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                # self._device['status']['on/off']['status_id'], 1)
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

    async def async_added_to_hass(self, **kwargs):
        return 0

    async def async_will_remove_from_hass(self, **kwargs):
        return 0

    # private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['on/off']['status_value'] != '0']
            if 'value' in self._device['status']:
                self._brightness = recalculate_brightness(
                    int(self._device['status']['value']['status_value']))


# end class VimarLight
