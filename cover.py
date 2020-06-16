"""Platform for cover integration."""
# credits to https://community.home-assistant.io/t/create-new-cover-component-not-working/50361/5

from homeassistant.components.cover import (
    SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_STOP)
try:
    from homeassistant.components.cover import CoverEntity
except ImportError:
    from homeassistant.components.cover import CoverDevice as CoverEntity
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION)
from datetime import timedelta
from time import gmtime, strftime, localtime, mktime
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
import logging

from .const import DOMAIN
from . import format_name

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
PARALLEL_UPDATES = True

# see: https://developers.home-assistant.io/docs/en/entity_cover.html


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Cover platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Cover started!")
    covers = []

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
        #     covers.append(VimarCover(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            covers.append(VimarCover(device, device_id, vimarconnection))

    # fallback
    # if len(lights) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             covers.append(VimarCover({'object_name': name}, device_id, link))

    if len(covers) != 0:
        async_add_entities(covers)
    _LOGGER.info("Vimar Cover complete!")

# CoverDevice is deprecated, modify VimarCover to extend CoverEntity
# class VimarCover(CoverDevice):


class VimarCover(CoverEntity):
    """ Provides a Vimar cover. """

    # see: https://developers.home-assistant.io/docs/entity_index/#generic-properties
    """ Return True if the state is based on our assumption instead of reading it from the device."""
    """ this will ignore is_closed state ? """
    assumed_state = False

    """ set entity_id, object_id manually due to possible duplicates """
    entity_id = "cover." + "unset"

    # pylint: disable=no-self-use
    def __init__(self, device, device_id, vimarconnection):
        """Initialize the cover."""
        self._device = device
        self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        # _state = False .. 0, stop has not been pressed
        # _state = True .. 1, stop has been pressed
        self._state = False
        # _direction = 0 .. upwards
        # _direction = 1 .. downards
        self._direction = 0
        self._reset_status()
        self._vimarconnection = vimarconnection

        self.entity_id = "cover." + self._name.lower() + "_" + self._device_id

    # default properties

    @property
    def should_poll(self):
        """ polling is needed for a Vimar device. """
        return True

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if 'icon' in self._device and self._device['icon']:
            return self._device['icon']
        # return self.ICON
        return ("mdi:window-open", "mdi:window-closed")[self.is_closed]

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
    # cover properties

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if _state (stopped) is 1, than stopped was pressed, therefor it cannot be completely closed
        # if its 0, and direction 1, than it was going downwards and it was never stopped, therefor it is closed now
        if self._state:
            self.assumed_state = True
            return False
        elif self._direction == 1:
            self.assumed_state = False
            return True
        else:
            self.assumed_state = False
            return False

    @property
    def is_closing(self):
        if not self._state and self._direction == 1:
            return True

    @property
    def is_opening(self):
        if not self._state and self._direction == 0:
            return True

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    # async getter and setter

    # def update(self):
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this cover.
        This is the only method that should fetch new data for Home Assistant.
        """
        # starttime = localtime()
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
        # _LOGGER.debug("Vimar Cover update finished after " +
        #               str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if 'status' in self._device and self._device['status']:
            if 'up/down' in self._device['status']:
                self._direction = 1
                self._device['status']['up/down']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['up/down']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['up/down']['status_id'], 1)
                self.async_schedule_update_ha_state()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if 'status' in self._device and self._device['status']:
            if 'up/down' in self._device['status']:
                self._direction = 0
                self._device['status']['up/down']['status_value'] = '0'
                # self._vimarconnection.set_device_status(self._device['status']['up/down']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['up/down']['status_id'], 0)
                self.async_schedule_update_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        if 'status' in self._device and self._device['status']:
            if 'stop up/stop down' in self._device['status']:
                self._state = 1
                self._device['status']['stop up/stop down']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['stop up/stop down']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['stop up/stop down']['status_id'], 1)
                self.async_schedule_update_ha_state()

    # private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'stop up/stop down' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['stop up/stop down']['status_value'] != '0']
            if 'up/down' in self._device['status']:
                self._direction = int(
                    self._device['status']['up/down']['status_value'])
                self.assumed_state = False

    def format_name(self, name):
        name = name.replace('ROLLLADEN', 'ROLLO')
        name = name.replace('F-FERNBEDIENUNG', 'FENSTER')
        # change case
        return name.title()

# end class VimarCover
