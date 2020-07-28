"""Platform for switch integration."""

import logging
# from datetime import timedelta
from homeassistant.helpers.entity import ToggleEntity
# from .const import DOMAIN
from .vimar_entity import (VimarEntity, vimar_setup_platform)

_LOGGER = logging.getLogger(__name__)

# SCAN_INTERVAL = timedelta(seconds=20)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)
# PARALLEL_UPDATES = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Switch platform."""
    vimar_setup_platform(VimarSwitch, hass, async_add_entities, discovery_info)


class VimarSwitch(VimarEntity, ToggleEntity):
    """Provide Vimar switches and scenes."""

    # _platform = "switch"

    # set entity_id, object_id manually due to possible duplicates
    # entity_id = "switch." + "unset"

    def __init__(self, device_id, vimarconnection, vimarproject, coordinator):
        """Initialize the switch."""
        VimarEntity.__init__(self, device_id, vimarconnection, vimarproject, coordinator)

        # self.entity_id = "switch." + self._name.lower() + "_" + self._device_id

    # switch properties

    @property
    def is_on(self):
        """Return True if the device is on."""
        if self.has_state('on/off'):
            return self.get_state('on/off') == '1'
        elif self.has_state('comando'):
            return self.get_state('comando') == '1'
        return None

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return (self.is_on, True)[self.is_on is None]

    # async getter and setter

    # def update(self):
    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    # async def async_update(self):
    #     """Fetch new state data for this switch.
    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     # starttime = localtime()
    #     # self._device = self._vimarconnection.getDevice(self._device_id)
    #     # self._device['status'] = self._vimarconnection.getDeviceStatus(self._device_id)
    #     old_status = self._device['status']
    #     self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
    #     self._reset_status()
    #     if old_status != self._device['status']:
    #         self.async_schedule_update_ha_state()
    #     # _LOGGER.debug("Vimar Switch update finished after " +
    #     # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    async def async_turn_on(self, **kwargs):
        """Turn the Vimar switch on."""
        if self.has_state('on/off'):
            self.change_state('on/off', '1')

        elif self.has_state('comando'):
            self.change_state('comando', '1')

    async def async_turn_off(self, **kwargs):
        """Turn the Vimar switch off."""
        if self.has_state('on/off'):
            self.change_state('on/off', '0')

        # no turn off for scenes

    # private helper methods

    # def _reset_status(self):
    #     """Set status from _device to class variables."""
    #     if 'status' in self._device and self._device['status']:
    #         if 'on/off' in self._device['status']:
    #             self._state = (False, True)[
    #                 self._device['status']['on/off']['status_value'] != '0']
    #         if 'comando' in self._device['status']:
    #             self._state = (False, True)[
    #                 self._device['status']['comando']['status_value'] != '0']
