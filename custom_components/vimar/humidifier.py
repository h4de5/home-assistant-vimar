"""Platform for climate integration."""

import logging

from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_DRY,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    FAN_ON,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_DRY,
    SUPPORT_AUX_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_HUMIDITY,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT

from .const import (
    VIMAR_CLIMATE_AUTO,
    VIMAR_CLIMATE_AUTO_I,  # DOMAIN,
    VIMAR_CLIMATE_AUTO_II,
    VIMAR_CLIMATE_COOL,
    VIMAR_CLIMATE_COOL_I,
    VIMAR_CLIMATE_COOL_II,
    VIMAR_CLIMATE_HEAT,
    VIMAR_CLIMATE_HEAT_I,
    VIMAR_CLIMATE_HEAT_II,
    VIMAR_CLIMATE_MANUAL,
    VIMAR_CLIMATE_MANUAL_I,
    VIMAR_CLIMATE_MANUAL_II,
    VIMAR_CLIMATE_OFF,
    VIMAR_CLIMATE_OFF_I,
    VIMAR_CLIMATE_OFF_II,
)
from .vimar_entity import VimarEntity, vimar_setup_entry
from homeassistant.components.humidifier import HumidifierEntity
from .const import DEVICE_TYPE_HUMIDIFIER as CURR_PLATFORM

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Climate platform."""
    vimar_setup_entry(VimarHumidifier, CURR_PLATFORM, hass, entry, async_add_devices)


# see example: https://github.com/home-assistant/core/blob/dev/homeassistant/components/generic_hygrostat/humidifier.py

class VimarHumidifier(VimarEntity, HumidifierEntity):
    """Provides a Vimar climates."""

    def __init__(self, coordinator, device_id: int):
        """Initialize the climate."""
        VimarEntity.__init__(self, coordinator, device_id)

        # self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

    # climate properties
    @property
    def entity_platform(self):
        """Return current platform."""
        return CURR_PLATFORM

    @property
    def is_on(self):
        """Return True if the device is on or completely off."""
        if self.has_state("funzionamento"):
            return (True, False)[self.get_state("funzionamento") == self.get_const_value(VIMAR_CLIMATE_OFF)]
        elif self.has_state("enable"):
            return (True, False)[self.get_state("enable") == 0]

    @property
    def supported_features(self):
        """Flag supported features. The device supports a target temperature."""
        flags = 0
        if self.has_state("temperatura") or self.has_state("temperatura_misurata"):
            flags |= SUPPORT_TARGET_TEMPERATURE
        if self.has_state("velocita_fancoil"):
            flags |= SUPPORT_FAN_MODE
        if self.has_state("stato_boost on/off"):
            flags |= SUPPORT_AUX_HEAT
        if self.has_state("dynamic_mode"):
            flags |= SUPPORT_TARGET_HUMIDITY
        return flags

    @property
    def current_temperature(self):
        """Return current temperature."""
        if self.has_state("temperatura"):
            return float(self.get_state("temperatura"))
        if self.has_state("temperatura_misurata"):
            return float(self.get_state("temperatura_misurata"))

    @property
    def current_humidity(self):
        """Return current humidity."""
        if self.has_state("umidita"):
            return float(self.get_state("umidita"))
        if self.has_state("value"):
            return float(self.get_state("value"))

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""
        # CH_Clima_ControlloOnOffMisuraUmidita
        if self.has_state("setpoint"):
            return float(self.get_state("setpoint"))

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return float(self.get_state("setpoint"))

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.1

    @property
    def temperature_unit(self):
        """Return unit of temperature measurement for the system (TEMP_CELSIUS or TEMP_FAHRENHEIT)."""
        # TODO - find a way to handle different units from vimar device
        if self.has_state("unita"):
            return (TEMP_FAHRENHEIT, TEMP_CELSIUS)[self.get_state("unita") == "0"]
        else:
            return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        """Return target operation (e.g.heat, cool, auto, off). Used to determine state."""
        # can be HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF
        # will never be HVAC_MODE_AUTO, because funzionamento can be auto in both (HEAT and COOL) hvac modes.
        # if its not on, its off
        if not self.is_on:
            return HVAC_MODE_OFF

        if self.climate_type == "heat_cool":
            if self.get_const_value(VIMAR_CLIMATE_AUTO) == self.get_state("funzionamento"):
                return HVAC_MODE_AUTO
            else:
                return (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
                    self.get_state("stagione") == self.get_const_value(VIMAR_CLIMATE_COOL)
                ]
        elif self.climate_type == "heat_cool":
            if self.get_const_value(VIMAR_CLIMATE_AUTO) == self.get_state("funzionamento"):
                return HVAC_MODE_AUTO
            else:
                return (HVAC_MODE_HEAT, HVAC_MODE_COOL)[
                    self.get_state("regolazione") == self.get_const_value(VIMAR_CLIMATE_COOL)
                ]
        elif self.climate_type == "dry":
            return HVAC_MODE_DRY

            # if self.has_state('stato_principale_condizionamento on/off') and self.get_state('stato_principale_condizionamento on/off') == '1':
            #     return HVAC_MODE_COOL
            # elif self.has_state('stato_principale_riscaldamento on/off') and self.get_state('stato_principale_riscaldamento on/off') == '1':
            #     return HVAC_MODE_HEAT
            # else:
            #     return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """List of available operation modes. See below."""
        # button for auto is still there, to clear manual mode, but will not change highlighted icon
        if self.has_state("dynamic_mode"):
            return [HVAC_MODE_DRY]
        else:
            return [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF, HVAC_MODE_AUTO]

    @property
    def hvac_action(self):
        """Return current HVAC action (heating, cooling, idle, off)."""
        if not self.is_on:
            return CURRENT_HVAC_OFF

        # on/off is only available in heat_cool
        if self.has_state("on/off") and self.get_state("on/off") == "0":
            return CURRENT_HVAC_IDLE

        # if not self.is_running:
        #     return CURRENT_HVAC_IDLE

        if self.climate_type == "heat_cool":
            return (CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL)[
                self.get_state("stagione") == self.get_const_value(VIMAR_CLIMATE_COOL)
            ]
        elif self.climate_type == "heat_cool_fancoil":
            if (
                self.has_state("stato_principale_condizionamento on/off")
                and self.get_state("stato_principale_condizionamento on/off") == "1"
            ):
                return CURRENT_HVAC_COOL
            elif (
                self.has_state("stato_principale_riscaldamento on/off")
                and self.get_state("stato_principale_riscaldamento on/off") == "1"
            ):
                return CURRENT_HVAC_HEAT
            else:
                return CURRENT_HVAC_IDLE
        elif self.climate_type == "dry":
            return CURRENT_HVAC_DRY

    @property
    def is_aux_heat(self):
        """Return True if an auxiliary heater is on. Requires SUPPORT_AUX_HEAT."""
        if self.has_state("stato_boost on/off"):
            return self.get_state("stato_boost on/off") != "0"

    @property
    def fan_modes(self):
        """Return the list of available fan modes. Requires SUPPORT_FAN_MODE."""
        return (FAN_ON, FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH)

    @property
    def fan_mode(self):
        """Return the current fan mode. Requires SUPPORT_FAN_MODE."""
        if self.has_state("modalita_fancoil"):
            if self.get_state("modalita_fancoil") == "0":
                return FAN_OFF

        if self.has_state("velocita_fancoil"):
            fancoil_speed = float(self.get_state("velocita_fancoil"))

            if fancoil_speed == 0:
                return FAN_ON
            elif fancoil_speed <= 33:
                return FAN_LOW
            elif fancoil_speed <= 66:
                return FAN_MEDIUM
            elif fancoil_speed > 66:
                return FAN_HIGH

    # async getter and setter

    # possible actions from HA:
    # off: funzionamento = off *
    # cooling: funzionamento = auto, stagione/regolazione = 1, setpoint: temp
    # heating: funzionamento = auto, stagione/regolazione = 0, setpoint: temp
    # auto: funzionamento = auto,
    # temperature: funzionamento = manual, setpoint: temp
    # set fan mode: modalita_fancoil: state, velocita_fancoil: speed
    # set heater: stato_principale_riscaldamento on/off: state

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        _LOGGER.info("Vimar Climate setting fan_mode: %s", fan_mode)

        if self.has_state("velocita_fancoil") and self.has_state("modalita_fancoil"):
            if fan_mode == FAN_ON or fan_mode == FAN_OFF:
                self.change_state("modalita_fancoil", ("0", "1")[fan_mode == FAN_ON])
            else:
                fancoil_speed = "0"
                if fan_mode == FAN_LOW:
                    fancoil_speed = "33"
                elif fan_mode == FAN_MEDIUM:
                    fancoil_speed = "66"
                elif fan_mode == FAN_HIGH:
                    fancoil_speed = "100"
                self.change_state("modalita_fancoil", "1", "velocita_fancoil", fancoil_speed)

    # aux heating is just an output status
    async def async_turn_aux_heat_on(self):
        """Turn auxiliary heater on."""
        _LOGGER.info("Vimar Climate setting aux_heat: %s", "on")
        self.change_state("stato_boost on/off", "1")

    async def async_turn_aux_heat_off(self):
        """Turn auxiliary heater off."""
        _LOGGER.info("Vimar Climate setting aux_heat: %s", "off")
        self.change_state("stato_boost on/off", "0")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        set_function_mode = None

        if hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT]:

            # if heating or cooling is pressed, got to automode
            # no longer sure why?
            set_function_mode = self.get_const_value(VIMAR_CLIMATE_AUTO)
            set_hvac_mode = (self.get_const_value(VIMAR_CLIMATE_HEAT), self.get_const_value(VIMAR_CLIMATE_COOL))[
                hvac_mode == HVAC_MODE_COOL
            ]

            _LOGGER.info("Vimar Climate setting setup mode to heat/cool: %s", set_function_mode)

            # DONE - get current set_temperatur and set it again

        elif hvac_mode in [HVAC_MODE_AUTO]:
            set_function_mode = self.get_const_value(VIMAR_CLIMATE_AUTO)

            set_hvac_mode = (self.get_const_value(VIMAR_CLIMATE_HEAT), self.get_const_value(VIMAR_CLIMATE_COOL))[
                self.hvac_mode == HVAC_MODE_COOL
            ]

            _LOGGER.info("Vimar Climate setting setup mode to auto: %s", set_function_mode)
            # we only clear manual mode - no further settings
            # self.change_state('funzionamento', set_function_mode)

        elif hvac_mode in [HVAC_MODE_OFF]:
            set_function_mode = self.get_const_value(VIMAR_CLIMATE_OFF)

            set_hvac_mode = (self.get_const_value(VIMAR_CLIMATE_HEAT), self.get_const_value(VIMAR_CLIMATE_COOL))[
                self.hvac_mode == HVAC_MODE_COOL
            ]

            _LOGGER.info("Vimar Climate setting setup mode to off: %s", set_function_mode)
            # self.change_state('funzionamento', set_function_mode)

        _LOGGER.info("Vimar Climate setting hvac_mode: %s", set_hvac_mode)
        _LOGGER.info("Vimar Climate resetting target temperature: %s", self.target_temperature)

        if self.climate_type == "heat_cool":
            self.change_state(
                "funzionamento", set_function_mode, "stagione", set_hvac_mode, "setpoint", self.target_temperature
            )
        elif self.climate_type == "heat_cool_fancoil":
            self.change_state(
                "funzionamento", set_function_mode, "regolazione", set_hvac_mode, "setpoint", self.target_temperature
            )

        # if self.climate_type == 'heat_cool':
        #     self.change_state('setpoint', str(self.target_temperature),
        #   'unita', self.get_state('unita'), 'stagione', set_hvac_mode, 'centralizzato', '1', 'funzionamento', set_function_mode)
        # elif self.climate_type == 'heat_cool_fancoil':
        #     # stato_principale_condizionamento and stato_principale_riscaldamento are results not states - i think
        #     self.change_state('setpoint', str(self.target_temperature), 'unita', self.get_state('unita'), 'regolazione', set_hvac_mode, 'funzionamento', set_function_mode)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        set_temperature = kwargs.get(ATTR_TEMPERATURE)
        if set_temperature is None:
            return
        # upper limit for target temp
        if set_temperature > 50:
            set_temperature = 50
        if set_temperature < 0:
            set_temperature = 0

        # if temperatur is set, always fall back to manual mode
        set_function_mode = self.get_const_value(VIMAR_CLIMATE_MANUAL)

        set_hvac_mode = (self.get_const_value(VIMAR_CLIMATE_HEAT), self.get_const_value(VIMAR_CLIMATE_COOL))[
            self.hvac_mode == HVAC_MODE_COOL
        ]

        _LOGGER.info("Vimar Climate setting target temperature: %s", str(set_temperature))
        _LOGGER.info("Vimar Climate setting setup mode to manual: %s", set_function_mode)

        if self.climate_type == "heat_cool":
            self.change_state(
                "setpoint",
                str(set_temperature),
                "unita",
                self.get_state("unita"),
                "stagione",
                set_hvac_mode,
                "centralizzato",
                "1",
                "funzionamento",
                set_function_mode,
            )
        elif self.climate_type == "heat_cool_fancoil":
            # stato_principale_condizionamento and stato_principale_riscaldamento are results not states - i think
            self.change_state(
                "setpoint",
                str(set_temperature),
                "unita",
                self.get_state("unita"),
                "regolazione",
                set_hvac_mode,
                "funzionamento",
                set_function_mode,
            )
        # self.change_state('funzionamento', set_function_mode, 'setpoint', set_temperature)

    def set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        self.change_state("setpoint", str(humidity))

    # helper

    @property
    def climate_type(self):
        """Return type of climate control - either has heating and cooling or also fancoil."""
        if self.has_state("velocita_fancoil"):
            return "heat_cool_fancoil"
        elif self.has_state("temperatura_misurata") or self.has_state("temperatura"):
            return "heat_cool"
        elif self.has_state("dynamic_mode"):
            return "dry"

    def get_const_value(self, const):
        """Return ids depending on the climate type."""
        # thermostat I (funzionamento)
        # NO-OPTIONALS
        # 0 .. off  VIMAR_CLIMATE_OFF_I
        # 6 .. manual  VIMAR_CLIMATE_MANUAL_I
        # 7 .. manual timed
        # 8 .. auto  VIMAR_CLIMATE_AUTO_I

        # thermostat II (funzionamento)
        # 0 (automatic)  VIMAR_CLIMATE_AUTO_II
        # 1 (manual)  VIMAR_CLIMATE_MANUAL_II
        # 2 (so called 'reduction')  I guess a kind of energy saving mode, never used
        # 3 (away)  Away mode (If you use an extreme setpoint - eg. 31° for cooling - is equivalent of being off)
        # 5 (manual for a certain time)
        # 6 (off)  VIMAR_CLIMATE_OFF_II

        if self.climate_type == "heat_cool":
            if const == VIMAR_CLIMATE_OFF:
                return VIMAR_CLIMATE_OFF_I
            elif const == VIMAR_CLIMATE_MANUAL:
                return VIMAR_CLIMATE_MANUAL_I
            elif const == VIMAR_CLIMATE_AUTO:
                return VIMAR_CLIMATE_AUTO_I
            elif const == VIMAR_CLIMATE_COOL:
                return VIMAR_CLIMATE_COOL_I
            elif const == VIMAR_CLIMATE_HEAT:
                return VIMAR_CLIMATE_HEAT_I
            else:
                return None
        elif self.climate_type == "heat_cool_fancoil":
            if const == VIMAR_CLIMATE_OFF:
                return VIMAR_CLIMATE_OFF_II
            elif const == VIMAR_CLIMATE_MANUAL:
                return VIMAR_CLIMATE_MANUAL_II
            elif const == VIMAR_CLIMATE_AUTO:
                return VIMAR_CLIMATE_AUTO_II
            elif const == VIMAR_CLIMATE_COOL:
                return VIMAR_CLIMATE_COOL_II
            elif const == VIMAR_CLIMATE_HEAT:
                return VIMAR_CLIMATE_HEAT_II
            else:
                return None


# end class VimarClimate
