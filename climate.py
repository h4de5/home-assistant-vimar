"""Platform for climate integration."""
# credits to
# https://github.com/GeoffAtHome/climatewaverf-home-assistant-climates/blob/master/climatewave.py

import logging
import asyncio

from datetime import timedelta
from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    FAN_ON,
    FAN_OFF,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT)
from .const import (
    DOMAIN,
    VIMAR_CLIMATE_COOL,
    VIMAR_CLIMATE_HEAT,
    VIMAR_CLIMATE_AUTO_I,
    VIMAR_CLIMATE_MANUAL_I,
    VIMAR_CLIMATE_OFF_I,
    VIMAR_CLIMATE_AUTO_II,
    VIMAR_CLIMATE_MANUAL_II,
    VIMAR_CLIMATE_OFF_II)
from .vimar_entity import VimarEntity

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)
PARALLEL_UPDATES = 3


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Climate platform."""

    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.info("Vimar Climate started!")
    climates = []

    vimarconnection = hass.data[DOMAIN]['connection']

    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        for device_id, device in devices.items():
            climates.append(VimarClimate(device, device_id, vimarconnection))

    if len(climates) != 0:
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        async_add_entities(climates, True)
    _LOGGER.info("Vimar Climate complete!")


class VimarClimate(VimarEntity, ClimateEntity):
    """ Provides a Vimar climates. """

    # set entity_id, object_id manually due to possible duplicates
    entity_id = "sensor." + "unset"

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

    # fancoil mode
    _fancoil_mode = None
    _fancoil_speed = None

    # vimar climate type
    _climate_type = None

    # for how many hours the temporary target temperature will be held SYNCDB
    # not in use
    # _temporizzazione = 0

    # functional mode, can be VIMAR_CLIMATE_AUTO, or VIMAR_CLIMATE_MANUAL
    _function_mode = None

    # TODO - find a way to handle different units from vimar device
    _temperature_unit = TEMP_CELSIUS

    # thermostat I
    # 8 .. auto, 7 .. manual timed, 6 .. manual  NO-OPTIONALS
    # thermostat II
    # 0 (automatic)
    # 1 (manual)
    # 2 (so called 'reduction')
    # 3 (away)
    # 5 (manual for a certain time)
    # 6 (off)
    # 0 Automatico -> Automatic (follow the 3-setpoints T1-T2-T3 program along the week see rows 97-99)
    # 1 Manuale-> Manual mode with setpoint
    # maybe later for presents
    # 2 Riduzione -> I guess a kind of energy saving mode, never used
    # 3 Assenza -> Away mode (If you use an extreme setpoint - eg. 31° for cooling - is equivalent of being off)

    # self._function_mode = VIMAR_CLIMATE_AUTO

    # vimar property - if it should be seen as idle
    _is_running = None

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the climate."""
        VimarEntity.__init__(self, device, device_id, vimarconnection)
        self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

        # depending on available states, set the climate types
        self._climate_type = "heat_cool"
        if 'status' in self._device and self._device['status']:
            if 'velocita_fancoil' in self._device['status']:
                self._climate_type = "heat_cool_fancoil"

    # climate properties

    @property
    def is_on(self):
        """ True if the device is on. """
        return self._state

    @property
    def supported_features(self):
        """Flag supported features. The device supports a target temperature."""
        flags = SUPPORT_TARGET_TEMPERATURE
        if 'status' in self._device and self._device['status']:
            if 'velocita_fancoil' in self._device['status']:
                flags |= SUPPORT_FAN_MODE
        return flags

    @property
    def current_temperature(self):
        """The current temperature."""
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
    def fan_modes(self):
        """Returns the list of available fan modes. Requires SUPPORT_FAN_MODE."""
        return (
            FAN_ON,
            FAN_OFF,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH)

    @property
    def fan_mode(self):
        """Returns the current fan mode. Requires SUPPORT_FAN_MODE."""

        if self._fancoil_mode == 1 and self._fancoil_speed == 0:
            return FAN_ON
        elif self._fancoil_mode == 1 and self._fancoil_speed <= 33:
            return FAN_LOW
        elif self._fancoil_mode == 1 and self._fancoil_speed <= 66:
            return FAN_MEDIUM
        elif self._fancoil_mode == 1 and self._fancoil_speed > 66:
            return FAN_HIGH
        else:
            return FAN_OFF

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

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""

        _LOGGER.info("Vimar Climate setting fan_mode: %s", fan_mode)

        if 'status' in self._device and self._device['status']:

            if 'velocita_fancoil' in self._device['status']:

                if fan_mode == FAN_ON:
                    self._fancoil_mode = 1
                elif fan_mode == FAN_OFF:
                    self._fancoil_mode = 0
                elif fan_mode == FAN_LOW:
                    self._fancoil_mode = 1
                    self._fancoil_speed = 33
                elif fan_mode == FAN_MEDIUM:
                    self._fancoil_mode = 1
                    self._fancoil_speed = 66
                elif fan_mode == FAN_HIGH:
                    self._fancoil_mode = 1
                    self._fancoil_speed = 100

                self._device['status']['modulate_fancoil']['status_value'] = self._fancoil_mode
                self._device['status']['modalita_fancoil']['status_value'] = self._fancoil_speed

                # self._vimarconnection.set_device_status(self._device['status']['value']['status_id'], brightness_value)
                # await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['value']['status_id'], brightness_value)
                await asyncio.gather(
                    self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['modulate_fancoil']['status_id'], self._fancoil_mode),
                    self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status']['modalita_fancoil']['status_id'], self._fancoil_speed)
                )

            self.async_schedule_update_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        # if 'stagione' in self._device['status']:
        #     self._hvac_mode = (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
        #         self._device['status']['stagione']['status_value'] == '1']

        # self._hvac_mode = hvac_mode

        if 'status' in self._device and self._device['status']:
            if hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT]:
                if 'stagione' in self._device['status']:

                    self._hvac_mode = hvac_mode
                    if self._climate_type == 'heat_cool':
                        self._function_mode = VIMAR_CLIMATE_AUTO_I
                    else:
                        self._function_mode = VIMAR_CLIMATE_AUTO_II

                    self._device['status']['stagione']['status_value'] = (
                        VIMAR_CLIMATE_HEAT, VIMAR_CLIMATE_COOL)[self._hvac_mode == HVAC_MODE_COOL]
                    self._device['status']['funzionamento']['status_value'] = self._function_mode

                    _LOGGER.info("Vimar Climate setting hvac_mode: %s", self._hvac_mode)
                    _LOGGER.info("Vimar Climate setting setup mode to: %s", self._function_mode)

                    await asyncio.gather(
                        self.hass.async_add_executor_job(
                            self._vimarconnection.set_device_status,
                            self._device['status']['stagione']['status_id'],
                            self._device['status']['stagione']['status_value'], 'SYNCDB'),
                        self.hass.async_add_executor_job(
                            self._vimarconnection.set_device_status,
                            self._device['status']['funzionamento']['status_id'],
                            self._device['status']['funzionamento']['status_value'], 'NO-OPTIONALS')
                    )

            # we always set current function mode
            elif 'funzionamento' in self._device['status']:

                if hvac_mode in (HVAC_MODE_AUTO, HVAC_MODE_OFF):
                    if self._climate_type == 'heat_cool':
                        self._function_mode = (VIMAR_CLIMATE_AUTO_I, VIMAR_CLIMATE_OFF_I)[hvac_mode == HVAC_MODE_OFF]
                    else:
                        self._function_mode = (VIMAR_CLIMATE_AUTO_II, VIMAR_CLIMATE_OFF_II)[hvac_mode == HVAC_MODE_OFF]

                self._device['status']['funzionamento']['status_value'] = self._function_mode

                _LOGGER.info("Vimar Climate setting setup mode to: %s", self._function_mode)

                await self.hass.async_add_executor_job(
                    self._vimarconnection.set_device_status,
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

                if self._climate_type == 'heat_cool':
                    self._function_mode = VIMAR_CLIMATE_MANUAL_I
                else:
                    self._function_mode = VIMAR_CLIMATE_MANUAL_II

                self._device['status']['funzionamento']['status_value'] = self._function_mode
                self._device['status']['setpoint']['status_value'] = str(
                    self._target_temperature)

                _LOGGER.info("Vimar Climate setting setup mode to: %s", self._function_mode)

                await asyncio.gather(
                    self.hass.async_add_executor_job(
                        self._vimarconnection.set_device_status,
                        self._device['status']['setpoint']['status_id'],
                        self._device['status']['setpoint']['status_value'], 'SYNCDB'),

                    self.hass.async_add_executor_job(
                        self._vimarconnection.set_device_status,
                        self._device['status']['funzionamento']['status_id'],
                        self._device['status']['funzionamento']['status_value'], 'NO-OPTIONALS')
                )

                self.async_schedule_update_ha_state()


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


# Row000061: '2830','forzatura off','-1','0'
# Row000062: '2832','allarme_massetto','-1','0'
# Row000063: '2834','regolazione','-1','1'
# Row000064: '2838','modalita_fancoil','-1','0'
# Row000065: '2840','velocita_fancoil','-1','0'
# Row000066: '2842','funzionamento','-1','3'
# Row000067: '2850','setpoint','-1','31.00'
# Row000068: '2858','temporizzazione','-1','1'
# Row000069: '2869','temperatura_misurata','-1','27.20'
# Row000070: '2872','stato_boost on/off','-1','0'
# Row000071: '2873','stato_principale_condizionamento on/off','-1','0'
# Row000072: '2874','stato_principale_riscaldamento on/off','-1','0'


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
            if 'temperatura_misurata' in self._device['status']:
                self._temperature = float(
                    self._device['status']['temperatura_misurata']['status_value'])

            # cooling ventilatore
            # modalita_fancoil
            # velocita_fancoil

            # target tempertature
            if 'setpoint' in self._device['status']:
                self._target_temperature = float(
                    self._device['status']['setpoint']['status_value'])

            # fancoil
            if 'modalita_fancoil' in self._device['status']:
                self._fancoil_mode = int(
                    self._device['status']['modalita_fancoil']['status_value'])

            if 'velocita_fancoil' in self._device['status']:
                self._fancoil_speed = float(
                    self._device['status']['velocita_fancoil']['status_value'])

            # current direction cooling or heating
            if 'stagione' in self._device['status']:
                self._hvac_mode = (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
                    self._device['status']['stagione']['status_value'] == VIMAR_CLIMATE_COOL]
                self._hvac_action = (CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL)[
                    self._device['status']['stagione']['status_value'] == VIMAR_CLIMATE_COOL]

            # mode of the climate, 0 off, 8 auto, 6 manual
            if 'funzionamento' in self._device['status']:
                self._function_mode = self._device['status']['funzionamento']['status_value']

                if self._climate_type == 'heat_cool':
                    self._state = (True, False)[
                        self._device['status']['funzionamento']['status_value'] == VIMAR_CLIMATE_OFF_I]
                else:
                    self._state = (True, False)[
                        self._device['status']['funzionamento']['status_value'] == VIMAR_CLIMATE_OFF_II]

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
