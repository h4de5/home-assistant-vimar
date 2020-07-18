"""Insteon base entity."""
import logging

# from homeassistant.core import callback
# from homeassistant.util import Throttle
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from . import format_name

_LOGGER = logging.getLogger(__name__)

# MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)

# DONE central updater
# see: https://developers.home-assistant.io/docs/integration_fetching_data/


# @asyncio.coroutine

class VimarEntity(Entity):
    """Vimar abstract base entity."""

    _name = ''
    _device = []
    _device_id = 0
    _vimarconnection = None
    _coordinator = None
    _attributes = {}

    ICON = "mdi:checkbox-marked"

    def __init__(self, device, device_id, vimarconnection, coordinator):
        """Initialize the base entity."""
        self._coordinator = coordinator
        # self.idx = idx
        self._device = device
        self._name = format_name(self._device['object_name'])
        self._device_id = device_id
        self._state = False
        self._vimarconnection = vimarconnection
        # self._attributes.append()
        self._reset_status()

        self.entity_id = self._platform + "." + self._name.lower() + "_" + self._device_id
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
        return True

    @ property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(
                self.async_write_ha_state
            )
        )

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        # see: https://developers.home-assistant.io/docs/dev_101_states/
        return self._attributes

    def request_status_update(self):
        """Update the hass status."""
        # with polling, we need to schedule another poll request
        self.async_schedule_update_ha_state()

        # if not self.should_poll:
        #     # with the central update coordinator, we do this
        #     self._coordinator.async_request_refresh()

    # def update(self):
    # see:
    # https://github.com/samueldumont/home-assistant/blob/added_vaillant/homeassistant/components/climate/vaillant.py
    # @Throttle(MIN_TIME_BETWEEN_UPDATES)

    async def async_update(self):
        """Fetch new state data for this entity.

        This is the only method that should fetch new data for Home Assistant.
        """
        # starttime = localtime()
        # strftime("%Y-%m-%d %H:%M:%S",
        # self._light.update()

        _LOGGER.debug("updated methode called for %d", self._device_id)

        old_status = self._device['status']

        if False and self.should_poll:
            self._device['status'] = await self.hass.async_add_executor_job(self._vimarconnection.get_device_status, self._device_id)

        else:
            # _LOGGER.debug("updated whole data: %s ", str(self._coordinator.data))
            # await self._coordinator.async_request_refresh()
            # DONE : von get_scenes kommt was ganz anders zurück als von get_device_status ..
            # wahrscheinlich geht deswegen auch der initiale status nicht
            if self._device_id in self._coordinator.data:
                self._device['status'] = self._coordinator.data[self._device_id]['status']
                # _LOGGER.debug("updated new status: %s ", str(self._device['status']))
            # else:
                # _LOGGER.debug("could not find device_id in coordinator data: %s ", str(self._coordinator.data))

        self._reset_status()
        if old_status != self._device['status']:
            self.async_schedule_update_ha_state()

        # _LOGGER.debug("Vimar Light update finished after " +
        # str(mktime(localtime()) - mktime(starttime)) + "s " + self._name)

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
        return self._device_id

    def _reset_status(self):
        """Set status from _device to class variables."""

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return self._state


def vimar_setup_platform(vimar_entity_class: VimarEntity, hass: HomeAssistantType, async_add_entities, discovery_info=None):
    """Set up the Vimar Sensor platform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    _LOGGER.debug("Vimar %s started!", discovery_info['hass_data_key'])
    entities = []

    vimarconnection = hass.data[DOMAIN]['connection']
    coordinator = hass.data[DOMAIN]['coordinator']
    devices = hass.data[DOMAIN][discovery_info['hass_data_key']]

    if len(devices) != 0:
        for device_id, device in devices.items():
            if hasattr(vimar_entity_class, "get_entity_list") and callable(getattr(vimar_entity_class, "get_entity_list")):
                # tmpinst = VimarEntityClass(device, device_id, vimarconnection)
                # tmplist = tmpinst.get_entity_list()
                # entities += tmplist
                entities += vimar_entity_class(device, device_id, vimarconnection, coordinator).get_entity_list()
            else:
                entities.append(vimar_entity_class(device, device_id, vimarconnection, coordinator))

    if len(entities) != 0:

        _LOGGER.info("Adding %d %s", len(entities), discovery_info['hass_data_key'])

        # if discovery_info['hass_data_key'] == 'sensors':
        #     for entity in entities:
        #         _LOGGER.info("entity_list final: %s", entity.entity_id)

        # import json
        # _LOGGER.info("entity list: %s", json.dumps(entities, indent=4))
        # If your entities need to fetch data before being written to Home
        # Assistant for the first time, pass True to the add_entities method:
        # add_entities([MyEntity()], True).
        # async_add_entities(entities, True)
        async_add_entities(entities)

    _LOGGER.debug("Vimar %s complete!", discovery_info['hass_data_key'])
