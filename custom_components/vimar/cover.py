"""Platform for cover integration."""

import logging

from homeassistant.components.cover import (ATTR_POSITION, ATTR_TILT_POSITION,
                                            SUPPORT_CLOSE, SUPPORT_CLOSE_TILT,
                                            SUPPORT_OPEN, SUPPORT_OPEN_TILT,
                                            SUPPORT_SET_POSITION,
                                            SUPPORT_SET_TILT_POSITION,
                                            SUPPORT_STOP, SUPPORT_STOP_TILT)

from .vimar_entity import VimarEntity, vimar_setup_entry

try:
    from homeassistant.components.cover import CoverEntity
except ImportError:
    from homeassistant.components.cover import CoverDevice as CoverEntity

from .const import DEVICE_TYPE_COVERS as CURR_PLATFORM

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the Vimar Switch platform."""
    vimar_setup_entry(VimarCover, CURR_PLATFORM, hass, entry, async_add_devices)

# see: https://developers.home-assistant.io/docs/core/entity/cover
class VimarCover(VimarEntity, CoverEntity):
    """Provides a Vimar cover."""

    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    # Return True if the state is based on our assumption instead of reading it from the device. this will ignore is_closed state
    assumed_state = True

    def __init__(self, coordinator, device_id: int):
        """Initialize the cover."""
        VimarEntity.__init__(self, coordinator, device_id)
        # self.entity_id = "cover." + self._name.lower() + "_" + self._device_id

        # _state = False .. 0, stop has not been pressed
        # _state = True .. 1, stop has been pressed
        # _direction = 0 .. upwards
        # _direction = 1 .. downards

    @property
    def entity_platform(self):
        return CURR_PLATFORM

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if _state (stopped) is 1, than stopped was pressed, therefor it cannot be completely closed
        # if its 0, and direction 1, than it was going downwards and it was
        # never stopped, therefor it is closed now
        # if self.get_state('stop up/stop down') != '0':
        #     return None

        if self.get_state("up/down") == "1":
            return True
        elif self.get_state("up/down") == "0":
            return False
        else:
            return None

    @property
    def current_cover_position(self):
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self.has_state("position"):
            return 100 - int(self.get_state("position"))
        else:
            return None

    @property
    def current_cover_tilt_position(self):
        """
        Return current position of cover tilt.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self.has_state("slat_position"):
            return 100 - int(self.get_state("slat_position"))
        else:
            return None

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return (self.is_closed, True)[self.is_closed is None]

    @property
    def supported_features(self):
        """Flag supported features."""
        flags = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
        if self.has_state("position"):
            flags |= SUPPORT_SET_POSITION
        if self.has_state("slat_position") and self.has_state("clockwise/counterclockwise"):
            flags |= SUPPORT_STOP_TILT | SUPPORT_OPEN_TILT | SUPPORT_CLOSE_TILT | SUPPORT_SET_TILT_POSITION
            # flags |= SUPPORT_STOP_TILT | SUPPORT_SET_TILT_POSITION

        return flags

    # async getter and setter

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self.change_state("up/down", "1")

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self.change_state("up/down", "0")

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.change_state("stop up/stop down", "1")

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        if kwargs:
            if ATTR_POSITION in kwargs and self.has_state("position"):
                self.change_state("position", 100 - int(kwargs[ATTR_POSITION]))

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        self.change_state("clockwise/counterclockwise", "0")

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        self.change_state("clockwise/counterclockwise", "1")

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position. vimar 100 is down and 0 is up, hass: 100 is up and 0 is down."""
        if kwargs:
            if ATTR_TILT_POSITION in kwargs and self.has_state("slat_position"):
                self.change_state("slat_position", 100 - int(kwargs[ATTR_TILT_POSITION]))

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover."""
        self.change_state("stop up/stop down", "1")

    # private helper methods


# end class VimarCover
