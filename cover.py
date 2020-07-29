"""Platform for cover integration."""

import logging
from homeassistant.components.cover import (SUPPORT_CLOSE, SUPPORT_OPEN,
                                            SUPPORT_STOP)
from .vimar_entity import (VimarEntity, vimar_setup_platform)
try:
    from homeassistant.components.cover import CoverEntity
except ImportError:
    from homeassistant.components.cover import CoverDevice as CoverEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Cover platform."""
    vimar_setup_platform(VimarCover, hass, async_add_entities, discovery_info)


# see: https://developers.home-assistant.io/docs/core/entity/cover
class VimarCover(VimarEntity, CoverEntity):
    """Provides a Vimar cover."""

    # _platform = "cover"
    # see:
    # https://developers.home-assistant.io/docs/entity_index/#generic-properties
    # Return True if the state is based on our assumption instead of reading it from the device. this will ignore is_closed state
    # assumed_state = True

    def __init__(self, device_id, vimarconnection, vimarproject, coordinator):
        """Initialize the cover."""
        VimarEntity.__init__(self, device_id, vimarconnection, vimarproject, coordinator)
        # self.entity_id = "cover." + self._name.lower() + "_" + self._device_id

        # _state = False .. 0, stop has not been pressed
        # _state = True .. 1, stop has been pressed
        # _direction = 0 .. upwards
        # _direction = 1 .. downards

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if _state (stopped) is 1, than stopped was pressed, therefor it cannot be completely closed
        # if its 0, and direction 1, than it was going downwards and it was
        # never stopped, therefor it is closed now
        if self.get_state('stop up/stop down') != '0':
            return None

        if self.get_state('up/down') == '1':
            return True
        elif self.get_state('up/down') == '0':
            return False
        else:
            return None

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return (self.is_closed, True)[self.is_closed is None]

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    # async getter and setter

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self.change_state('up/down', '1')

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self.change_state('up/down', '0')

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.change_state('stop up/stop down', '1')

    # private helper methods

# end class VimarCover
