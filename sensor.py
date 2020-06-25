"""Platform for sensor integration."""

import logging
from datetime import timedelta
from homeassistant.const import (
    POWER_KILO_WATT)
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
            # sensors += VimarSensorContainer(device, device_id, vimarconnection).get_sensor_list()

    if len(sensors) != 0:
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        async_add_entities(sensors, True)
    _LOGGER.info("Vimar Sensor complete!")

# see: https://developers.home-assistant.io/docs/core/entity/sensor/


# class VimarSensor(VimarEntity, Entity):
#     """Provides a Vimar Sensors"""

#     # set entity_id, object_id manually due to possible duplicates
#     entity_id = "sensor." + "unset"

#     _measurement = None

#     def __init__(self, device, device_id, vimarconnection, measurement_name):
#         """Initialize the sensor."""

#         VimarEntity.__init__(self, device, device_id, vimarconnection)

#         self.entity_id = "sensor." + self._name.lower() + "_" + measurement_name + "_" + self._device_id

#         self._measurement = measurement_name

#     @property
#     def unit_of_measurement(self):
#         """Return the unit of measurement."""
#         return POWER_KILO_WATT

#     @property
#     def device_state_attributes(self):
#         """Return the state attributes."""
#         # state_attr = {ATTR_HOST: self._host}
#         # if self._ipcam.status_data is None:
#         #     return state_attr

#         state_attr[_measurement] =

#         return state_attr

#     def _reset_status(self):
#         pass


# class VimarSensorContainer(VimarEntity):
class VimarSensor(VimarEntity, Entity):
    """Defines a Vimar Sensor device"""

    # different types of sensors
    _measurements = {}
    # _sensor_list = []

    # set entity_id, object_id manually due to possible duplicates
    # entity_id = "sensor." + "unset"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the sensor."""

        VimarEntity.__init__(self, device, device_id, vimarconnection)

        self.entity_id = "sensor." + self._name.lower() + "_" + self._device_id

    # async getter and setter
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return POWER_KILO_WATT

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        # state_attr = {ATTR_HOST: self._host}
        # if self._ipcam.status_data is None:
        #     return state_attr

        return self._measurements

    # private helper methods

    # def get_sensor_value(self, measurement):
    #     """Returns the value of a single measurement"""
    #     return self._measurements[measurement]

    # def get_sensor_list(self):
    #     """returns a List of VimarSensors"""

    #     for measurement in self._measurements:
    #         self._sensor_list.append(VimarSensor(self._device, self._device_id, self._vimarconnection, measurement))

    #     return self._sensor_list;

# The row is Row000005: '321','consumo_totale','-1','0.310' (the device is set to consider also your potential production - zero in my case - with row n.6 and the net demand row n.8
# Row000004: '319','scambio_totale','-1','0.310'
# Row000005: '321','consumo_totale','-1','0.310'
# Row000006: '323','produzione_totale','-1','0'
# Row000007: '325','immissione_totale','-1','-0.000'
# Row000008: '327','prelievo_totale','-1','0.310'
# Row000009: '329', 'autoconsumo_totale', '-1', '0.000'

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'scambio_totale' in self._device['status']:
                self._measurements['scambio_totale'] = float(self._device['status']['scambio_totale']['status_value'])
            if 'consumo_totale' in self._device['status']:
                self._measurements['consumo_totale'] = float(self._device['status']['consumo_totale']['status_value'])
            if 'produzione_totale' in self._device['status']:
                self._measurements['produzione_totale'] = float(self._device['status']['produzione_totale']['status_value'])
            if 'immissione_totale' in self._device['status']:
                self._measurements['immissione_totale'] = float(self._device['status']['immissione_totale']['status_value'])
            if 'prelievo_totale' in self._device['status']:
                self._measurements['prelievo_totale'] = float(self._device['status']['prelievo_totale']['status_value'])
            if 'autoconsumo_totale' in self._device['status']:
                self._measurements['autoconsumo_totale'] = float(self._device['status']['autoconsumo_totale']['status_value'])
