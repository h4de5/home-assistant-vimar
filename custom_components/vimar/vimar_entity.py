"""Insteon base entity."""

import logging
from typing import Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_IGNORE_PLATFORM,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
    PACKAGE_NAME,
    _LOGGER,
)
from .vimar_coordinator import VimarDataUpdateCoordinator
from .vimarlink.vimarlink import VimarDevice, VimarLink, VimarProject


class VimarEntity(CoordinatorEntity):
    """Vimar abstract base entity."""

    _logger = _LOGGER
    _logger_is_debug = False
    _device: VimarDevice | None = None
    _device_id = 0
    _vimarconnection: VimarLink | None = None
    _vimarproject: VimarProject | None = None
    _coordinator: VimarDataUpdateCoordinator | None = None
    _attributes = {}

    ICON = "mdi:checkbox-marked"

    def __init__(self, coordinator: VimarDataUpdateCoordinator, device_id: int):
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._device_id = device_id
        self._vimarconnection = coordinator.vimarconnection
        self._vimarproject = coordinator.vimarproject
        self._reset_status()

        if self._vimarproject is not None and self._device_id in self._vimarproject.devices:
            self._device = self._vimarproject.devices[self._device_id]
            self._logger = logging.getLogger(PACKAGE_NAME + "." + self.entity_platform)
            self._logger_is_debug = self._logger.isEnabledFor(logging.DEBUG)
        else:
            self._logger.warning("Cannot find device #%s", self._device_id)

        # self.entity_id = self._platform + "." + self.name.lower().replace(" ", "_") + "_" + self._device_id

    @property
    def device_name(self):
        """Return the name of the device."""
        name = self._device["device_friendly_name"]
        if name is None:
            name = self._device["object_name"]
        return name

    @property
    def name(self):
        """Return the name of the device."""
        return self.device_name

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        # see: https://developers.home-assistant.io/docs/dev_101_states/
        # mostro gli attributi importati da vimar
        if self._device is not None:
            for key in self._device:
                value = self._device[key]
                if self._logger_is_debug is False and (
                    key == "status"
                    or key == "device_class"
                    or key == "device_friendly_name"
                    or key == "vimar_icon"
                ):
                    # for status_name in value:
                    #    deviceItem["state_" + status_name.replace("/", "_").replace(" ", "_")] = value[status_name]["status_value"]
                    continue
                self._attributes["vimar_" + key] = value
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
        if "status" in self._device and self._device["status"]:

            if args and len(args) > 0:
                iter_args = iter(args)
                for state, value in zip(iter_args, iter_args):
                    if state in self._device["status"]:
                        state_changed = True
                        optionals = self._vimarconnection.get_optionals_param(state)
                        self.hass.async_add_executor_job(
                            self._vimarconnection.set_device_status,
                            self._device["status"][state]["status_id"],
                            str(value),
                            optionals,
                        )
                        self._device["status"][state]["status_value"] = str(value)
                    else:
                        self._logger.warning(
                            "Could not find state %s in device %s - %s - could not change value to: %s",
                            state,
                            self.name,
                            self._device_id,
                            value,
                        )

            if kwargs and len(kwargs) > 0:
                for state, value in kwargs.items():
                    if state in self._device["status"]:
                        state_changed = True
                        optionals = self._vimarconnection.get_optionals_param(state)
                        self.hass.async_add_executor_job(
                            self._vimarconnection.set_device_status,
                            self._device["status"][state]["status_id"],
                            str(value),
                            optionals,
                        )
                        self._device["status"][state]["status_value"] = str(value)
                    else:
                        self._logger.warning(
                            "Could not find state %s in device %s - %s - could not change value to: %s",
                            state,
                            self.name,
                            self._device_id,
                            value,
                        )

            if state_changed:
                self.request_statemachine_update()

        # TODO - call async_add_executor_job with asyncio.gather maybe?

    def get_state(self, state):
        """Get state of the local device state."""
        if self.has_state(state):
            return self._device["status"][state]["status_value"]
        else:
            self._logger.warning(
                "Could not find state %s in device %s - %s - could not get value",
                state,
                self.name,
                self._device_id,
            )
        return None

    def has_state(self, state):
        """Return true if local device has a given state."""
        if (
            "status" in self._device
            and self._device["status"]
            and state in self._device["status"]
        ):
            return True
        else:
            return False

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if isinstance(self._device["icon"], str):
            return self._device["icon"]
        elif isinstance(self._device["icon"], list):
            return (self._device["icon"][1], self._device["icon"][0])[
                self.is_default_state
            ]

        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device["device_class"]

    @property
    def unique_id(self):
        """Return the ID of this device."""
        # self._logger.debug("Unique Id: " + DOMAIN + '_' + self._platform + '_' + self._device_id + " - " + self.name)
        prefix = self._coordinator.entity_unique_id_prefix or ""
        if len(prefix) > 0:
            prefix += "_"
        return DOMAIN + "_" + prefix + self.entity_platform + "_" + self._device_id

    def _reset_status(self):
        """Set status from _device to class variables."""

    @property
    def is_default_state(self):
        """Return True of in default state - resulting in default icon."""
        return False

    @property
    def device_info(self) -> DeviceInfo | None:
        room_name = None
        if (
            self._device.get("room_friendly_name")
            and self._device["room_friendly_name"] != ""
        ):
            room_name = self._device["room_friendly_name"]

        device : DeviceInfo = {
            "identifiers": {
                (
                    DOMAIN,
                    self._coordinator.entity_unique_id_prefix or "",
                    self._device_id,
                )
            },
            "name": self.device_name,
            "model": self._device.get("object_type"),
            "manufacturer": "Vimar",
            "suggested_area": room_name,
        }
        return device

    @property
    def entity_platform(self):
        """Return device_type (platform overrrided in sensor class)"""
        return self._device["device_type"]

    def get_entity_list(self) -> list:
        """return entity as list for async_add_devices, method to override if has multiple attribute, as sensor"""
        return [self]


class VimarStatusSensor(BinarySensorEntity):
    """Representation of a Sensor."""

    _coordinator: VimarDataUpdateCoordinator = None

    def __init__(self, coordinator: VimarDataUpdateCoordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator
        vimarconfig = coordinator.vimarconfig
        self._name = (
            "Vimar Connection to "
            + str(coordinator.vimarconnection._host)
            + ":"
            + str(coordinator.vimarconnection._port)
        )
        self._type: BinarySensorDeviceClass = "connectivity"
        self._attributes = {
            "Host": coordinator.vimarconnection._host,
            "Port": coordinator.vimarconnection._port,
            "Secure": coordinator.vimarconnection._schema == "https",
            "Verify SSL": coordinator.vimarconnection._schema == "https"
            and vimarconfig.get(CONF_VERIFY_SSL),
            "Vimar Url": "%s://%s:%s"
            % (
                coordinator.vimarconnection._schema,
                coordinator.vimarconnection._host,
                coordinator.vimarconnection._port,
            ),
            "Certificate": coordinator.vimarconnection._certificate,
            "Username": coordinator.vimarconnection._username,
            "SessionID": coordinator.vimarconnection._session_id,
        }
        self._data = self._attributes
        self._state = False

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._type

    @property
    def should_poll(self):
        """Polling needed for a demo binary sensor."""
        return True

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the ID of this device."""
        # self._logger.debug("Unique Id: " + DOMAIN + '_' + self._platform + '_' + self._device_id + " - " + self.name)
        prefix = self._coordinator.entity_unique_id_prefix or ""
        if len(prefix) > 0:
            prefix += "_"
        return DOMAIN + "_" + prefix + "status"

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        if self._data:
            return self._data
        else:
            return None

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._coordinator.entity_unique_id_prefix or "", "status")
            },
            "name": "Vimar WebServer",
            "model": "Vimar WebServer",
            "manufacturer": "Vimar",
        }

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        # self._data = self._fetch(self._host)
        logged = self._coordinator.vimarconnection.is_logged()
        if logged:
            self._state = True
        else:
            self._state = False


def vimar_setup_entry(
    vimar_entity_class: VimarEntity,
    platform,
    hass: HomeAssistant,
    entry,
    async_add_devices,
):
    """Generic method for add entities of specified platform to HASS"""
    logger = logging.getLogger(PACKAGE_NAME + "." + platform)
    coordinator: VimarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    ignored_platforms = coordinator.vimarconfig.get(CONF_IGNORE_PLATFORM) or []
    platform_ignored = platform in ignored_platforms
    vimarproject = coordinator.vimarproject

    entities = []
    entities_to_add = []

    if platform == DEVICE_TYPE_BINARY_SENSOR:
        status_sensor = VimarStatusSensor(coordinator)
        async_add_devices([status_sensor], True)
        entities += [status_sensor]

    if not platform_ignored:
        logger.debug("Vimar %s started!", platform)
        devices = vimarproject.get_by_device_type(platform)
        if len(devices) != 0:
            for device_id, device in devices.items():
                if device.get("ignored", False):
                    continue
                entity: VimarEntity = vimar_entity_class(coordinator, device_id)
                entity_list = entity.get_entity_list()
                entities_to_add += entity_list

    if len(entities_to_add) != 0:
        logger.info("Adding %d %s", len(entities_to_add), platform)
    # need to call async_add_devices everytime for each registered platform (even if it's empty)! if not called, entry reload not work.
    async_add_devices(entities_to_add)
    entities += entities_to_add

    coordinator.devices_for_platform[platform] = entities

    if not platform_ignored:
        logger.debug("Vimar %s complete!", platform)
