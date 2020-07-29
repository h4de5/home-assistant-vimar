"""Platform for climate integration."""

import logging
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
    SUPPORT_AUX_HEAT,
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
    # DOMAIN,
    VIMAR_CLIMATE_COOL,
    VIMAR_CLIMATE_HEAT,
    VIMAR_CLIMATE_AUTO_I,
    VIMAR_CLIMATE_MANUAL_I,
    VIMAR_CLIMATE_OFF_I,
    VIMAR_CLIMATE_AUTO_II,
    VIMAR_CLIMATE_MANUAL_II,
    VIMAR_CLIMATE_OFF_II)
from .vimar_entity import (VimarEntity, vimar_setup_platform)
try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Climate platform."""
    vimar_setup_platform(VimarClimate, hass,
                         async_add_entities, discovery_info)


class VimarClimate(VimarEntity, ClimateEntity):
    """Provides a Vimar climates."""

    # _platform = "climate"

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

    def __init__(self, device_id, vimarconnection, vimarproject, coordinator):
        """Initialize the climate."""
        VimarEntity.__init__(self, device_id, vimarconnection, vimarproject, coordinator)

        # self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

    # climate properties

    @property
    def is_on(self):
        """Return True if the device is on."""
        if self.climate_type == 'heat_cool':
            return (True, False)[self.get_state('funzionamento') == VIMAR_CLIMATE_OFF_I]
        else:
            return (True, False)[self.get_state('funzionamento') == VIMAR_CLIMATE_OFF_II]

    @property
    def is_running(self):
        """Return True when climate is currently cooling or heating, idle of not."""
        if self.has_state('on/off'):
            return self.get_state('on/off') == '1'
        elif self.has_state('stato_principale_condizionamento on/off'):
            return self.get_state('stato_principale_condizionamento on/off') == '1'
        return None

    @property
    def supported_features(self):
        """Flag supported features. The device supports a target temperature."""
        flags = SUPPORT_TARGET_TEMPERATURE
        if self.has_state('velocita_fancoil'):
            flags |= SUPPORT_FAN_MODE
        if self.has_state('stato_principale_riscaldamento on/off'):
            flags |= SUPPORT_AUX_HEAT
        return flags

    @property
    def current_temperature(self):
        """Return current temperature."""
        if self.has_state('temperatura'):
            return float(self.get_state('temperatura'))
        if self.has_state('temperatura_misurata'):
            return float(self.get_state('temperatura_misurata'))

    @property
    def current_humidity(self):
        """Return current humidity."""
        if self.has_state('umidita'):
            return float(self.get_state('umidita'))

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return float(self.get_state('setpoint'))

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.1

    @property
    def temperature_unit(self):
        """Return unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT)."""
        # TODO - find a way to handle different units from vimar device
        if self.has_state('unita'):
            return (TEMP_FAHRENHEIT, TEMP_CELSIUS)[self.get_state('unita') == '0']
        else:
            return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        """Return current operation (e.g.heat, cool, idle). Used to determine state."""
        # HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF,
        if not self.is_on:
            return HVAC_MODE_OFF

        if self.climate_type == 'heat_cool':
            return (HVAC_MODE_HEAT, HVAC_MODE_COOL)[self.get_state('stagione') == VIMAR_CLIMATE_COOL]
        else:
            if self.has_state('stato_principale_condizionamento on/off') and self.get_state('stato_principale_condizionamento on/off') == '1':
                return VIMAR_CLIMATE_COOL
            elif self.has_state('stato_principale_riscaldamento on/off') and self.get_state('stato_principale_riscaldamento on/off') == '1':
                return HVAC_MODE_HEAT
            else:
                return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """List of available operation modes. See below."""
        return [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF, HVAC_MODE_AUTO]

    @property
    def hvac_action(self):
        """Return current HVAC action (heating, cooling, idle, off)."""
        # CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_OFF, CURRENT_HVAC_IDLE
        if not self.is_on:
            return CURRENT_HVAC_OFF

        if not self.is_running:
            return CURRENT_HVAC_IDLE

        if self.climate_type == 'heat_cool':
            return (CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL)[self.get_state('stagione') == VIMAR_CLIMATE_COOL]
        else:
            if self.has_state('stato_principale_condizionamento on/off') and self.get_state('stato_principale_condizionamento on/off') == '1':
                return CURRENT_HVAC_HEAT
            elif self.has_state('stato_principale_riscaldamento on/off') and self.get_state('stato_principale_riscaldamento on/off') == '1':
                return CURRENT_HVAC_COOL
            else:
                return CURRENT_HVAC_IDLE

    @property
    def is_aux_heat(self):
        """Return True if an auxiliary heater is on. Requires SUPPORT_AUX_HEAT."""
        if self.has_state('stato_principale_riscaldamento on/off'):
            return self.get_state('stato_principale_riscaldamento on/off') != '0'

    @property
    def fan_modes(self):
        """Return the list of available fan modes. Requires SUPPORT_FAN_MODE."""
        return (
            FAN_ON,
            FAN_OFF,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH)

    @property
    def fan_mode(self):
        """Return the current fan mode. Requires SUPPORT_FAN_MODE."""
        if self.has_state('modalita_fancoil'):
            if self.get_state('modalita_fancoil') == '0':
                return FAN_OFF

        if self.has_state('velocita_fancoil'):
            fancoil_speed = float(self.get_state('velocita_fancoil'))

            if fancoil_speed == 0:
                return FAN_ON
            elif fancoil_speed <= 33:
                return FAN_LOW
            elif fancoil_speed <= 66:
                return FAN_MEDIUM
            elif fancoil_speed > 66:
                return FAN_HIGH

    # async getter and setter

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        _LOGGER.info("Vimar Climate setting fan_mode: %s", fan_mode)

        if self.has_state('velocita_fancoil') and self.has_state('modalita_fancoil'):
            if fan_mode == FAN_ON or fan_mode == FAN_OFF:
                self.change_state('modalita_fancoil', ('0', '1')[fan_mode == FAN_ON])
            else:
                fancoil_speed = '0'
                if fan_mode == FAN_LOW:
                    fancoil_speed = '33'
                elif fan_mode == FAN_MEDIUM:
                    fancoil_speed = '66'
                elif fan_mode == FAN_HIGH:
                    fancoil_speed = '100'
                self.change_state('modalita_fancoil', '1', 'velocita_fancoil', fancoil_speed)

    async def async_turn_aux_heat_on(self):
        """Turn auxiliary heater on."""
        _LOGGER.info("Vimar Climate setting aux_heat: %s", "on")
        self.change_state('stato_principale_riscaldamento on/off', '1')

    async def async_turn_aux_heat_off(self):
        """Turn auxiliary heater off."""
        _LOGGER.info("Vimar Climate setting aux_heat: %s", "off")
        self.change_state('stato_principale_riscaldamento on/off', '0')

        # if 'status' in self._device and self._device['status']:
        #     if 'stato_principale_riscaldamento on/off' in self._device['status']:
        #         self._is_aux_heat = False
        #         self._device['status']['stato_principale_riscaldamento on/off']['status_value'] = self._is_aux_heat
        #         await self.hass.async_add_executor_job(self._vimarconnection.set_device_status,
        #                                                self._device['status']['stato_principale_riscaldamento on/off']['status_id'], self._is_aux_heat)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        # if 'stagione' in self._device['status']:
        #     self._hvac_mode = (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
        #         self._device['status']['stagione']['status_value'] == '1']

        # self._hvac_mode = hvac_mode

        if hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT]:

            set_function_mode = (VIMAR_CLIMATE_AUTO_II, VIMAR_CLIMATE_AUTO_I)[self.climate_type == 'heat_cool']
            set_hvac_mode = (VIMAR_CLIMATE_HEAT, VIMAR_CLIMATE_COOL)[hvac_mode == HVAC_MODE_COOL]

            # DONE - get current set_temparatur and set it again

            _LOGGER.info(
                "Vimar Climate setting setup mode to: %s", set_function_mode)
            _LOGGER.info(
                "Vimar Climate setting hvac_mode: %s", set_hvac_mode)

            if self.climate_type == 'heat_cool':
                self.change_state('funzionamento', set_function_mode, 'setpoint', self.current_temperature, 'stagione', set_hvac_mode)
            else:
                if hvac_mode == HVAC_MODE_COOL and self.has_state('stato_principale_condizionamento on/off'):
                    self.change_state('funzionamento', set_function_mode, 'setpoint', self.current_temperature, 'stato_principale_condizionamento on/off', '1')
                elif hvac_mode == VIMAR_CLIMATE_HEAT and self.has_state('stato_principale_riscaldamento on/off'):
                    self.change_state('funzionamento', set_function_mode, 'setpoint', self.current_temperature, 'stato_principale_riscaldamento on/off', '1')

        elif hvac_mode in [HVAC_MODE_AUTO]:
            set_function_mode = (VIMAR_CLIMATE_AUTO_II, VIMAR_CLIMATE_AUTO_I)[self.climate_type == 'heat_cool']

            _LOGGER.info(
                "Vimar Climate setting setup mode to auto: %s", set_function_mode)

            self.change_state('funzionamento', set_function_mode)

        elif hvac_mode in [HVAC_MODE_OFF]:
            set_function_mode = (VIMAR_CLIMATE_OFF_II, VIMAR_CLIMATE_OFF_I)[self.climate_type == 'heat_cool']

            _LOGGER.info(
                "Vimar Climate setting setup mode to off: %s", set_function_mode)

            self.change_state('funzionamento', set_function_mode)

        # if 'status' in self._device and self._device['status']:
        #     if hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT]:

        #         if 'stagione' in self._device['status']:

        #             self._hvac_mode = hvac_mode
        #             if self._climate_type == 'heat_cool':
        #                 self._function_mode = VIMAR_CLIMATE_AUTO_I
        #             else:
        #                 self._function_mode = VIMAR_CLIMATE_AUTO_II

        #             self._device['status']['stagione']['status_value'] = (
        #                 VIMAR_CLIMATE_HEAT, VIMAR_CLIMATE_COOL)[self._hvac_mode == HVAC_MODE_COOL]
        #             self._device['status']['funzionamento']['status_value'] = self._function_mode

        #             _LOGGER.info(
        #                 "Vimar Climate setting hvac_mode: %s", self._hvac_mode)
        #             _LOGGER.info(
        #                 "Vimar Climate setting setup mode to: %s", self._function_mode)

        #             await asyncio.gather(
        #                 self.hass.async_add_executor_job(
        #                     self._vimarconnection.set_device_status,
        #                     self._device['status']['stagione']['status_id'],
        #                     self._device['status']['stagione']['status_value'], 'SYNCDB'),
        #                 self.hass.async_add_executor_job(
        #                     self._vimarconnection.set_device_status,
        #                     self._device['status']['funzionamento']['status_id'],
        #                     self._device['status']['funzionamento']['status_value'], 'NO-OPTIONALS')
        #             )

            # # we always set current function mode
            # elif 'funzionamento' in self._device['status']:

            #     if hvac_mode in (HVAC_MODE_AUTO, HVAC_MODE_OFF):
            #         if self._climate_type == 'heat_cool':
            #             self._function_mode = (VIMAR_CLIMATE_AUTO_I, VIMAR_CLIMATE_OFF_I)[
            #                 hvac_mode == HVAC_MODE_OFF]
            #         else:
            #             self._function_mode = (VIMAR_CLIMATE_AUTO_II, VIMAR_CLIMATE_OFF_II)[
            #                 hvac_mode == HVAC_MODE_OFF]

            #     self._device['status']['funzionamento']['status_value'] = self._function_mode

            #     _LOGGER.info(
            #         "Vimar Climate setting setup mode to: %s", self._function_mode)

            #     await self.hass.async_add_executor_job(
            #         self._vimarconnection.set_device_status,
            #         self._device['status']['funzionamento']['status_id'],
            #         self._device['status']['funzionamento']['status_value'], 'NO-OPTIONALS')

            # self.request_statemachine_update()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        set_temperature = kwargs.get(ATTR_TEMPERATURE)
        if set_temperature is None:
            return

        set_function_mode = (VIMAR_CLIMATE_MANUAL_II, VIMAR_CLIMATE_MANUAL_I)[self.climate_type == 'heat_cool']

        _LOGGER.info("Vimar Climate setting temperature: %s", str(set_temperature))
        _LOGGER.info(
            "Vimar Climate setting setup mode to: %s", set_function_mode)

        self.change_state('funzionamento', set_function_mode, 'setpoint', set_temperature)

    # helper

    @property
    def climate_type(self):
        """Return type of climate control - either has heating and cooling or fancoil."""
        if self.has_state('velocita_fancoil'):
            return "heat_cool_fancoil"
        else:
            return "heat_cool"

# end class VimarClimate
