"""Insteon base entity."""
import logging

# from homeassistant.core import callback
# from homeassistant.util import Throttle
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.entity import Entity
from .vimarlink import (VimarLink, VimarProject)
from .const import DOMAIN
# from . import format_name

_LOGGER = logging.getLogger(__name__)

# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)

# DONE central updater
# see: https://developers.home-assistant.io/docs/integration_fetching_data/


# @asyncio.coroutine


class VimarEntity(Entity):
    """Vimar abstract base entity."""

    # _name = ''
    _device = []
    _device_id = 0
    _vimarconnection = None
    _vimarproject = None
    _coordinator = None
    _attributes = {}
    # entity_id = "light.not-set"

    ICON = "mdi:checkbox-marked"

    def __init__(self, device_id: int, vimarconnection: VimarLink, vimarproject: VimarProject, coordinator):
        """Initialize the base entity."""
        self._coordinator = coordinator
        # self.idx = idx
        # self._device = device
        # self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        # self._state = False
        self._vimarconnection = vimarconnection
        self._vimarproject = vimarproject
        # self._attributes.append()
        self._reset_status()

        if self._device_id in self._vimarproject.devices:
            self._device = self._vimarproject.devices[self._device_id]
        else:
            _LOGGER.warning("Cannot find device #%s", self._device_id)

        # self.entity_id = self._platform + "." + self.name.lower().replace(" ", "_") + "_" + self._device_id

        # _LOGGER.debug('Initializing new entity: %s', self.entity_id)
        # self.async_schedule_update_ha_state()

    # @property
    # def should_poll(self):
    #     """ polling is needed for a Vimar device. """
    #     return True

    # @property
    # def available(self):
    #     """Return True if entity is available."""
    #     return True

    # async def async_added_to_hass(self):
    #     return 0

    # async def async_will_remove_from_hass(self):
    #     return 0

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

    # see: https://github.com/home-assistant/core/blob/11b786a4fc39d3a31c8ab27045d88c9a437003b5/homeassistant/components/gogogate2/cover.py
    # @callback
    # def async_on_data_updated(self) -> None:
    #     """Receive data from data dispatcher."""
    #     if not self._coordinator.last_update_success:
    #         self.async_write_ha_state()
    #         return

    #     if self._device_id in self._vimarproject.devices:
    #         self._device = self._vimarproject.devices[self._device_id]
    #     else:
    #         _LOGGER.warning("Cannot re-add device #%s", self._device_id)

    #     self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
        return self._device['object_name']

    # @property
    # def state(self):
    #     """Return the states of the device."""
    #     return self._device['status']

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
                        self._device['status'][state]['status_value'] = value
                        optionals = self._vimarconnection.get_optionals_param(state)
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status'][state]['status_id'], value, optionals)
                    else:
                        _LOGGER.warning("Could not find state %s in device %s - %s - could not change value to: %s", state, self._name, self._device_id, value)

            if kwargs and len(kwargs) > 0:
                for state, value in kwargs.items():
                    if state in self._device['status']:
                        state_changed = True
                        self._device['status'][state]['status_value'] = value
                        optionals = self._vimarconnection.get_optionals_param(state)
                        self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status'][state]['status_id'], value, optionals)
                    else:
                        _LOGGER.warning("Could not find state %s in device %s - %s - could not change value to: %s", state, self._name, self._device_id, value)

            if state_changed:
                self.request_statemachine_update()

        # await asyncio.gather(
        # if 'status' in self._device and self._device['status'] and state in self._device['status']:
        #     self._device['status'][state]['status_value'] = value
        #     await self.hass.async_add_executor_job(self._vimarconnection.set_device_status, self._device['status'][state]['status_id'], value)
        # else:
        #     _LOGGER.warning("Could not find state %s in device %s - could not change value to: %s", state, self._device_id, value)

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

    # def update(self):
    # see:
    # https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    # @Throttle(MIN_TIME_BETWEEN_UPDATES)
    # async def async_update(self):
    #     """DEPRECATED Fetch new state data for this entity.

    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     # starttime = localtime()
    #     # strftime("%Y-%m-%d %H:%M:%S",
    #     # self._light.update()

    #     _LOGGER.debug("updated method called for %d", self._device_id)

    #     old_status = self._device['status']

    #     if False and self.should_poll:
    #         self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)

    #     else:
    #         # _LOGGER.debug("updated whole data: %s ", str(self._coordinator.data))
    #         # await self._coordinator.async_request_refresh()
    #         # DONE : von get_scenes kommt was ganz anders zurück als von get_device_status ..
    #         # wahrscheinlich geht deswegen auch der initiale status nicht
    #         if self._device_id in self._coordinator.data:
    #             self._device['status'] = self._coordinator.data[self._device_id]['status']
    #             # _LOGGER.debug("updated new status: %s ", str(self._device['status']))
    #         # else:
    #             # _LOGGER.debug("could not find device_id in coordinator data: %s ", str(self._coordinator.data))

    #     self._reset_status()
    #     if old_status != self._device['status']:
    #         self.async_schedule_update_ha_state()

    #     # _LOGGER.debug("Vimar Light update finished after " +
    #     # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if isinstance(self._device['icon'], str):
            return self._device['icon']
        elif isinstance(self._device['icon'], list):
            # _LOGGER.debug('default state for %s is %s - icon: %s', str(self.entity_id), str(self.is_default_state), str(self._device['icon']))
            # return self._device['icon'][0]
            # TypeError: tuple indices must be integers or slices, not str
            return (self._device['icon'][1], self._device['icon'][0])[self.is_default_state]

        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device['device_class']

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return DOMAIN + '_' + self._device_id

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

    # devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    devices = vimarproject.get_by_device_type(discovery_info['hass_data_key'])

    if len(devices) != 0:
        # _LOGGER.debug("Vimar found %d %s devices!", len(devices), discovery_info['hass_data_key'])
        for device_id, device in devices.items():
            if hasattr(vimar_entity_class, "get_entity_list") and callable(getattr(vimar_entity_class, "get_entity_list")):
                # tmpinst = VimarEntityClass(device, device_id, vimarconnection)
                # tmplist = tmpinst.get_entity_list()
                # entities += tmplist
                # _LOGGER.debug("Vimar %s has get_entity_list!", discovery_info['hass_data_key'])

                entities += vimar_entity_class(device_id, vimarconnection, vimarproject, coordinator).get_entity_list()
            else:
                entities.append(vimar_entity_class(device_id, vimarconnection, vimarproject, coordinator))

    if len(entities) != 0:
        _LOGGER.info("Adding %d %s", len(entities), discovery_info['hass_data_key'])

        # if discovery_info['hass_data_key'] == 'sensors':
        #     for entity in entities:
        #         _LOGGER.info("entity_list final: %s - #%s", entity.name, entity.unique_id)

        # import json
        # _LOGGER.info("entity list: %s", json.dumps(entities, indent=4))
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        # async_add_entities(entities, True)
        async_add_entities(entities)
    # else:
        # _LOGGER.debug("Vimar %s has no entities!", discovery_info['hass_data_key'])

    _LOGGER.debug("Vimar %s complete!", discovery_info['hass_data_key'])
