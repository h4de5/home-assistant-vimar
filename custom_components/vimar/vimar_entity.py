"""Insteon base entity."""
import logging

from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.entity import Entity
from .vimarlink.vimarlink import (VimarLink, VimarProject)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VimarEntity(Entity):
    """Vimar abstract base entity."""

    _device = []
    _device_id = 0
    _vimarconnection = None
    _vimarproject = None
    _coordinator = None
    _attributes = {}

    ICON = "mdi:checkbox-marked"

    def __init__(self, device_id: int, vimarconnection: VimarLink, vimarproject: VimarProject, coordinator):
        """Initialize the base entity."""
        self._coordinator = coordinator
        self._device_id = device_id
        self._vimarconnection = vimarconnection
        self._vimarproject = vimarproject
        self._reset_status()

        if self._device_id in self._vimarproject.devices:
            self._device = self._vimarproject.devices[self._device_id]
        else:
            _LOGGER.warning("Cannot find device #%s", self._device_id)

        # self.entity_id = self._platform + "." + self.name.lower().replace(" ", "_") + "_" + self._device_id

    @ property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @ property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.last_update_success

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        # _LOGGER.debug("async_added_to_hass %s called for %s", str(self.platform.platform), self.name)
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Disconnect from update signal."""
        _LOGGER.debug("async_will_remove_from_hass %s called for %s", str(self.platform.platform), self.name)
        self._coordinator.async_remove_listener(self.async_write_ha_state)

    # async def async_added_to_hass(self):
    #     """When entity is added to hass."""
    #     self.async_on_remove(
    #         self._coordinator.async_add_listener(
    #             # self.async_write_ha_state
    #             self.async_on_data_updated
    #         )
    #     )

    @property
    def name(self):
        """Return the name of the device."""
        return self._device['object_name']

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        # see: https://developers.home-assistant.io/docs/dev_101_states/
        return self._attributes

    def request_statemachine_update(self):
        """Update the hass status."""
        # with polling, we need to schedule another poll request
        self.async_schedule_update_ha_state()
        # if not self.should_poll:
        #     # with the central update coordinator, we do this
        #     self._coordinator.async_request_refresh()

    # def change_state(self, state: str, value: str,  *args):
    def change_state(self, *args, **kwargs):
        """Change state on bus system and the local device state."""
        state_changed = False
        if 'status' in self._device and self._device['status']:

            if args and len(args) > 0:
                iter_args = iter(args)
                for state, value in zip(iter_args, iter_args):
                    if state in self._device['status']:
                        state_changed = True
                        optionals = self._vimarconnection.get_optionals_param(state)
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status'][state]['status_id'], str(value), optionals)
                        self._device['status'][state]['status_value'] = str(value)
                    else:
                        _LOGGER.warning("Could not find state %s in device %s - %s - could not change value to: %s", state, self.name, self._device_id, value)

            if kwargs and len(kwargs) > 0:
                for state, value in kwargs.items():
                    if state in self._device['status']:
                        state_changed = True
                        optionals = self._vimarconnection.get_optionals_param(state)
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status'][state]['status_id'], str(value), optionals)
                        self._device['status'][state]['status_value'] = str(value)
                    else:
                        _LOGGER.warning("Could not find state %s in device %s - %s - could not change value to: %s", state, self.name, self._device_id, value)

            if state_changed:
                self.request_statemachine_update()

        # TODO - call async_add_executor_job with asyncio.gather maybe?

    def get_state(self, state):
        """Get state of the local device state."""
        if self.has_state(state):
            return self._device['status'][state]['status_value']
        else:
            _LOGGER.warning("Could not find state %s in device %s - %s - could not get value", state, self.name, self._device_id)
        return None

    def has_state(self, state):
        """Return true if local device has a given state."""
        if 'status' in self._device and self._device['status'] and state in self._device['status']:
            return True
        else:
            return False

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
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
        # _LOGGER.debug("Unique Id: " + DOMAIN + '_' + self._platform + '_' + self._device_id + " - " + self.name)
        return DOMAIN + '_' + self._platform + '_' + self._device_id

    def _reset_status(self):
        """Set status from _device to class variables."""

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return False


def vimar_setup_platform(vimar_entity_class: VimarEntity, hass: HomeAssistantType, async_add_entities, discovery_info=None):
    """Set up the Vimar Sensor platform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.debug("Vimar %s started!", discovery_info['hass_data_key'])
    entities = []

    vimarconnection = hass.data[DOMAIN]['connection']
    coordinator = hass.data[DOMAIN]['coordinator']
    vimarproject = hass.data[DOMAIN]['project']

    devices = vimarproject.get_by_device_type(discovery_info['hass_data_key'])

    if len(devices) != 0:
        for device_id, device in devices.items():
            if hasattr(vimar_entity_class, "get_entity_list") and callable(getattr(vimar_entity_class, "get_entity_list")):
                entities += vimar_entity_class(device_id, vimarconnection, vimarproject, coordinator).get_entity_list()
            else:
                entities.append(vimar_entity_class(device_id, vimarconnection, vimarproject, coordinator))

    if len(entities) != 0:
        _LOGGER.info("Adding %d %s", len(entities), discovery_info['hass_data_key'])
        async_add_entities(entities)
    # else:
    #     _LOGGER.warning("Vimar %s has no entities!", discovery_info['hass_data_key'])

    _LOGGER.debug("Vimar %s complete!", discovery_info['hass_data_key'])
