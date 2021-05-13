"""Platform for scene integration."""

import logging
from homeassistant.components.scene import Scene
from .vimar_entity import (VimarEntity, vimar_setup_platform)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vimar Scene platform."""
    vimar_setup_platform(VimarScene, hass, async_add_entities, discovery_info)


class VimarScene(VimarEntity, Scene):
    """Provide Vimar scenees and scenes."""

    _platform = "scene"

    def __init__(self, device_id, vimarconnection, vimarproject, coordinator):
        """Initialize the scene."""
        VimarEntity.__init__(self, device_id, vimarconnection, vimarproject, coordinator)

    # scene properties

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        # return (self.is_on, True)[self.is_on is None]
        return True

    # async getter and setter

    async def async_activate(self, **kwargs) -> None:
        """Activate scene. Try to get entities into requested state."""
        if self.has_state('on/off'):
            self.change_state('on/off', '1')

        elif self.has_state('comando'):
            self.change_state('comando', '0')


# end class VimarScene
