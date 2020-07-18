"""Platform for sensor integration."""

import copy
import logging
# from datetime import timedelta
from homeassistant.const import (
    POWER_KILO_WATT)
from homeassistant.helpers.entity import Entity
# from .const import DOMAIN
from .vimar_entity import (VimarEntity, vimar_setup_platform)
# from . import format_name

_LOGGER = logging.getLogger(__name__)

# SCAN_INTERVAL = timedelta(seconds=20)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)
# PARALLEL_UPDATES = 2

# see: https://developers.home-assistant.io/docs/core/entity/sensor/


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar sensor platform."""
    vimar_setup_platform(VimarSensorContainer, hass, async_add_entities, discovery_info)


class VimarSensor(VimarEntity, Entity):
    """Provide a Vimar Sensors."""

    # set entity_id, object_id manually due to possible duplicates
    # entity_id = "sensor." + "unset"

    _platform = "sensor"
    _measurement = None
    # _parent = None
    _state_value = None

    def __init__(self, device, device_id, vimarconnection, measurement_name, coordinator):
        """Initialize the sensor."""
        # copy device - otherwise we will have duplicate keys
        device_c = copy.copy(device)

        device_c['object_name'] += " " + measurement_name

        VimarEntity.__init__(self, device_c, device_id, vimarconnection, coordinator)

        # self.entity_id = "sensor." + self._name.lower() + "-" + measurement_name + "-" + self._device_id

        # self._name = format_name(self._device['object_name'] + " " + measurement_name)

        _LOGGER.debug("Creating new sensor for %s", self.entity_id)

        self._measurement = measurement_name
        # self._parent = parent

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        # return self._parent.unit_of_measurement
        return POWER_KILO_WATT

    @property
    def unique_id(self):
        """Return the ID of this device and its state."""
        return self._device_id + '-' + self._device['status'][self._measurement]['status_id']

    @property
    def state(self):
        """Return the value of the sensor."""
        # return self._parent.get_sensor_value(self._measurement)
        return self._state_value

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device
    #     # state_attr = {ATTR_HOST: self._host}
    #     # if self._ipcam.status_data is None:
    #     #     return state_attr

    #     state_attr[_measurement] =

    #     return state_attr

    def _reset_status(self):
        """Read data from device and convert it into hass states."""
        if 'status' in self._device and self._device['status']:
            if self._measurement in self._device['status']:
                self._state_value = float(self._device['status'][self._measurement]['status_value'])


class VimarSensorContainer():
    # class VimarSensor(VimarEntity, Entity):
    """Defines a Vimar Sensor device."""

    # different types of sensors
    # _measurements = {}
    # _sensor_list = []

    _device = []
    _device_id = 0
    _vimarconnection = None

    # set entity_id, object_id manually due to possible duplicates
    # entity_id = "sensor." + "unset"

    def __init__(self, device, device_id, vimarconnection, coordinator):
        """Initialize the sensor."""
        self._device = device
        self._device_id = device_id
        self._vimarconnection = vimarconnection
        self._coordinator = coordinator

        # self._reset_status()

        # VimarEntity.__init__(self, device, device_id, vimarconnection)

        # self.entity_id = "sensor." + self._name.lower() + "_" + self._device_id

    # async getter and setter
    # @property
    # def unit_of_measurement(self):
    #     """Return the unit of measurement."""
    #     return POWER_KILO_WATT

    # @property
    # def device_state_attributes(self):
    #     """Return the state attributes."""
    #     # state_attr = {ATTR_HOST: self._host}
    #     # if self._ipcam.status_data is None:
    #     #     return state_attr

    #     return self._measurements

    # @property
    # def state(self):
    #     """The value of the sensor."""
    #     first_value = 0
    #     # get the first available value in the measurements dict
    #     if self._measurements and len(self._measurements) > 0:
    #         values_view = self._measurements.values()
    #         value_iterator = iter(values_view)
    #         first_value = next(value_iterator)

    #     return first_value

        # if 'scambio_totale' in self._device['status']:
        #     return self._measurements['scambio_totale'] = float(self._device['status']['scambio_totale']['status_value'])
        # if 'consumo_totale' in self._device['status']:
        #     self._measurements['consumo_totale'] = float(self._device['status']['consumo_totale']['status_value'])
        # if 'produzione_totale' in self._device['status']:
        #     self._measurements['produzione_totale'] = float(self._device['status']['produzione_totale']['status_value'])
        # if 'immissione_totale' in self._device['status']:
        #     self._measurements['immissione_totale'] = float(self._device['status']['immissione_totale']['status_value'])
        # if 'prelievo_totale' in self._device['status']:
        #     self._measurements['prelievo_totale'] = float(self._device['status']['prelievo_totale']['status_value'])
        # if 'autoconsumo_totale' in self._device['status']:
        #     self._measurements['autoconsumo_totale'] = float(self._device['status']['autoconsumo_totale']['status_value'])

        # return None

    # private helper methods

    # def get_sensor_value(self, measurement):
    #     """Returns the value of a single measurement"""
    #     return self._measurements[measurement]

    def get_entity_list(self):
        """Return a List of VimarSensors."""
        sensor_list = []

        if 'status' in self._device and self._device['status']:
            for status in self._device['status']:
                # _LOGGER.info("Adding sensor for %s", status)

                # newsensor = VimarSensor(self._device, self._device_id, self._vimarconnection, status)
                # _LOGGER.info("sensor id %s", newsensor.entity_id)
                # sensor_list.append(newsensor)
                sensor_list.append(VimarSensor(self._device, self._device_id, self._vimarconnection, status, self._coordinator))

        # _LOGGER.info("Adding: %d new sensors", len(sensor_list))

        # for sensor in sensor_list:
        #     _LOGGER.info("sensor_list: %s", sensor.entity_id)

        return sensor_list

# The row is Row000005: '321','consumo_totale','-1','0.310'
#  (the device is set to consider also your potential production - zero in my case - with row n.6 and the net demand row n.8
# Row000004: '319','scambio_totale','-1','0.310'
# Row000005: '321','consumo_totale','-1','0.310'
# Row000006: '323','produzione_totale','-1','0'
# Row000007: '325','immissione_totale','-1','-0.000'
# Row000008: '327','prelievo_totale','-1','0.310'
# Row000009: '329', 'autoconsumo_totale', '-1', '0.000'

    # def _reset_status(self):
    #     """ set status from _device to class variables  """
    #     if 'status' in self._device and self._device['status']:
    #         for status in self._device['status']:
    #             self._measurements[status] = self._device['status'][status]['status_value']

    #     if 'status' in self._device and self._device['status']:
    #         if 'consumo_totale' in self._device['status']:
    #             self._measurements['consumo_totale'] = float(self._device['status']['consumo_totale']['status_value'])
    #         if 'scambio_totale' in self._device['status']:
    #             self._measurements['scambio_totale'] = float(self._device['status']['scambio_totale']['status_value'])
    #         if 'produzione_totale' in self._device['status']:
    #             self._measurements['produzione_totale'] = float(self._device['status']['produzione_totale']['status_value'])
    #         if 'immissione_totale' in self._device['status']:
    #             self._measurements['immissione_totale'] = float(self._device['status']['immissione_totale']['status_value'])
    #         if 'prelievo_totale' in self._device['status']:
    #             self._measurements['prelievo_totale'] = float(self._device['status']['prelievo_totale']['status_value'])
    #         if 'autoconsumo_totale' in self._device['status']:
    #             self._measurements['autoconsumo_totale'] = float(self._device['status']['autoconsumo_totale']['status_value'])
