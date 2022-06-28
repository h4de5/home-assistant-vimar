"""Platform for sensor integration."""

# import copy
import logging

# from datetime import timedelta
from homeassistant.const import (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_TIMESTAMP,
    ENERGY_KILO_WATT_HOUR,
    POWER_KILO_WATT,
    SPEED_METERS_PER_SECOND,
    TEMP_CELSIUS,
)

try:
    from homeassistant.const import ELECTRIC_POTENTIAL_VOLT
except ImportError:
    from homeassistant.const import VOLT as ELECTRIC_POTENTIAL_VOLT

try:
    from homeassistant.components.sensor import (STATE_CLASS_TOTAL_INCREASING, STATE_CLASS_MEASUREMENT)
except ImportError:
    from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT
    from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT as STATE_CLASS_TOTAL_INCREASING
try:
    from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT
except ImportError:
    STATE_CLASS_MEASUREMENT = "measurement"

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .vimar_entity import VimarEntity, vimar_setup_entry

# from . import format_name


from .const import DEVICE_TYPE_SENSORS as CURR_PLATFORM

# SCAN_INTERVAL = timedelta(seconds=20)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)
# PARALLEL_UPDATES = 2
# see: https://developers.home-assistant.io/docs/core/entity/sensor/

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Sensor platform."""
    vimar_setup_entry(VimarSensorContainer, CURR_PLATFORM, hass, entry, async_add_devices)
    # https://github.com/custom-components/remote_homeassistant/blob/aac178b737357492cf3beb60ec3494dcf0513c3a/custom_components/remote_homeassistant/sensor.py#L4


class VimarSensor(VimarEntity, SensorEntity):
    """Provide a Vimar Sensors."""

    # set entity_id, object_id manually due to possible duplicates
    # entity_id = "sensor." + "unset"

    _measurement_name = None
    _measurement_display_name = None
    _class_and_units = None
    # _parent = None
    # _state_value = None

    def __init__(self, coordinator, device_id: int, measurement_name):
        """Initialize the sensor."""
        # copy device - otherwise we will have duplicate keys
        # device_c = copy.copy(device)
        # device_c['object_name'] += " " + measurement_name

        self._measurement_name = measurement_name
        self._measurement_display_name = self._measurement_name.title().strip().replace("_", " ")
        VimarEntity.__init__(self, coordinator, device_id)
        self._class_and_units = self.class_and_units()
        # this will override the name for all
        # self._device['object_name_' + self._measurement_name] = self._device['object_name'] + " " + measurement_name
        # self.entity_id = self._platform + "." + self.name.lower() + "-" + measurement_name + "_" + self._device_id
        # self.entity_id = "sensor." + self._name.lower() + "-" + measurement_name + "-" + self._device_id
        # self._name = format_name(self._device['object_name'] + " " + measurement_name)
        # _LOGGER.debug("Creating new sensor for %s", self.entity_id)
        # self._parent = parent

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    @property
    def name(self):
        """Return the name of the device."""
        return super().name + " " + self._measurement_display_name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        class_and_unit = self.class_and_units()
        # _LOGGER.warning("DEBUG units for %s %s %s", self._device["object_type"], self._measurement_name, class_and_unit[0]);
        return class_and_unit[0]

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        class_and_unit = self.class_and_units()
        return class_and_unit[1]

    @property
    def state_class(self) -> str:
        """Return the state class of this entity."""
        class_and_unit = self.class_and_units()
        if class_and_unit[1] == DEVICE_CLASS_ENERGY:
            return STATE_CLASS_TOTAL_INCREASING
        elif class_and_unit[1] == DEVICE_CLASS_POWER and any(x in self._measurement_name for x in ["totale"]):
            return STATE_CLASS_MEASUREMENT

    def class_and_units(self):
        if not self._class_and_units is None:
            return self._class_and_units
        """Return the class of this device, from component DEVICE_CLASSES."""
        if self._device["object_type"] in [
            "CH_Misuratore",
            "CH_Carichi_Custom",
            "CH_Carichi",
            "CH_Carichi_3F",
            "CH_KNX_GENERIC_POWER_KW",
        ]:
            if any(x in self._measurement_name for x in ["energia", "potenza_attiva"]):
                return [ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_ENERGY]
            elif any(x in self._measurement_name for x in ["fase"]):
                return [ELECTRIC_POTENTIAL_VOLT, DEVICE_CLASS_CURRENT]
            # elif any(x in self._measurement_name for x in ["fase"]):
            #     return [ELECTRIC_POTENTIAL_VOLT, DEVICE_CLASS_VOLTAGE]
            elif any(x in self._measurement_name for x in ["_date", "_time", "_datetime"]):
                return ["", DEVICE_CLASS_TIMESTAMP]
            else:
                return [POWER_KILO_WATT, DEVICE_CLASS_POWER]
        elif self._device["object_type"] in ["CH_KNX_GENERIC_TEMPERATURE_C"] or any(
            x in self._measurement_name for x in ["temperature"]
        ):
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20
            return [TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE]
        elif self._device["object_type"] in ["CH_KNX_GENERIC_WINDSPEED"] or any(
            x in self._measurement_name for x in ["wind_speed"]
        ):
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20
            return [SPEED_METERS_PER_SECOND, self._device["device_class"]]
        elif any(x in self._measurement_name for x in ["brightness"]):
            # see: https://github.com/h4de5/home-assistant-vimar/issues/20
            return ["lm", DEVICE_CLASS_ILLUMINANCE]
        else:
            return [None, self._device["device_class"]]

        # ‘its_night’: {‘status_id’: ‘3369’, ‘status_value’: ‘1’, ‘status_range’: ‘’},
        # ‘its_raining’: {‘status_id’: ‘3371’, ‘status_value’: ‘0’, ‘status_range’: ‘’},
        # ‘temperature’: {‘status_id’: ‘3373’, ‘status_value’: ‘11.00’, ‘status_range’: ‘’},
        # ‘temperature_min’: {‘status_id’: ‘3375’, ‘status_value’: ‘5.30’, ‘status_range’: ‘’},
        # ‘temperature_max’: {‘status_id’: ‘3377’, ‘status_value’: ‘8.10’, ‘status_range’: ‘’},
        # ‘temperature_request_minmax’: {‘status_id’: ‘3379’, ‘status_value’: ‘0’, ‘status_range’: ‘’},
        # ‘temperature_reset’: {‘status_id’: ‘3381’, ‘status_value’: ‘1’, ‘status_range’: ‘’},
        # ‘temperature_alarm’: {‘status_id’: ‘3383’, ‘status_value’: ‘0’, ‘status_range’: ‘’},
        # ‘wind_speed’: {‘status_id’: ‘3409’, ‘status_value’: ‘3.24’, ‘status_range’: ‘’},
        # ‘wind_speed_max’: {‘status_id’: ‘3411’, ‘status_value’: ‘0.00’, ‘status_range’: ‘’},
        # ‘wind_speed_request_minmax’: {‘status_id’: ‘3413’, ‘status_value’: ‘0’, ‘status_range’: ‘’},
        # ‘wind_speed_reset’: {‘status_id’: ‘3415’, ‘status_value’: ‘1’, ‘status_range’: ‘’},
        # ‘wind_speed_alarm’: {‘status_id’: ‘3417’, ‘status_value’: ‘0’, ‘status_range’: ‘’},
        # ‘brightness’: {‘status_id’: ‘3437’, ‘status_value’: ‘0.00’, ‘status_range’: ‘’},

        # 'potenza_attiva','-1','0.01'

        # 'contatore_assoluto': {'status_id': '102467', 'status_value': '104','status_range': 'min=0|max=4294967295'},
        # 'contatore_parziale':{'status_id': '102469', 'status_value': '15', 'status_range': 'min=0|max=4294967295'},
        # 'reset_to_value': {'status_id': '102472', 'status_value': '0', 'status_range': 'min=0|max=4294967295'},
        # 'reset_history': {'status_id': '102474', 'status_value': '0', 'status_range': 'min=0|max=1'},
        # 'frequenza_impulsi': {'status_id': '102476', 'status_value':'0', 'status_range':'min=-2147483648|max=2147483648'},
        # 'divisore': {'status_id': '103644', 'status_value': '1', 'status_range': ''},
        # 'moltiplicatore': {'status_id': '103646', 'status_value': '100', 'status_range': ''}}

        # contatore assoluto = absolute counter. total pulses received
        # contatore parziale = partial counter. pulses since the last reset
        # reset_to_value = initial value to count from
        # reset_history = reset history
        # frequenza_impulsi = pulse frequency
        # divisore = divisor: value by which to divide the partial counter
        # moltiplicatore = multiplier: value by which to multiply the partial counter

    @property
    def unique_id(self):
        """Return the ID of this device and its state."""
        # _LOGGER.debug("Unique Id: " + DOMAIN + '_' + self._platform + '_' + self._device_id + '-' +
        # self._device['status'][self._measurement_name]['status_id'] + " - " + self.name)
        return super().unique_id + "-" + self._device["status"][self._measurement_name]["status_id"]
        # return str(VimarEntity.unique_id) + '-' + self._device['status'][self._measurement_name]['status_id']

    @property
    def state(self):
        """Return the value of the sensor."""
        return self.get_state(self._measurement_name)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        base_attr = super().extra_state_attributes
        attr = self._device["status"][self._measurement_name]
        for key in attr:
            base_attr[key] = attr[key]
        return base_attr

    # def _reset_status(self):
    #     """Read data from device and convert it into hass states."""
    #     if 'status' in self._device and self._device['status']:
    #         if self._measurement_name in self._device['status']:
    #             self._state_value = float(self._device['status'][self._measurement_name]['status_value'])

    @property
    def native_unit_of_measurement(self):
        """Return the native unit_of_measurement of this sensor."""
        class_and_unit = self.class_and_units()
        # _LOGGER.warning("DEBUG units for %s %s %s", self._device["object_type"], self._measurement_name, class_and_unit[0]);
        return class_and_unit[0]

    @property
    def native_value(self):
        """Return the native value of this sensor."""
        return self.get_state(self._measurement_name)


class VimarSensorContainer(VimarEntity):
    """Defines a Vimar Sensor device."""

    def __init__(self, coordinator, device_id: int):
        """Initialize the sensor."""
        VimarEntity.__init__(self, coordinator, device_id)

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    def get_entity_list(self):
        """Return a List of VimarSensors."""
        # if len(self._sensor_list) == 0:
        sensor_list = []
        if "status" in self._device and self._device["status"]:
            for status in self._device["status"]:
                # if status.find('_setpoint') != -1 or status.find('_output') != -1:
                if any(x in status for x in ["_setpoint", "_output"]):
                    continue
                # _LOGGER.debug("Adding sensor for %s", status)
                # _LOGGER.debug("Adding sensor %s from id %s", status, self._device_id)
                sensor_list.append(VimarSensor(self._coordinator, self._device_id, status))

        return sensor_list


# The row is Row000005: '321','consumo_totale','-1','0.310'
#  (the device is set to consider also your potential production - zero in my case - with row n.6 and the net demand row n.8
# Row000004: '319','scambio_totale','-1','0.310'
# Row000005: '321','consumo_totale','-1','0.310'
# Row000006: '323','produzione_totale','-1','0'
# Row000007: '325','immissione_totale','-1','-0.000'
# Row000008: '327','prelievo_totale','-1','0.310'
# Row000009: '329', 'autoconsumo_totale', '-1', '0.000'
#
# CH_KNX_GENERIC_POWER_KW
# Unknown object has states: {'value': {'status_id': '58240', 'status_value': '0.00', 'status_range': 'min=-670760|max=670760'}}
