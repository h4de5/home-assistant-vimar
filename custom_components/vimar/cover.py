"""Platform for cover integration - CON ENTITY OPTIONS.

Configurazione travel times tramite UI di ogni singola cover!
"""

import logging
from datetime import datetime, timedelta

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
import voluptuous as vol

from .const import (
    CONF_COVER_POSITION_MODE,
    COVER_POSITION_MODE_AUTO,
    COVER_POSITION_MODE_NATIVE,
    COVER_POSITION_MODE_TIME_BASED,
    COVER_POSITION_MODE_LEGACY,
    DEFAULT_COVER_POSITION_MODE,
    DEVICE_TYPE_COVERS as CURR_PLATFORM,
)
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)

DEFAULT_TRAVEL_TIME_UP = 28
DEFAULT_TRAVEL_TIME_DOWN = 26
POSITION_UPDATE_INTERVAL = 0.2
UI_UPDATE_THRESHOLD = 1  # Aggiorna UI ogni 1% di variazione
RELAY_DELAY = 0.5        # Compensazione ritardo relè Vimar in secondi
GRACE_SECONDS = 6        # Finestra di immunità post-STOP da HA:
                         # il webserver Vimar non espone metadati sulla sorgente
                         # del comando (DPADD_OBJECT ha solo CURRENT_VALUE),
                         # quindi sopprimiamo le detection di pulsante fisico
                         # per GRACE_SECONDS dopo ogni stop inviato da HA.

# Chiavi per storage entity options
CONF_TRAVEL_TIME_UP = "travel_time_up"
CONF_TRAVEL_TIME_DOWN = "travel_time_down"


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Cover platform."""
    vimar_setup_entry(VimarCover, CURR_PLATFORM, hass, entry, async_add_devices)

    # Registra servizio per configurare travel times
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "set_travel_times",
        {
            vol.Required(CONF_TRAVEL_TIME_UP): vol.All(int, vol.Range(min=1, max=300)),
            vol.Required(CONF_TRAVEL_TIME_DOWN): vol.All(int, vol.Range(min=1, max=300)),
        },
        "async_set_travel_times",
    )


class VimarCover(VimarEntity, CoverEntity, RestoreEntity):
    """Provides a Vimar cover with time-based position tracking."""

    @property
    def assumed_state(self) -> bool:
        """Return True if state is assumed (estimated), False if known (certain).

        True = State is ASSUMED/ESTIMATED (cannot access real position)
        False = State is KNOWN/CERTAIN (have accurate position info)

        LEGACY mode: Always True (like original master branch)
        NATIVE mode: True if no sensor, False if has sensor
        TIME_BASED mode: False (calculated position is "known")
        AUTO mode: False (either native sensor or time-based calculation)
        """
        mode = self._get_position_mode()

        if mode == COVER_POSITION_MODE_LEGACY:
            # LEGACY: Always True (original master behavior)
            return True

        if mode == COVER_POSITION_MODE_NATIVE:
            # NATIVE: True if no sensor (assumed), False if has sensor (known)
            return not self.has_state("position")

        # TIME_BASED or AUTO modes:
        # - Time-based tracking provides calculated position -> False (known)
        # - Native sensor provides hardware position -> False (known)
        return False

    def __init__(self, coordinator, device_id: int):
        """Initialize the cover."""
        VimarEntity.__init__(self, coordinator, device_id)

        # Time-based tracking
        self._tb_position = None
        self._tb_target = None
        self._tb_start_time = None
        self._tb_start_position = None
        self._tb_operation = None
        self._tb_unsub = None
        self._tb_last_updown = None
        self._tb_last_reported_position = None  # Per threshold UI
        self._tb_ha_command_active = False  # Flag per distinguere comandi HA da pulsanti fisici
        self._tb_ha_stop_time = None        # Timestamp ultimo STOP inviato da HA (grace period)

        # Travel times (saranno caricati in async_added_to_hass)
        self._travel_time_up = DEFAULT_TRAVEL_TIME_UP
        self._travel_time_down = DEFAULT_TRAVEL_TIME_DOWN

    def _get_position_mode(self) -> str:
        """Get configured position mode from coordinator."""
        if hasattr(self.coordinator, "vimarconfig"):
            return self.coordinator.vimarconfig.get(
                CONF_COVER_POSITION_MODE, DEFAULT_COVER_POSITION_MODE
            )
        return DEFAULT_COVER_POSITION_MODE

    def _use_time_based_tracking(self) -> bool:
        """Determine if time-based tracking should be used."""
        mode = self._get_position_mode()

        if mode == COVER_POSITION_MODE_LEGACY:
            # LEGACY mode: disable all time-based tracking (original master behavior)
            return False
        elif mode == COVER_POSITION_MODE_TIME_BASED:
            # Force time-based even if native position is available
            return True
        elif mode == COVER_POSITION_MODE_NATIVE:
            # Never use time-based, rely on native only
            return False
        else:  # COVER_POSITION_MODE_AUTO or default
            # Use time-based only if native position is not available
            return not self.has_state("position")

    async def async_set_travel_times(self, travel_time_up: int, travel_time_down: int):
        """Service to set travel times for this cover."""
        self._travel_time_up = travel_time_up
        self._travel_time_down = travel_time_down

        # Salva nelle entity options
        if hasattr(self, "registry_entry") and self.registry_entry:
            from homeassistant.helpers import entity_registry as er

            entity_reg = er.async_get(self.hass)
            entity_reg.async_update_entity_options(
                self.entity_id,
                "cover",
                {
                    CONF_TRAVEL_TIME_UP: travel_time_up,
                    CONF_TRAVEL_TIME_DOWN: travel_time_down,
                }
            )

        _LOGGER.info(
            "%s: Travel times updated - up: %ds, down: %ds",
            self.name, travel_time_up, travel_time_down
        )

    async def async_added_to_hass(self):
        """Restore state when added to hass."""
        await super().async_added_to_hass()

        _LOGGER.debug("%s: === async_added_to_hass START ===", self.name)
        _LOGGER.debug("%s: Position mode: %s", self.name, self._get_position_mode())
        _LOGGER.debug("%s: Use time-based tracking: %s", self.name, self._use_time_based_tracking())

        # Carica travel times dalle entity options
        if hasattr(self, "registry_entry") and self.registry_entry:
            options = self.registry_entry.options.get("cover", {})

            saved_up = options.get(CONF_TRAVEL_TIME_UP)
            saved_down = options.get(CONF_TRAVEL_TIME_DOWN)

            if saved_up is not None:
                self._travel_time_up = int(saved_up)
            if saved_down is not None:
                self._travel_time_down = int(saved_down)

            if (
                self._travel_time_up != DEFAULT_TRAVEL_TIME_UP
                or self._travel_time_down != DEFAULT_TRAVEL_TIME_DOWN
            ):
                _LOGGER.info(
                    "%s: Custom travel times loaded - up: %ds, down: %ds",
                    self.name, self._travel_time_up, self._travel_time_down
                )

        # Ripristina posizione solo se usiamo time-based tracking
        if self._use_time_based_tracking():
            old_state = await self.async_get_last_state()

            _LOGGER.debug("%s: old_state exists = %s", self.name, old_state is not None)

            if old_state:
                _LOGGER.debug("%s: old_state.state = '%s'", self.name, old_state.state)
                position_attr = old_state.attributes.get("current_position")
                _LOGGER.debug("%s: current_position value = %s", self.name, position_attr)

            if old_state and old_state.attributes.get("current_position") is not None:
                self._tb_position = old_state.attributes["current_position"]
                _LOGGER.info("%s: Position restored: %s%%", self.name, self._tb_position)
            else:
                self._tb_position = 0
                _LOGGER.info("%s: New cover, default position: 0%% (closed)", self.name)
        else:
            mode = self._get_position_mode()
            if mode == COVER_POSITION_MODE_LEGACY:
                _LOGGER.debug("%s: LEGACY mode - no time-based tracking", self.name)
            else:
                _LOGGER.debug("%s: Using native position from webserver", self.name)

        self._tb_last_updown = self.get_state("up/down")
        self._tb_last_reported_position = self._tb_position
        _LOGGER.debug("%s: === async_added_to_hass END ===", self.name)

    async def async_will_remove_from_hass(self):
        """Cleanup when removed."""
        if self._tb_unsub:
            self._tb_unsub()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        super()._handle_coordinator_update()
        if self._use_time_based_tracking():
            self._tb_check_vimar_state()

    def _tb_check_vimar_state(self):
        """Controlla stato Vimar e gestisci movimenti fisici."""
        current_updown = self.get_state("up/down")

        # Durante tracking da comandi HA, verifica solo interruzioni (STOP fisico)
        if self._tb_operation:
            expected_updown = "0" if self._tb_operation == "opening" else "1"

            # Se lo stato cambia inaspettatamente durante tracking HA
            if current_updown != expected_updown:
                _LOGGER.info(
                    "%s: Physical STOP detected during HA tracking! up/down=%s (was %s)",
                    self.name, current_updown, self._tb_operation
                )
                # Reset del flag comando HA perché è stato interrotto fisicamente
                self._tb_ha_command_active = False
                self.hass.async_create_task(self._tb_stop_tracking())

            # FIX: aggiorna sempre _tb_last_updown durante il tracking, altrimenti
            # il valore stantio dopo lo stop causa una falsa detection di pulsante fisico
            self._tb_last_updown = current_updown
            return

        # Rileva movimenti da pulsanti fisici solo quando:
        # 1. NON c'è tracking attivo (_tb_operation è None)
        # 2. Lo stato up/down è cambiato rispetto all'ultimo valore
        # 3. NON è un comando HA recente (_tb_ha_command_active)
        # 4. NON siamo nel grace period post-STOP di HA
        #    (il webserver Vimar non distingue la sorgente del comando:
        #    DPADD_OBJECT espone solo CURRENT_VALUE senza metadati di origine)
        in_grace_period = (
            self._tb_ha_stop_time is not None
            and (datetime.now() - self._tb_ha_stop_time).total_seconds() < GRACE_SECONDS
        )

        if current_updown != self._tb_last_updown and not self._tb_ha_command_active:
            if in_grace_period:
                _LOGGER.debug(
                    "%s: Ignoring up/down change (%s->%s) - in grace period (%.1fs remaining)",
                    self.name,
                    self._tb_last_updown,
                    current_updown,
                    GRACE_SECONDS - (datetime.now() - self._tb_ha_stop_time).total_seconds(),
                )
            elif current_updown == "0":
                self._tb_position = 100
                _LOGGER.info("%s: Physical button OPEN -> Position set to 100%%", self.name)
                self._tb_last_reported_position = 100
                self.async_write_ha_state()

            elif current_updown == "1":
                self._tb_position = 0
                _LOGGER.info("%s: Physical button CLOSE -> Position set to 0%%", self.name)
                self._tb_last_reported_position = 0
                self.async_write_ha_state()

        self._tb_last_updown = current_updown

    async def _tb_start_tracking(self, opening: bool, target: int = None):
        """Avvia tracking temporale per comandi HA."""
        operation = "opening" if opening else "closing"

        if self._tb_operation == operation:
            return

        self._tb_operation = operation
        self._tb_start_time = datetime.now()
        self._tb_start_position = self._tb_position
        self._tb_target = target if target is not None else (100 if opening else 0)
        self._tb_last_reported_position = self._tb_position

        # Imposta flag comando HA per evitare false detection di pulsanti fisici
        self._tb_ha_command_active = True
        # Reset grace period: un nuovo movimento annulla la finestra precedente
        self._tb_ha_stop_time = None

        if self._tb_unsub:
            self._tb_unsub()

        self._tb_unsub = async_track_time_interval(
            self.hass,
            self._tb_update_position,
            timedelta(seconds=POSITION_UPDATE_INTERVAL),
        )

        _LOGGER.debug(
            "%s: Tracking %s from %s%% to %s%%",
            self.name, operation, self._tb_position, self._tb_target
        )
        self.async_write_ha_state()

    async def _tb_stop_tracking(self):
        """Ferma tracking e calcola posizione finale."""
        if self._tb_unsub:
            self._tb_unsub()
            self._tb_unsub = None

        if self._tb_start_time:
            self._tb_calculate_position()

        _LOGGER.info("%s: Stopped at %s%%", self.name, self._tb_position)

        self._tb_operation = None
        self._tb_start_time = None
        self._tb_target = None
        self._tb_last_reported_position = self._tb_position

        # Reset flag comando HA e avvia grace period:
        # per GRACE_SECONDS le detection di pulsante fisico sono soppresse
        # perché il protocollo Vimar non distingue la sorgente del comando.
        self._tb_ha_command_active = False
        self._tb_ha_stop_time = datetime.now()

        self.async_write_ha_state()

    @callback
    def _tb_update_position(self, now):
        """Aggiorna posizione durante tracking ogni 1%."""
        self._tb_calculate_position()

        should_stop = False
        send_stop_command = False

        if self._tb_position >= 100 and self._tb_operation == "opening":
            self._tb_position = 100
            should_stop = True
            send_stop_command = False

        elif self._tb_position <= 0 and self._tb_operation == "closing":
            self._tb_position = 0
            should_stop = True
            send_stop_command = False

        elif self._tb_target is not None:
            if self._tb_operation == "opening" and self._tb_position >= self._tb_target:
                self._tb_position = self._tb_target
                should_stop = True
                send_stop_command = (self._tb_target not in [0, 100])

            elif self._tb_operation == "closing" and self._tb_position <= self._tb_target:
                self._tb_position = self._tb_target
                should_stop = True
                send_stop_command = (self._tb_target not in [0, 100])

        if should_stop:
            if send_stop_command:
                _LOGGER.info(
                    "%s: Reached target %s%%, sending STOP",
                    self.name, self._tb_position
                )
                # FIX: async_stop_cover chiama già _tb_stop_tracking internamente,
                # non schedulare un task separato per evitare doppia esecuzione
                self.hass.async_create_task(self.async_stop_cover())
            else:
                _LOGGER.info(
                    "%s: Reached end-stop %s%%, mechanical stop (no STOP command)",
                    self.name, self._tb_position
                )
                self.hass.async_create_task(self._tb_stop_tracking())
        else:
            # Aggiorna UI ogni 1% di variazione (o più frequente se UI_UPDATE_THRESHOLD < 1)
            if self._tb_last_reported_position is None or \
               abs(self._tb_position - self._tb_last_reported_position) >= UI_UPDATE_THRESHOLD:
                self._tb_last_reported_position = self._tb_position
                self.async_write_ha_state()

    def _tb_calculate_position(self):
        """Calcola posizione attuale basata sul tempo trascorso con compensazione ritardo relè."""
        if not self._tb_start_time:
            return

        elapsed_total = (datetime.now() - self._tb_start_time).total_seconds()
        # Sottrae il ritardo stimato del relè (non scende sotto zero)
        elapsed_effective = max(0.0, elapsed_total - RELAY_DELAY)

        travel_time = (
            self._travel_time_up
            if self._tb_operation == "opening"
            else self._travel_time_down
        )
        percentage = (elapsed_effective / travel_time) * 100

        if self._tb_operation == "opening":
            self._tb_position = min(100, self._tb_start_position + percentage)
        else:
            self._tb_position = max(0, self._tb_start_position - percentage)

        self._tb_position = round(self._tb_position)

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    @property
    def is_closed(self) -> bool | None:
        mode = self._get_position_mode()

        if mode == COVER_POSITION_MODE_LEGACY:
            # LEGACY mode: original behavior from master branch
            if self.get_state("up/down") == "1":
                return True
            elif self.get_state("up/down") == "0":
                return False
            else:
                return None

        if not self._use_time_based_tracking():
            # Native mode - use traditional logic
            if self.get_state("up/down") == "1":
                return True
            elif self.get_state("up/down") == "0":
                return False
            else:
                return None

        # Time-based mode: handle robustly
        if self._tb_position is not None:
            return self._tb_position == 0
        return None

    @property
    def is_opening(self) -> bool:
        """Return True only during active opening operation.

        Home Assistant disables buttons based on is_closed and current_cover_position,
        NOT based on is_opening/is_closing. These properties only indicate ACTIVE movement.
        """
        if self._use_time_based_tracking():
            return self._tb_operation == "opening"
        return False

    @property
    def is_closing(self) -> bool:
        """Return True only during active closing operation.

        Home Assistant disables buttons based on is_closed and current_cover_position,
        NOT based on is_opening/is_closing. These properties only indicate ACTIVE movement.
        """
        if self._use_time_based_tracking():
            return self._tb_operation == "closing"
        return False

    @property
    def current_cover_position(self):
        mode = self._get_position_mode()

        if mode == COVER_POSITION_MODE_LEGACY:
            # LEGACY mode: only return position if native sensor available
            if self.has_state("position"):
                return 100 - int(self.get_state("position"))
            return None  # No position in legacy mode without sensor

        if not self._use_time_based_tracking() and self.has_state("position"):
            # Native mode
            return 100 - int(self.get_state("position"))
        # Time-based mode
        return self._tb_position

    @property
    def current_cover_tilt_position(self):
        if self.has_state("slat_position"):
            return 100 - int(self.get_state("slat_position"))
        return None

    @property
    def is_default_state(self):
        return (self.is_closed, True)[self.is_closed is None]

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features.

        In LEGACY mode, SET_POSITION is only available if hardware sensor exists.
        In other modes, SET_POSITION is always available.
        """
        mode = self._get_position_mode()

        flags = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
        )

        # SET_POSITION logic based on mode
        if mode == COVER_POSITION_MODE_LEGACY:
            # LEGACY mode: SET_POSITION only if native sensor available
            if self.has_state("position"):
                flags |= CoverEntityFeature.SET_POSITION
        else:
            # All other modes: always include SET_POSITION
            flags |= CoverEntityFeature.SET_POSITION

        if self.has_state("slat_position") and self.has_state(
            "clockwise/counterclockwise"
        ):
            flags |= (
                CoverEntityFeature.STOP_TILT
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )

        return flags

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        attrs = super().extra_state_attributes or {}
        attrs["position_mode"] = self._get_position_mode()
        attrs["uses_time_based_tracking"] = self._use_time_based_tracking()
        if self._use_time_based_tracking():
            attrs["travel_time_up"] = self._travel_time_up
            attrs["travel_time_down"] = self._travel_time_down
        return attrs

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if self._use_time_based_tracking():
            await self._tb_start_tracking(False, target=0)
        self.change_state("up/down", "1")

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if self._use_time_based_tracking():
            await self._tb_start_tracking(True, target=100)
        self.change_state("up/down", "0")

    async def async_stop_cover(self, **kwargs):
        if self._use_time_based_tracking():
            await self._tb_stop_tracking()
        self.change_state("stop up/stop down", "1")

    async def async_set_cover_position(self, **kwargs):
        if kwargs:
            if ATTR_POSITION in kwargs:
                target = int(kwargs[ATTR_POSITION])

                if not self._use_time_based_tracking() and self.has_state("position"):
                    # Native mode (or LEGACY with sensor)
                    self.change_state("position", 100 - target)
                else:
                    # FIX #3: _tb_position is None until async_added_to_hass runs.
                    # Guard against TypeError from comparing int with None.
                    if self._tb_position is None:
                        _LOGGER.debug(
                            "%s: set_cover_position called before position was initialized, "
                            "defaulting to 0 (closed)",
                            self.name,
                        )
                        self._tb_position = 0
                    # Time-based mode
                    if target > self._tb_position:
                        await self._tb_start_tracking(True, target=target)
                        self.change_state("up/down", "0")
                    elif target < self._tb_position:
                        await self._tb_start_tracking(False, target=target)
                        self.change_state("up/down", "1")

    async def async_open_cover_tilt(self, **kwargs):
        self.change_state("clockwise/counterclockwise", "0")

    async def async_close_cover_tilt(self, **kwargs):
        self.change_state("clockwise/counterclockwise", "1")

    async def async_set_cover_tilt_position(self, **kwargs):
        if kwargs:
            if ATTR_TILT_POSITION in kwargs and self.has_state("slat_position"):
                self.change_state(
                    "slat_position", 100 - int(kwargs[ATTR_TILT_POSITION])
                )

    async def async_stop_cover_tilt(self, **kwargs):
        self.change_state("stop up/stop down", "1")
