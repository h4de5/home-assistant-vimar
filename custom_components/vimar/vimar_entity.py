"""Vimar base entity implementation."""

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    _LOGGER,
    CONF_IGNORE_PLATFORM,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
    PACKAGE_NAME,
)
from .vimar_coordinator import VimarDataUpdateCoordinator
from .vimarlink.vimarlink import VimarDevice, VimarLink, VimarProject


class VimarEntity(CoordinatorEntity[VimarDataUpdateCoordinator]):
    """Vimar abstract base entity.

    Implements proper availability handling according to Home Assistant standards:
    - Entity is unavailable when coordinator update fails
    - Entity is unavailable when device data is missing from coordinator
    - Entity is available when device data is present and valid
    """

    _logger = _LOGGER
    _logger_is_debug = False
    _device: VimarDevice | None = None
    _device_id: str = "0"
    _vimarconnection: VimarLink | None = None
    _vimarproject: VimarProject | None = None
    _coordinator: VimarDataUpdateCoordinator | None = None

    ICON = "mdi:checkbox-marked"

    def __init__(self, coordinator: VimarDataUpdateCoordinator, device_id: int):
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._device_id = str(device_id)
        self._vimarconnection = coordinator.vimarconnection
        self._vimarproject = coordinator.vimarproject
        # _attributes must be instance-level, not class-level.
        self._attributes: dict = {}
        self._reset_status()

        if self._vimarproject is not None and self._device_id in self._vimarproject.devices:
            self._device = self._vimarproject.devices[self._device_id]
            self._logger = logging.getLogger(str(PACKAGE_NAME) + "." + self.entity_platform)
            self._logger_is_debug = self._logger.isEnabledFor(logging.DEBUG)
        else:
            self._logger.warning("Cannot find device #%s", self._device_id)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        FIX #23: il log per entity (updated/skipped) e' stato spostato
        interamente nel coordinator (_log_poll_summary), che emette due
        sole righe DEBUG per ciclo. Qui si filtra solo l'aggiornamento
        effettivo dell'entity senza produrre log.
        """
        if self._device_id in self.coordinator._changed_device_ids:
            super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Entity is considered available when:
        1. Coordinator update is successful (super().available)
        2. Device data exists in coordinator
        3. Device has not been removed

        This ensures entities correctly show 'unavailable' state when:
        - Vimar web server is offline
        - Authentication fails
        - Network connectivity is lost
        - Device is removed from Vimar configuration
        """
        if not super().available:
            return False

        if self.coordinator.data is None:
            return False

        if self._device_id not in self.coordinator.data:
            return False

        return True

    @property
    def device_name(self):
        """Return the name of the device."""
        if self._device is None:
            return f"Unknown Device {self._device_id}"
        name = self._device.get("device_friendly_name")
        if name is None:
            name = self._device.get("object_name", f"Device {self._device_id}")
        return name

    @property
    def name(self):
        """Return the name of the device."""
        return self.device_name

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes.

        FIX #8: build and return a fresh dict each time instead of mutating
        self._attributes in place.
        """
        if self._device is None:
            return {}

        attrs: dict = {}
        for key in self._device:
            value = self._device[key]
            if self._logger_is_debug is False and key in (
                "status",
                "device_class",
                "device_friendly_name",
                "vimar_icon",
            ):
                continue
            attrs["vimar_" + key] = value
        return attrs

    def request_statemachine_update(self):
        """Push local state change to HA UI immediately.

        FIX #22: bypassa il filtro _changed_device_ids di
        _handle_coordinator_update aggiungendo esplicitamente il device_id
        al set del coordinator, poi chiama async_write_ha_state() che
        legge direttamente le property dell'entity (cache locale gia'
        aggiornata da _apply_state_change) senza refetch dal webserver.

        FIX #24: invalida l'hash del device nel coordinator.
        Senza questa invalidazione, se il webserver risponde con lo stesso
        valore gia' presente in cache prima dell'azione ottimistica
        (es. device monostabile che torna a 0 per la seconda volta
        consecutiva), _detect_state_changes trova hash identico e non
        aggiunge il device_id a _changed_device_ids -> la UI resta
        desincronizzata.
        Con il .pop() l'hash viene cancellato: al ciclo successivo
        old_hash e' None -> il device e' sempre considerato changed ->
        la UI si risincronizza con il valore reale del webserver.
        Vale per tutti i device, non solo i monostabili: termostati che
        arrotondano il setpoint, tapparelle che non si muovono, ecc.
        """
        if self._coordinator is not None:
            self._coordinator._changed_device_ids.add(self._device_id)
            # FIX #24: forza rilettura hash al prossimo poll
            self._coordinator._device_state_hashes.pop(self._device_id, None)
        self.async_write_ha_state()

    def _apply_state_change(self, state: str, value) -> bool:
        """Apply a single state change to the device and schedule a bus write.

        FIX #9: extracted from change_state() to remove duplicate logic.
        Returns True if the state was found and the write was scheduled.
        """
        if state not in self._device["status"]:
            self._logger.warning(
                "Could not find state %s in device %s - %s - could not change value to: %s",
                state,
                self.name,
                self._device_id,
                value,
            )
            return False

        optionals = self._vimarconnection.get_optionals_param(state)
        self.hass.async_add_executor_job(
            self._vimarconnection.set_device_status,
            self._device["status"][state]["status_id"],
            str(value),
            optionals,
        )
        self._device["status"][state]["status_value"] = str(value)
        return True

    def change_state(self, *args, **kwargs):
        """Change state on bus system and the local device state."""
        if self._device is None or "status" not in self._device:
            self._logger.warning(
                "Cannot change state for device %s - device data not available",
                self._device_id
            )
            return

        state_changed = False

        if self._device["status"]:
            if args:
                iter_args = iter(args)
                for state, value in zip(iter_args, iter_args, strict=False):
                    if self._apply_state_change(state, value):
                        state_changed = True

            for state, value in kwargs.items():
                if self._apply_state_change(state, value):
                    state_changed = True

        if state_changed:
            self.request_statemachine_update()

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
        if self._device is None:
            return False
        if "status" in self._device and self._device["status"] and state in self._device["status"]:
            return True
        return False

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._device is None:
            return self.ICON

        device_icon = self._device.get("icon")
        if isinstance(device_icon, str):
            return device_icon
        elif isinstance(device_icon, list):
            return (device_icon[1], device_icon[0])[self.is_default_state]

        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        if self._device is None:
            return None
        return self._device.get("device_class")

    @property
    def unique_id(self):
        """Return the ID of this device."""
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
        """Return device information for device registry."""
        if self._device is None:
            return None

        room_name = None
        if self._device.get("room_friendly_name") and self._device["room_friendly_name"] != "":
            room_name = self._device["room_friendly_name"]

        device: DeviceInfo = {
            "identifiers": {
                (
                    DOMAIN,
                    self._coordinator.entity_unique_id_prefix or "",
                    self._device_id,
                )
            },  # type: ignore[arg-type]
            "name": self.device_name,
            "model": self._device.get("object_type"),
            "manufacturer": "Vimar",
            "suggested_area": room_name,
        }
        return device

    @property
    def entity_platform(self):
        """Return device_type (platform overrrided in sensor class)"""
        if self._device is None:
            return "unknown"
        return self._device.get("device_type", "unknown")

    def get_entity_list(self) -> list:
        """return entity as list for async_add_devices, method to override if has multiple attribute, as sensor"""
        return [self]


class VimarStatusSensor(BinarySensorEntity):
    """Representation of Vimar connection status sensor."""

    _coordinator: VimarDataUpdateCoordinator
    _attr_should_poll = True

    def __init__(self, coordinator: VimarDataUpdateCoordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator
        vimarconfig = coordinator.vimarconfig
        conn = coordinator.vimarconnection._connection
        self._attr_name = (
            "Vimar Connection to "
            + str(conn._host)
            + ":"
            + str(conn._port)
        )
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_extra_state_attributes = {
            "Host": conn._host,
            "Port": conn._port,
            "Secure": conn._schema == "https",
            "Verify SSL": conn._schema == "https" and vimarconfig.get(CONF_VERIFY_SSL),
            "Vimar Url": f"{conn._schema}://{conn._host}:{conn._port}",
            "Certificate": conn._certificate,
            "Username": conn._username,
            "SessionID": coordinator.vimarconnection._session_id,
        }
        self._attr_is_on = False

    @property
    def unique_id(self):
        """Return the ID of this device."""
        prefix = self._coordinator.entity_unique_id_prefix or ""
        if len(prefix) > 0:
            prefix += "_"
        return DOMAIN + "_" + prefix + "status"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.entity_unique_id_prefix or "", "status")},  # type: ignore[arg-type]
            name="Vimar WebServer",
            model="Vimar WebServer",
            manufacturer="Vimar",
        )

    def update(self):
        """Fetch new state data for the sensor.

        FIX #10: this method is called by HA on the executor thread
        (because _attr_should_poll = True and update() is synchronous),
        so the blocking is_logged() network call is safe here.
        """
        self._attr_is_on = self._coordinator.vimarconnection.is_logged()


def vimar_setup_entry(
    vimar_entity_class: type[VimarEntity],
    platform: str,
    hass: HomeAssistant,
    entry,
    async_add_devices,
):
    """Generic method for add entities of specified platform to HASS."""
    logger = logging.getLogger(str(PACKAGE_NAME) + "." + platform)
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
    async_add_devices(entities_to_add)
    entities += entities_to_add

    coordinator.devices_for_platform[platform] = entities

    if not platform_ignored:
        logger.debug("Vimar %s complete!", platform)
