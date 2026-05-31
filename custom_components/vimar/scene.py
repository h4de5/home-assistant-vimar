"""Platform for scene integration."""

import logging
from datetime import datetime

from homeassistant.components.scene import Scene
from homeassistant.const import STATE_UNKNOWN
from homeassistant.util import dt as dt_util

from .const import DEVICE_TYPE_SCENES as CURR_PLATFORM
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Scene platform."""
    vimar_setup_entry(VimarScene, CURR_PLATFORM, hass, entry, async_add_devices)


class VimarScene(VimarEntity, Scene):
    """Provide Vimar scenes."""

    _last_activated: datetime | None = None

    def __init__(self, coordinator, device_id: int):
        """Initialize the scene."""
        VimarEntity.__init__(self, coordinator, device_id)

    async def async_added_to_hass(self) -> None:
        """Restore last activation timestamp from HA storage on startup.

        Scene inherits RestoreEntity, so async_get_last_state() reads the
        last persisted state from .storage/core.restore_state. The state
        string is the ISO 8601 timestamp we set in async_activate().
        """
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (STATE_UNKNOWN, "unknown", None):
            try:
                self._last_activated = dt_util.parse_datetime(last_state.state)
                _LOGGER.debug(
                    "Scene %s: restored last activation: %s",
                    self.name,
                    self._last_activated,
                )
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Scene %s: could not parse restored state '%s'",
                    self.name,
                    last_state.state,
                )

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    # scene properties

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return True

    @property
    def state(self) -> str:
        """Return the state of the scene.

        Returns the ISO 8601 timestamp of the last activation, or STATE_UNKNOWN
        if the scene has never been activated. The value is persisted across
        HA restarts via RestoreEntity (inherited from Scene base class).
        """
        if self._last_activated is None:
            return STATE_UNKNOWN
        return self._last_activated.isoformat()

    @property
    def extra_state_attributes(self):
        """Return scene-specific state attributes."""
        attrs = super().extra_state_attributes
        if self._last_activated is not None:
            attrs["last_activated"] = self._last_activated.isoformat()
        return attrs

    # async getter and setter

    async def async_activate(self, **kwargs) -> None:
        """Activate scene. Try to get entities into requested state.

        _last_activated is set BEFORE change_state() because change_state()
        internally calls request_statemachine_update() → async_write_ha_state().
        If we set it after, that first write would still see _last_activated=None
        and persist STATE_UNKNOWN instead of the timestamp.
        """
        self._last_activated = dt_util.utcnow()

        if self.has_state("on/off"):
            self.change_state("on/off", "1")
        elif self.has_state("comando"):
            self.change_state("comando", "0")
        else:
            # No Vimar state to write, but still update HA state machine
            self.async_write_ha_state()


# end class VimarScene
