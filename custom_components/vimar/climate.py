"""Platform for climate integration."""

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    FAN_ON,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .const import (
    VIMAR_CLIMATE_AUTO,
    VIMAR_CLIMATE_AUTO_I,
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
from .const import DEVICE_TYPE_CLIMATES as CURR_PLATFORM
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Climate platform."""
    vimar_setup_entry(VimarClimate, CURR_PLATFORM, hass, entry, async_add_devices)


class VimarClimate(VimarEntity, ClimateEntity):
    """Provides a Vimar climates."""

    # {'status_id': '2129', 'status_value': '0', 'status_range': 'min=0|max=1'},
    # 'regolazione': {'status_id': '2131', 'status_value': '2', 'status_range': ''},
    # 'modalita_fancoil': {'status_id': '2135', 'status_value': '0', 'status_range': 'min=0|max=1'},
    # 'velocita_fancoil': {'status_id': '2137', 'status_value': '0', 'status_range': 'min=0|max=100'},
    # 'funzionamento': {'status_id': '2139', 'status_value': '6', 'status_range': ''},
    # 'setpoint': {'status_id': '2146', 'status_value': '21.00', 'status_range': 'min=-273|max=670760'},
    # 'temporizzazione': {'status_id': '2152', 'status_value': '1', 'status_range': 'min=0|max=65535'},
    # 'temperatura_misurata': {'status_id': '2160', 'status_value': '24.40', 'status_range': 'min=-273|max=670760'},
    # 'stato_boost on/off': {'status_id': '2163', 'status_value': '0', 'status_range': 'min=0|max=1'},
    # 'stato_principale_condizionamento on/off': {'status_id': '2164', 'status_value': '0', 'status_range': 'min=0|max=1'},
    # 'stato_principale_riscaldamento on/off': {'status_id': '2165', 'status_value': '0', 'status_range': 'min=0|max=1'},
    # 'uscita4': {'status_id': '2944', 'status_value': 'non_utilizzata', 'status_range':
    #   'principale_riscaldamento=0|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'},
    # 'uscita3': {'status_id': '2945', 'status_value': 'non_utilizzata', 'status_range':
    #   'principale_riscaldamento=0|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'},
    # 'uscita2': {'status_id': '2946', 'status_value': 'non_utilizzata', 'status_range':
    #   'principale_riscaldamento=0|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'},
    # 'uscita1': {'status_id': '2947', 'status_value': 'CH_Uscita_ValvolaOnOff', 'status_range':
    #    'principale_riscaldamento=1|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'},
    # 'forzatura off': {'status_id': '3282', 'status_value': '0', 'status_range': ''}}

    # # my climate (heat_cool)
    # Row000004: '947','funzionamento','-1','0'  #mode of operation on/off
    # Row000005: '948','centralizzato','-1','1'
    # Row000006: '949','stagione','-1','1'  # heat/cool
    # Row000007: '950','terziario','-1','0'
    # Row000008: '951','on/off','-1','0' # idle/working
    # Row000009: '952','setpoint','-1','15.6'  #desired temperature
    # Row000010: '953','temporizzazione','-1','0'  #timer (forcing temp)
    # Row000011: '954','temperatura','-1','25.6'  #current temp
    # Row000014: '959','unita','-1','0' #unit of measurement

    # # other climate (heat_cool_fancoil)
    # Row000001: 'ID','NAME','STATUS_ID','CURRENT_VALUE'
    # Row000006: '62791','forzatura off','-1','0'  #i don't know
    # Row000007: '62793','allarme_massetto','-1','0'  #alarm temp for cooling floor
    # Row000008: '62795','regolazione','-1','1'  # heating/cooling/neutral zone
    # Row000009: '62799','modalita_fancoil','-1','0'  #fan auto or manual
    # Row000010: '62801','velocita_fancoil','-1','0'  #fan speed
    # Row000011: '62803','funzionamento','-1','6'  #mode of operation on/off
    # Row000012: '62811','setpoint','-1','25.00'  #desired temperature
    # Row000013: '62819','temporizzazione','-1','1'  #timer (forcing temp)
    # Row000014: '62830','temperatura_misurata','-1','25.70'  #current temp
    # Row000015: '62833','stato_boost on/off','-1','0'  #activates second output to reach the setpoint first
    # Row000016: '62834','stato_principale_condizionamento on/off','-1','0'  #cooling on/ff
    # Row000017: '62835','stato_principale_riscaldamento on/off','-1','0'  #heating on/ff

    def __init__(self, coordinator, device_id: int):
        """Initialize the climate."""
        VimarEntity.__init__(self, coordinator, device_id)

        # self.entity_id = "climate." + self._name.lower() + "_" + self._device_id

    # climate properties
    @property
    def entity_platform(self):
        """Return the platform of the entity."""
        return CURR_PLATFORM

    @property
    def is_on(self):
        """Return True if the device is on or completely off."""
        return (True, False)[
            self.get_state("funzionamento") == self.get_const_value(VIMAR_CLIMATE_OFF)
        ]

    @property
    def supported_features(self):
        """Flag supported features. The device supports a target temperature."""
        flags = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
        if self.has_state("velocita_fancoil"):
            flags |= ClimateEntityFeature.FAN_MODE
        if self.has_state("stato_boost on/off"):
            flags |= ClimateEntityFeature.AUX_HEAT
        return flags

    @property
    def current_temperature(self):
        """Return current temperature."""
        if self.has_state("temperatura"):
            return float(self.get_state("temperatura") or 0)
        if self.has_state("temperatura_misurata"):
            return float(self.get_state("temperatura_misurata") or 0)

    @property
    def current_humidity(self):
        """Return current humidity."""
        if self.has_state("umidita"):
            return float(self.get_state("umidita") or 0)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return float(self.get_state("setpoint") or 0)

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.1

    @property
    def temperature_unit(self):
        """Return unit of temperature measurement for the system (UnitOfTemperature.CELSIUS or UnitOfTemperature.FAHRENHEIT)."""
        # TODO - find a way to handle different units from vimar device
        if self.has_state("unita"):
            return (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS)[
                self.get_state("unita") == "0"
            ]
        else:
            return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self):
        """Return target operation (e.g.heat, cool, auto, off). Used to determine state."""
        # can be HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF
        # will never be HVACMode.AUTO, because funzionamento can be auto in both (HEAT and COOL) hvac modes.
        # if its not on, its off
        if not self.is_on:
            return HVACMode.OFF

        if self.climate_type == "heat_cool":
            if self.get_const_value(VIMAR_CLIMATE_AUTO) == self.get_state(
                "funzionamento"
            ):
                return HVACMode.AUTO
            else:
                return (HVACMode.HEAT, HVACMode.COOL)[
                    self.get_state("stagione")
                    == self.get_const_value(VIMAR_CLIMATE_COOL)
                ]
        else:
            if self.get_const_value(VIMAR_CLIMATE_AUTO) == self.get_state(
                "funzionamento"
            ):
                return HVACMode.AUTO
            else:
                return (HVACMode.HEAT, HVACMode.COOL)[
                    self.get_state("regolazione")
                    == self.get_const_value(VIMAR_CLIMATE_COOL)
                ]

            # if self.has_state('stato_principale_condizionamento on/off') and self.get_state('stato_principale_condizionamento on/off') == '1':
            #     return HVACMode.COOL
            # elif self.has_state('stato_principale_riscaldamento on/off') and self.get_state('stato_principale_riscaldamento on/off') == '1':
            #     return HVACMode.HEAT
            # else:
            #     return HVACMode.OFF

    @property
    def hvac_modes(self):
        """List of available operation modes. See below."""
        # button for auto is still there, to clear manual mode, but will not change highlighted icon
        return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF, HVACMode.AUTO]

    @property
    def hvac_action(self):
        """Return current HVAC action (heating, cooling, idle, off)."""
        # HVACAction.HEATING, HVACAction.COOLING, HVACAction.OFF, HVACAction.IDLE
        if not self.is_on:
            return HVACAction.OFF

        # on/off is only available in heat_cool
        if self.has_state("on/off") and self.get_state("on/off") == "0":
            return HVACAction.IDLE

        # if not self.is_running:
        #     return HVACAction.IDLE

        if self.climate_type == "heat_cool":
            return (HVACAction.HEATING, HVACAction.COOLING)[
                self.get_state("stagione") == self.get_const_value(VIMAR_CLIMATE_COOL)
            ]
        else:
            if (
                self.has_state("stato_principale_condizionamento on/off")
                and self.get_state("stato_principale_condizionamento on/off") == "1"
            ):
                return HVACAction.COOLING
            elif (
                self.has_state("stato_principale_riscaldamento on/off")
                and self.get_state("stato_principale_riscaldamento on/off") == "1"
            ):
                return HVACAction.HEATING
            else:
                return HVACAction.IDLE

    @property
    def is_aux_heat(self):
        """Return True if an auxiliary heater is on. Requires ClimateEntityFeature.AUX_HEAT."""
        if self.has_state("stato_boost on/off"):
            return self.get_state("stato_boost on/off") != "0"

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes. Requires ClimateEntityFeature.FAN_MODE."""
        return [FAN_ON, FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    @property
    def fan_mode(self):
        """Return the current fan mode. Requires ClimateEntityFeature.FAN_MODE."""
        if self.has_state("modalita_fancoil"):
            if self.get_state("modalita_fancoil") == "0":
                return FAN_OFF

        if self.has_state("velocita_fancoil"):
            fancoil_speed = float(self.get_state("velocita_fancoil") or 0)

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
                self.change_state(
                    "modalita_fancoil", "1", "velocita_fancoil", fancoil_speed
                )

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
        set_hvac_mode = None

        if hvac_mode in [HVACMode.COOL, HVACMode.HEAT]:

            # if heating or cooling is pressed, got to automode
            set_function_mode = self.get_const_value(VIMAR_CLIMATE_AUTO)
            set_hvac_mode = (
                self.get_const_value(VIMAR_CLIMATE_HEAT),
                self.get_const_value(VIMAR_CLIMATE_COOL),
            )[hvac_mode == HVACMode.COOL]

            _LOGGER.info(
                "Vimar Climate setting setup mode to heat/cool: %s", set_function_mode
            )

            # DONE - get current set_temperatur and set it again

        elif hvac_mode in [HVACMode.AUTO]:
            set_function_mode = self.get_const_value(VIMAR_CLIMATE_AUTO)

            set_hvac_mode = (
                self.get_const_value(VIMAR_CLIMATE_HEAT),
                self.get_const_value(VIMAR_CLIMATE_COOL),
            )[self.hvac_mode == HVACMode.COOL]

            _LOGGER.info(
                "Vimar Climate setting setup mode to auto: %s", set_function_mode
            )
            # we only clear manual mode - no further settings
            # self.change_state('funzionamento', set_function_mode)

        elif hvac_mode in [HVACMode.OFF]:
            set_function_mode = self.get_const_value(VIMAR_CLIMATE_OFF)

            set_hvac_mode = (
                self.get_const_value(VIMAR_CLIMATE_HEAT),
                self.get_const_value(VIMAR_CLIMATE_COOL),
            )[self.hvac_mode == HVACMode.COOL]

            _LOGGER.info(
                "Vimar Climate setting setup mode to off: %s", set_function_mode
            )
            # self.change_state('funzionamento', set_function_mode)

        _LOGGER.info("Vimar Climate setting hvac_mode: %s", set_hvac_mode)
        _LOGGER.info(
            "Vimar Climate resetting target temperature: %s", self.target_temperature
        )

        if set_hvac_mode is not None:
            if self.climate_type == "heat_cool":
                self.change_state(
                    "funzionamento",
                    set_function_mode,
                    "stagione",
                    set_hvac_mode,
                    "setpoint",
                    self.target_temperature,
                )
            elif self.climate_type == "heat_cool_fancoil":
                self.change_state(
                    "funzionamento",
                    set_function_mode,
                    "regolazione",
                    set_hvac_mode,
                    "setpoint",
                    self.target_temperature,
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

        set_hvac_mode = (
            self.get_const_value(VIMAR_CLIMATE_HEAT),
            self.get_const_value(VIMAR_CLIMATE_COOL),
        )[self.hvac_mode == HVACMode.COOL]

        _LOGGER.info(
            "Vimar Climate setting target temperature: %s", str(set_temperature)
        )
        _LOGGER.info(
            "Vimar Climate setting setup mode to manual: %s", set_function_mode
        )

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

    # helper

    @property
    def climate_type(self):
        """Return type of climate control - either has heating and cooling or also fancoil."""
        if self.has_state("velocita_fancoil"):
            return "heat_cool_fancoil"
        else:
            return "heat_cool"

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
        else:
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
