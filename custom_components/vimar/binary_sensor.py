"""Platform for binary_sensor integration."""

# import copy
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DEVICE_TYPE_BINARY_SENSOR as CURR_PLATFORM
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar BinarySensor platform."""
    vimar_setup_entry(VimarBinarySensor, CURR_PLATFORM, hass, entry, async_add_devices)


class VimarBinarySensor(VimarEntity, BinarySensorEntity):
    """Provide Vimar BinarySensor."""

    def __init__(self, coordinator, device_id: int):
        """Initialize the switch."""
        VimarEntity.__init__(self, coordinator, device_id)

        # self.entity_id = "switch." + self._name.lower() + "_" + self._device_id

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    # switch properties
    @property
    def is_on(self):
        """Return True if the device is on."""
        if self.has_state("on/off"):
            return self.get_state("on/off") == "1"
        # elif self.has_state('comando'):
        #     return self.get_state('comando') == '1'
        return None
