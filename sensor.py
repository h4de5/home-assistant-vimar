"""Platform for sensor integration."""

import logging
from datetime import timedelta

from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .vimar_entity import VimarEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=20)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)
PARALLEL_UPDATES = 3


# @asyncio.coroutine
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Sensor platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Sensor started!")
    sensors = []

    vimarconnection = hass.data[DOMAIN]['connection']

    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        for device_id, device in devices.items():
            sensors.append(VimarSensor(device, device_id, vimarconnection))

    if len(sensors) != 0:
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        async_add_entities(sensors, True)
    _LOGGER.info("Vimar Sensor complete!")


# see: https://developers.home-assistant.io/docs/core/entity/sensor/
class VimarSensor(VimarEntity, Entity):
    """Provides a Vimar Sensors. """

    # set entity_id, object_id manually due to possible duplicates
    entity_id = "switch." + "unset"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the switch."""

        VimarEntity.__init__(self, device, device_id, vimarconnection)

        self.entity_id = "switch." + self._name.lower() + "_" + self._device_id

    # switch properties

    @property
    def is_on(self):
        """ True if the device is on. """
        return self._state

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
        """ Turn the Vimar switch on. """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = True
                self._device['status']['on/off']['status_value'] = '1'
                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
                self.async_schedule_update_ha_state()

            if 'comando' in self._device['status']:
                self._state = True
                self._device['status']['comando']['status_value'] = '1'
                # for some reason we are sending 0 on activation
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['comando']['status_id'], 0)
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
            # no turn off for scenes

    # private helper methods

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'on/off' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['on/off']['status_value'] != '0']
            if 'comando' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['comando']['status_value'] != '0']

# end class VimarSwitch

    # async def async_toggle(self, **kwargs):
    #     """ Turn the Vimar switch on. """
    #     if 'status' in self._device and self._device['status']:
    #         if 'comando' in self._device['status']:
    #             self._state = True
    #             self._device['status']['comando']['status_value'] = '1'
    #             await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['comando']['status_id'], 0)
    #             self.async_schedule_update_ha_state()
