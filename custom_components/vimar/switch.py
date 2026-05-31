"""Platform for switch integration."""

import logging

# FIX #17: import SwitchEntity from homeassistant.components.switch
# instead of the deprecated ToggleEntity path (HA >= 2021.x).
from homeassistant.components.switch import SwitchEntity

from .const import DEVICE_TYPE_SWITCHES as CURR_PLATFORM
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Switch platform."""
    vimar_setup_entry(VimarSwitch, CURR_PLATFORM, hass, entry, async_add_devices)


class VimarSwitch(VimarEntity, SwitchEntity):
    """Provide Vimar switches."""

    def __init__(self, coordinator, device_id: int):
        """Initialize the switch."""
        VimarEntity.__init__(self, coordinator, device_id)

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    @property
    def is_on(self):
        """Return True if the device is on."""
        if self.has_state("on/off"):
            return self.get_state("on/off") == "1"
        return None

    @property
    def is_default_state(self):
        """Return True when in default (off/unknown) state for icon selection.

        FIX #18: old expression (self.is_on, True)[self.is_on is None] returned
        self.is_on (False, index-0) when device was off, instead of True.
        Correct semantics: True unless device is explicitly on.
        """
        return not self.is_on  # True when off or unknown (None is falsy)

    async def async_turn_on(self, **kwargs):
        """Turn the Vimar switch on."""
        if self.has_state("on/off"):
            self.change_state("on/off", "1")

    async def async_turn_off(self, **kwargs):
        """Turn the Vimar switch off."""
        if self.has_state("on/off"):
            self.change_state("on/off", "0")
