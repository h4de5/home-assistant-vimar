"""Insteon base entity."""
import logging

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import Entity
from . import format_name

_LOGGER = logging.getLogger(__name__)


class VimarEntity(Entity):
    """Vimar abstract base entity."""

    _name = ''
    _device = []
    _device_id = 0

    ICON = "mdi:checkbox-marked"

    def __init__(self, device, device_id, vimarconnection):
        """Initialize the base entity."""
        self._device = device
        self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        self._state = False
        self._vimarconnection = vimarconnection

        self._reset_status()

    @property
    def should_poll(self):
        """ polling is needed for a Vimar device. """
        return True

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        # if 'icon' in self._device and self._device['icon']:
        #     return self._device['icon']
        #     # mdi-fan-off

        if isinstance(self._device['icon'], str):
            return self._device['icon']
        elif isinstance(self._device['icon'], list):
            return (self._device['icon'][1], self._device['icon'][0])[self.is_default_state]

        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device['device_class']

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return self._device_id

    @property
    def available(self):
        """Return True if entity is available."""
        return True

    def _reset_status(self):
        """set status from _device to class variables"""

    @property
    def is_default_state(self):
        """Returns True of in default state - resulting in default icon"""
        return self._state
