"""Platform for climate integration."""
# credits to https://github.com/GeoffAtHome/climatewaverf-home-assistant-climates/blob/master/climatewave.py

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_TARGET_TEMPERATURE_RANGE,
    HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_OFF)
from homeassistant.const import (
    ATTR_TEMPERATURE, STATE_OFF, TEMP_CELSIUS, TEMP_FAHRENHEIT)
from datetime import timedelta
from time import gmtime, strftime, localtime, mktime
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
import logging
import asyncio

from .const import DOMAIN
from . import format_name

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
PARALLEL_UPDATES = True


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Climate platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Climate started!")
    climates = []

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
        #     climates.append(VimarClimate(name, device_id, vimarconnection))
        for device_id, device in devices.items():
            climates.append(VimarClimate(device, device_id, vimarconnection))

    # fallback
    # if len(climates) == 0:
    #     # Config is empty so generate a default set of switches
    #     for room in range(1, 2):
    #         for device in range(1, 2):
    #             name = "Room " + str(room) + " Device " + str(device)
    #             device_id = "R" + str(room) + "D" + str(device)
    #             climates.append(VimarClimate({'object_name': name}, device_id, link))

    if len(climates) != 0:
        async_add_entities(climates)
    _LOGGER.info("Vimar Climate complete!")


class VimarClimate(ClimateEntity):
    """ Provides a Vimar climates. """

    ICON = "mdi:ceiling-climate"

    # see: https://developers.home-assistant.io/docs/entity_index/#generic-properties
    """ Return True if the state is based on our assumption instead of reading it from the device."""
    # assumed_state = False

    """ set entity_id, object_id manually due to possible duplicates """
    entity_id = "climate." + "unset"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the climate."""
        self._device = device
        self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        self._state = False
        self._reset_status()
        self._vimarconnection = vimarconnection

        # 20.3
        self._temperature = None
        # 23
        # self._target_temperature_high = None
        # 20
        # self._target_temperature_low = None
        self._target_temperature = None
        # heat, cool, idle
        self._hvac_mode = None
        # heating, cooling
        self._hvac_action = None
        # TODO - find a way to handle different units from vimar device
        self._temperature_unit = TEMP_CELSIUS

        self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

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

    # climate properties

    @property
    def is_on(self):
        """ True if the device is on. """
        return self._state

    @property
    def supported_features(self):
        """ Flag supported features. The device supports a target temperature. """
        return SUPPORT_TARGET_TEMPERATURE
        # """ The device supports a ranged target temperature. Used for HVAC modes heat_cool and auto """
        # return SUPPORT_TARGET_TEMPERATURE | SUPPORT_TARGET_TEMPERATURE_RANGE

    @property
    def current_temperature(self):
        """ The current temperature."""
        return self._temperature

    @property
    def target_temperature_high(self):
        """ The upper bound target temperature """
        # return self._target_temperature_high
        if self._hvac_mode == HVAC_MODE_COOL:
            return self._target_temperature
        else:
            return None

    @property
    def target_temperature_low(self):
        """ The lower bound target temperature """
        # return self._target_temperature_low
        if self._hvac_mode == HVAC_MODE_HEAT:
            return self._target_temperature
        else:
            return None

    @property
    def hvac_mode(self):
        """ The current operation (e.g.heat, cool, idle). Used to determine state. """
        # HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF,
        return self._hvac_mode

    @property
    def hvac_action(self):
        """ The current HVAC action(heating, cooling) """
        # CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_OFF
        return self._hvac_action

    @property
    def hvac_modes(self):
        """ List of available operation modes. See below. """
        return [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF]

    @property
    def temperature_unit(self):
        """ The unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT). """
        # if self._temperature_unit == None:
        #     raise NotImplementedError()
        return self._temperature_unit
    # @property
    # def hvac_mode(self):
    #     """  """
    #     return self._hvac_mode

    # async getter and setter

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""

    # def update(self):
    # see: https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    # see: https://github.com/home-assistant/home-assistant/blob/master/homeassistant/components/dweet/__init__.py
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this climate.
        This is the only method that should fetch new data for Home Assistant.
        """
        # starttime = localtime()
        # self._climate.update()
        # self._state = self._climate.is_on()
        # self._brightness = self._climate.brightness
        # self._device = self._vimarconnection.getDevice(self._device_id)
        # self._device['status'] = self._vimarconnection.getDeviceStatus(self._device_id)
        old_status = self._device['status']
        self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
        self._reset_status()
        if old_status != self._device['status']:
            self.async_schedule_update_ha_state()

        # for status_name, status_dict in self._device['status'].items():
        #     _LOGGER.info("Vimar Climate update id: " +
        #                  status_name + " = " + status_dict['status_value'] + " / " + status_dict['status_id'])

        # keys_values = self._device['status'].items()
        # new_d = {str(key): str(value) for key, value in keys_values}

        # _LOGGER.info("Vimar Climate update " + new_d)

        # _LOGGER.info("Vimar Climate update finished after " +
        #              str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    # async def async_turn_on(self, **kwargs):
    #     """ Turn the Vimar climate on. """

    #     if 'status' in self._device and self._device['status']:
    #         if 'on/off' in self._device['status']:
    #             self._state = True
    #             # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
    #             # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
    #             self.hass.async_add_executor_job(
    #                 self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)

    #     if ATTR_BRIGHTNESS in kwargs:
    #         if 'status' in self._device and self._device['status']:
    #             if 'value' in self._device['status']:
    #                 self._brightness = kwargs[ATTR_BRIGHTNESS]
    #                 brightness_value = calculate_brightness(self._brightness)
    #                 # self._vimarconnection.set_device_status(self._device['status']['value']['status_id'], brightness_value)
    #                 self.hass.async_add_executor_job(
    #                     self._vimarconnection.set_device_status, self._device['status']['value']['status_id'], brightness_value)

    #     self.async_schedule_update_ha_state()

    # async def async_turn_off(self, **kwargs):
    #     """ Turn the Vimar climate off. """
    #     if 'status' in self._device and self._device['status']:
    #         if 'on/off' in self._device['status']:
    #             self._state = False
    #             # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 0)
    #             self.hass.async_add_executor_job(
    #                 self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 0)

    #     self.async_schedule_update_ha_state()
    # private helper methods

# Row000078: '984','unita','-1','0'
# Row000079: '997','funzionamento','-1','8'
# Row000080: '998','centralizzato','-1','1'
# Row000081: '999','stagione','-1','1'
# Row000082: '1000','terziario','-1','0'
# Row000083: '1001','on/off','-1','0'
# Row000084: '1002','setpoint','-1','26.0'
# Row000085: '1003','temporizzazione','-1','0'
# Row000086: '1004','temperatura','-1','23.2'
#############
# status_name = status_value / status_id
############
# funzionamento = 8 / 1022
# centralizzato = 1 / 1023
# stagione = 1 / 1024
# terziario = 0 / 1025
# on/off = 0 / 1026
# setpoint = 26.0 / 1027
# temporizzazione = 0 / 1028
# temperatura = 19.6 / 1029
# unita = 0 / 1034
# differenziale = 2 / 1845
# variazione = 2 / 1846
# forzatura off = 0 / 3331

    def _reset_status(self):
        """ set status from _device to class variables  """
        if 'status' in self._device and self._device['status']:
            if 'temperatura' in self._device['status']:
                self._temperature = float(
                    self._device['status']['temperatura']['status_value'])

            if 'setpoint' in self._device['status']:
                self._target_temperature = float(
                    self._device['status']['setpoint']['status_value'])

            if 'stagione' in self._device['status']:
                self._hvac_mode = (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
                    self._device['status']['stagione']['status_value'] == '1']

            if 'unita' in self._device['status']:
                self._temperature_unit = (TEMP_FAHRENHEIT, TEMP_CELSIUS)[
                    self._device['status']['unita']['status_value'] == '0']

            if 'on/off' in self._device['status']:
                self._state = (False, True)[
                    self._device['status']['on/off']['status_value'] != '0']

            # if 'value' in self._device['status']:
            #     self._brightness = recalculate_brightness(
            #         int(self._device['status']['value']['status_value']))

    def format_name(self, name):
        # change case
        return name.title()

# end class VimarClimate
