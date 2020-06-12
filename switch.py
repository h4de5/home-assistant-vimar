"""Platform for switch integration."""

from homeassistant.helpers.entity import ToggleEntity
from homeassistant.components import switch
from datetime import timedelta
from time import gmtime, strftime, localtime, mktime
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
import logging
import asyncio

# import variables set in __init__.py
# from . import vimarconnection
# from . import vimarlink
from .const import DOMAIN
from . import format_name

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=20)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
PARALLEL_UPDATES = True


@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Switch platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Switch started!")
    switches = []

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
        #     switches.append(VimarSwitch(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            switches.append(VimarSwitch(device, device_id, vimarconnection))

    # fallback
    # if len(switches) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             switches.append(VimarSwitch({'object_name': name}, device_id, link))

    if len(switches) != 0:
        async_add_entities(switches)
    _LOGGER.info("Vimar Switch complete!")


class VimarSwitch(ToggleEntity):
    """ Provides a Vimar switches. """

    ICON = "mdi:power-plug"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the switch."""
        self._device = device
        self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        self._state = False
        self._reset_status()
        self._vimarconnection = vimarconnection

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

    # switch properties

    @property
    def is_on(self):
        """ True if the device is on. """
        return self._state

    # async getter and setter

    # def update(self):
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this switch.
        This is the only method that should fetch new data for Home Assistant.
        """
        starttime = localtime()
        # self._device = self._vimarconnection.getDevice(self._device_id)
        # self._device['status'] = self._vimarconnection.getDeviceStatus(self._device_id)
        old_status = self._device['status']
        self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
        self._reset_status()
        if old_status != self._device['status']:
            self.async_schedule_update_ha_state()
        # _LOGGER.debug("Vimar Switch update finished after " +
        #               str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    async def async_turn_on(self, **kwargs):
        """ Turn the Vimar switch on. """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = True
                self._device['status']['on/off']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
                self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the Vimar switch off. """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = False
                self._device['status']['on/off']['status_value'] = '0'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 0)
                self.async_schedule_update_ha_state()

    # private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['on/off']['status_value'] != '0']

    def format_name(self, name):
        name = name.replace('VENTILATOR', '')
        name = name.replace('STECKDOSE', '')
        # change case
        return name.title()

# end class VimarSwitch
