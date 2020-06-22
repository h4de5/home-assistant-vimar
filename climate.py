"""Platform for climate integration."""
# credits to
# https://github.com/GeoffAtHome/climatewaverf-home-assistant-climates/blob/master/climatewave.py

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity
# import homeassistant.helpers.config_validation as cv
import logging
from datetime import timedelta

from homeassistant.components.climate.const import (CURRENT_HVAC_COOL,
                                                    CURRENT_HVAC_HEAT,
                                                    CURRENT_HVAC_IDLE,
                                                    CURRENT_HVAC_OFF,
                                                    HVAC_MODE_AUTO,
                                                    HVAC_MODE_COOL,
                                                    HVAC_MODE_HEAT,
                                                    HVAC_MODE_OFF,
                                                    SUPPORT_TARGET_TEMPERATURE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
# from time import gmtime, strftime, localtime, mktime
from homeassistant.util import Throttle

from . import format_name
from .const import (DOMAIN, VIMAR_CLIMATE_AUTO, VIMAR_CLIMATE_COOL,
                    VIMAR_CLIMATE_HEAT, VIMAR_CLIMATE_MANUAL,
                    VIMAR_CLIMATE_OFF)
from .vimar_entity import VimarEntity


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
PARALLEL_UPDATES = 5


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


class VimarClimate(VimarEntity, ClimateEntity):
    """ Provides a Vimar climates. """

    ICON = "mdi:ceiling-climate"

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    """ Return True if the state is based on our assumption instead of reading it from the device."""
    # assumed_state = False

    """ set entity_id, object_id manually due to possible duplicates """
    entity_id = "climate." + "unset"

    # 20.3
    _temperature = None
    # 23
    # self._target_temperature_high = None
    # 20
    # self._target_temperature_low = None
    _target_temperature = None
    # heat, cool, idle
    _hvac_mode = None
    # heating, cooling
    _hvac_action = CURRENT_HVAC_IDLE

    # for how many hours the temporary target temperature will be held SYNCDB
    _temporizzazione = 0

    # TODO - find a way to handle different units from vimar device
    _temperature_unit = TEMP_CELSIUS

    # 8 .. auto, 7 .. manual timed, 6 .. manual  NO-OPTIONALS
    # self._funzionamento = VIMAR_CLIMATE_AUTO

    # vimar property - if it should be seen as idle
    _is_running = None

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the climate."""

        VimarEntity.__init__(self, device, device_id, vimarconnection)

        self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

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
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.1

    @property
    def hvac_mode(self):
        """ The current operation (e.g.heat, cool, idle). Used to determine state. """
        # HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF,
        if not self._state:
            return HVAC_MODE_OFF

        return self._hvac_mode

    @property
    def hvac_action(self):
        """ The current HVAC action(heating, cooling) """
        # CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_OFF, CURRENT_HVAC_IDLE
        if not self._state:
            return CURRENT_HVAC_OFF
        return self._hvac_action
        # return (CURRENT_HVAC_IDLE, self._hvac_action)[self._is_running]

    @property
    def hvac_modes(self):
        """ List of available operation modes. See below. """
        return [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF, HVAC_MODE_AUTO]

    @property
    def temperature_unit(self):
        """ The unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT). """
        # if self._temperature_unit == None:
        #     raise NotImplementedError()
        return self._temperature_unit

    # async getter and setter

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        _LOGGER.info("Vimar Climate setting hvac_mode: %s", hvac_mode)

        # if 'stagione' in self._device['status']:
        #     self._hvac_mode = (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
        #         self._device['status']['stagione']['status_value'] == '1']

        # self._hvac_mode = hvac_mode

        if 'status' in self._device and self._device['status']:
            if hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT]:

                if 'stagione' in self._device['status']:
                    self._hvac_mode = hvac_mode
                    self._device['status']['stagione']['status_value'] = (
                        VIMAR_CLIMATE_HEAT, VIMAR_CLIMATE_COOL)[self._hvac_mode == HVAC_MODE_COOL]
                    await self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                                                           self._device['status']['stagione']['status_id'],
                                                           self._device['status']['stagione']['status_value'], 'SYNCDB')

            # we always set current function mode
            if 'funzionamento' in self._device['status']:
                self._hvac_mode = hvac_mode

                if hvac_mode in (HVAC_MODE_AUTO, HVAC_MODE_OFF):
                    self._funzionamento = (VIMAR_CLIMATE_AUTO, VIMAR_CLIMATE_OFF)[hvac_mode == HVAC_MODE_OFF]

                _LOGGER.info("Vimar Climate setting setup mode to: %s", self._funzionamento)

                self._device['status']['funzionamento']['status_value'] = self._funzionamento
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                                                       self._device['status']['funzionamento']['status_id'],
                                                       self._device['status']['funzionamento']['status_value'], 'NO-OPTIONALS')

            self.async_schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        _LOGGER.info("Vimar Climate setting temperature: %s", str(temperature))

        self._target_temperature = temperature

        if 'status' in self._device and self._device['status']:
            # set target temperatur only if mode and setpoint status are available
            if 'setpoint' in self._device['status'] and 'funzionamento' in self._device['status']:

                self._device['status']['setpoint']['status_value'] = str(
                    self._target_temperature)
                self._device['status']['funzionamento']['status_value'] = VIMAR_CLIMATE_MANUAL

                self._funzionamento = VIMAR_CLIMATE_MANUAL

                # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 0)
                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                                                       self._device['status']['setpoint']['status_id'],
                                                       self._device['status']['setpoint']['status_value'], 'SYNCDB')

                await self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
                                                       self._device['status']['funzionamento']['status_id'],
                                                       self._device['status']['funzionamento']['status_value'], 'NO-OPTIONALS')

                self.async_schedule_update_ha_state()

    # def update(self):
    # see: https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    # see:
    # https://github.com/home-assistant/home-assistant/blob/master/homeassistant/components/dweet/__init__.py
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Fetch new state data for this climate.
        This is the only method that should fetch new data for Home Assistant.
        """
        # starttime = localtime()
        old_status = self._device['status']
        self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)
        self._reset_status()
        if old_status != self._device['status']:
            self.async_schedule_update_ha_state()

        # for status_name, status_dict in self._device['status'].items():
        #     _LOGGER.info("Vimar Climate update id: " +
        # status_name + " = " + status_dict['status_value'] + " / " +
        # status_dict['status_id'])

        # keys_values = self._device['status'].items()
        # new_d = {str(key): str(value) for key, value in keys_values}

        # _LOGGER.info("Vimar Climate update " + new_d)

        # _LOGGER.info("Vimar Climate update finished after " +
        # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    # async def async_turn_on(self, **kwargs):
    #     """ Turn the Vimar climate on. """

    #     if 'status' in self._device and self._device['status']:
    #         if 'on/off' in self._device['status']:
    #             self._state = True
    #             # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 1)
    #             # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['on/off']['status_id'], 1)
    #             self.hass.async_add_executor_job(
    # self._vimarconnection.set_device_status,
    # self._device['status']['on/off']['status_id'], 1)

    #     self.async_schedule_update_ha_state()

    # async def async_turn_off(self, **kwargs):
    #     """ Turn the Vimar climate off. """
    #     if 'status' in self._device and self._device['status']:
    #         if 'on/off' in self._device['status']:
    #             self._state = False
    #             # self._vimarconnection.set_device_status(self._device['status']['on/off']['status_id'], 0)
    #             self.hass.async_add_executor_job(
    # self._vimarconnection.set_device_status,
    # self._device['status']['on/off']['status_id'], 0)

    #     self.async_schedule_update_ha_state()
    # private helper methods

# SELECT ID,NAME,STATUS_ID,CURRENT_VALUE FROM DPADD_OBJECT WHERE ID IN
# (9195,9196,9197);

# ELECT ID,NAME,STATUS_ID,CURRENT_VALUE FROM DPADD_OBJECT WHERE ID IN
# (229,309,438,442,445,447,449,457,461,463,465,468,470,472,476,479,481,483,486,488,490,493,508,510,512,515,517,519,522,524,526,545,547,549,552,554,556,559,561,563,582,584,586,590,592,594,608,610,612,616,618,620,623,625,627,947,948,949,950,951,952,953,954,957,958,959,972,973,974,975,976,977,978,979,982,983,984,997,998,999,1000,1001,1002,1003,1004,1007,1008,1009,1022,1023,1024,1025,1026,1027,1028,1029,1032,1033,1034,1815,1816,1825,1826,1835,1836,1845,1846,3304,3313,3322,3331,9154,9195,9196,9197,9211,9212,9213);

# Row000113: '9154','_DPAD_PRODUCT_VIMARBYME_CERTIFICATE_TRIGGER','-1','0'
# Row000114: '9195','T1','-1','22.5'
# Row000115: '9196','T2','-1','23.5'
# Row000116: '9197','T3','-1','25.0'
# Row000117: '9211','T1','-1',''
# Row000118: '9212','T2','-1',''
# Row000119: '9213','T3','-1',''

# Row000078: '984','unita','-1','0'
# Row000079: '997','funzionamento','-1','8'
# Row000080: '998','centralizzato','-1','1'
# Row000081: '999','stagione','-1','1'
# Row000082: '1000','terziario','-1','0'
# Row000083: '1001','on/off','-1','0'
# Row000084: '1002','setpoint','-1','26.0'
# Row000085: '1003','temporizzazione','-1','0'
# Row000086: '1004','temperatura','-1','23.2'

# active cooling
# Row000067: '959','unita','-1','0'
# Row000068: '972','funzionamento','-1','8'
# Row000069: '973','centralizzato','-1','1'
# Row000070: '974','stagione','-1','1'
# Row000071: '975','terziario','-1','0'
# Row000072: '976','on/off','-1','1'
# Row000073: '977','setpoint','-1','22.5'
# Row000074: '978','temporizzazione','-1','0'
# Row000075: '979','temperatura','-1','23.9'

# idle cooling
# Row000078: '984','unita','-1','0'
# Row000079: '997','funzionamento','-1','8'
# Row000080: '998','centralizzato','-1','1'
# Row000081: '999','stagione','-1','1'
# Row000082: '1000','terziario','-1','0'
# Row000083: '1001','on/off','-1','0'
# Row000084: '1002','setpoint','-1','26.0'
# Row000085: '1003','temporizzazione','-1','0'
# Row000086: '1004','temperatura','-1','23.1'


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
            # temperature units
            if 'unita' in self._device['status']:
                self._temperature_unit = (TEMP_FAHRENHEIT, TEMP_CELSIUS)[
                    self._device['status']['unita']['status_value'] == '0']

            # current temperature
            if 'temperatura' in self._device['status']:
                self._temperature = float(
                    self._device['status']['temperatura']['status_value'])

            # target tempertature
            if 'setpoint' in self._device['status']:
                self._target_temperature = float(
                    self._device['status']['setpoint']['status_value'])

            # current direction cooling or heating
            if 'stagione' in self._device['status']:
                self._hvac_mode = (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
                    self._device['status']['stagione']['status_value'] == VIMAR_CLIMATE_COOL]
                self._hvac_action = (CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL)[
                    self._device['status']['stagione']['status_value'] == VIMAR_CLIMATE_COOL]

            # mode of the climate, 0 off, 8 auto, 6 manual
            if 'funzionamento' in self._device['status']:
                self._funzionamento = self._device['status']['funzionamento']['status_value']

                self._state = (True, False)[
                    self._device['status']['funzionamento']['status_value'] == VIMAR_CLIMATE_OFF]

            # whenever the climate is idle or active (heating, cooling)
            if 'on/off' in self._device['status']:
                self._is_running = (False, True)[
                    self._device['status']['on/off']['status_value'] != '0']

            # if 'value' in self._device['status']:
            #     self._brightness = recalculate_brightness(
            #         int(self._device['status']['value']['status_value']))

    def format_name(self, name):
        # change case
        return name.title()

# end class VimarClimate
