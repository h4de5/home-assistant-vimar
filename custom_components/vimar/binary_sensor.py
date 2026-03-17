"""Platform for binary_sensor integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPE_BINARY_SENSOR as CURR_PLATFORM, DOMAIN
from .vimar_coordinator import VimarDataUpdateCoordinator
from .vimar_entity import VimarEntity, vimar_setup_entry

_LOGGER = logging.getLogger(__name__)

# Keywords in zone names used to infer BinarySensorDeviceClass.
# Checked case-insensitively, first match wins.
_DEVICE_CLASS_HINTS: list[tuple[list[str], BinarySensorDeviceClass]] = [
    (["basculante", "garage", "garag"], BinarySensorDeviceClass.GARAGE_DOOR),
    (["porta", "portone", "ingresso"], BinarySensorDeviceClass.DOOR),
    (["portafin"], BinarySensorDeviceClass.DOOR),
    (["fin", "finestra", "fines"], BinarySensorDeviceClass.WINDOW),
    (["vol", "volumetr", "pir", "motion"], BinarySensorDeviceClass.MOTION),
    (["sirena", "manomis", "tamper"], BinarySensorDeviceClass.TAMPER),
]


def _guess_device_class(zone_name: str) -> BinarySensorDeviceClass | None:
    """Infer device class from zone name keywords."""
    name_lower = zone_name.lower()
    for keywords, device_class in _DEVICE_CLASS_HINTS:
        for kw in keywords:
            if kw in name_lower:
                return device_class
    return None


def _parse_sai2_zone_value(value: str) -> dict[str, bool]:
    """Decode SAI2 zone CURRENT_VALUE bitmask to state flags.

    Returns dict with boolean flags for each known state bit.
    Bit mapping (confirmed from diagnostic logs 2026-03-04):
        Bit 0: Aperta (zone physically open)  — value 1
        Bit 1: (reserved)
        Bit 2: Memoria (memory flag)           — value 4
        Bit 3: Allarme (alarm triggered)
        Bit 4: Manomessa (tampered)
        Bit 5: Mascherata (masked)
    """
    if not value:
        return {"open": False, "memory": False, "alarm": False, "tamper": False, "masked": False}
    try:
        bits = int(value, 2) if len(value) > 2 else int(value)
    except ValueError:
        return {"open": False, "memory": False, "alarm": False, "tamper": False, "masked": False}

    return {
        "open": bool(bits & (1 << 0)),
        "memory": bool(bits & (1 << 2)),
        "alarm": bool(bits & (1 << 3)),
        "tamper": bool(bits & (1 << 4)),
        "masked": bool(bits & (1 << 5)),
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vimar BinarySensor platform."""
    # Standard Vimar binary sensors (monostable switches)
    vimar_setup_entry(VimarBinarySensor, CURR_PLATFORM, hass, entry, async_add_entities)

    # SAI2 zone sensors (alarm physical sensors)
    coordinator: VimarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    vimarproject = coordinator.vimarproject

    if vimarproject is None or vimarproject.sai2_zones is None:
        _LOGGER.debug("SAI2: no alarm zones found, skipping zone binary sensors")
        return

    zone_to_group = vimarproject.sai2_zone_to_group or {}
    zone_entities: list[VimarSAI2ZoneSensor] = []
    for zone_id, zone_data in vimarproject.sai2_zones.items():
        parent_group_id = zone_to_group.get(zone_id)
        zone_entities.append(
            VimarSAI2ZoneSensor(
                coordinator, zone_id, zone_data, parent_group_id
            )
        )

    if zone_entities:
        _LOGGER.info(
            "Adding %d SAI2 zone binary_sensor entities", len(zone_entities)
        )
        async_add_entities(zone_entities)

    # Merge into devices_for_platform for cleanup tracking
    existing = coordinator.devices_for_platform.get(CURR_PLATFORM, [])
    if isinstance(existing, list):
        existing.extend(zone_entities)
    else:
        coordinator.devices_for_platform[CURR_PLATFORM] = zone_entities


class VimarBinarySensor(VimarEntity, BinarySensorEntity):
    """Provide Vimar BinarySensor."""

    def __init__(self, coordinator, device_id: int):
        """Initialize the binary sensor."""
        VimarEntity.__init__(self, coordinator, device_id)

    @property
    def entity_platform(self) -> str:
        return CURR_PLATFORM

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is on."""
        if self.has_state("on/off"):
            return self.get_state("on/off") == "1"
        return None


class VimarSAI2ZoneSensor(
    CoordinatorEntity[VimarDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Vimar SAI2 alarm zone as a binary sensor.

    Each zone corresponds to a physical sensor (door contact, motion
    detector, siren tamper, etc.) connected to the SAI2 alarm system.
    The entity reports is_on=True when the zone is physically "open"
    (e.g. door open, motion detected).
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VimarDataUpdateCoordinator,
        zone_id: str,
        zone_data: dict[str, Any],
        parent_group_id: str | None = None,
    ) -> None:
        """Initialize the SAI2 zone sensor."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data
        self._parent_group_id = parent_group_id
        zone_name = zone_data.get("name", f"Zone {zone_id}")

        # Resolve parent area name for labelling
        self._area_name: str | None = None
        if parent_group_id:
            project = coordinator.vimarproject
            if project and project.sai2_groups:
                group = project.sai2_groups.get(parent_group_id)
                if group:
                    self._area_name = group.get("name")

        # Prefix entity name with area for visual grouping
        if self._area_name:
            self._attr_name = f"{self._area_name} - {zone_name}"
        else:
            self._attr_name = zone_name

        self._attr_unique_id = f"vimar_sai2_zone_{zone_id}"
        self._attr_device_class = _guess_device_class(zone_name)
        self._last_logged_bits: int = -1

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.vimarproject is not None
            and self.coordinator.vimarproject.sai2_zones is not None
            and self._zone_id in self.coordinator.vimarproject.sai2_zones
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if zone is open/triggered.

        The SAI2 gateway updates the zone parent object's CURRENT_VALUE
        bitmask in real-time, but does NOT update individual children.
        We read from sai2_zone_values (parent bitmask) as primary source.

        Bit 0 = Aperta (confirmed: garage open = 00000001, bit0=1).
        """
        project = self.coordinator.vimarproject
        if project is None:
            return None

        # Primary: live bitmask from zone parent DPADD_OBJECT
        zone_values = getattr(project, "sai2_zone_values", None)
        if zone_values is not None and self._zone_id in zone_values:
            raw = zone_values[self._zone_id]
            try:
                bits = int(raw, 2) if len(raw) > 2 else int(raw)
            except (ValueError, TypeError):
                bits = 0
            if bits != self._last_logged_bits:
                _LOGGER.debug(
                    "SAI2 ZONE %s (%s): raw='%s' bits=%d",
                    self._zone_id,
                    self._zone_data.get("name", "?"),
                    raw, bits,
                )
                self._last_logged_bits = bits
            # Bit 0 = Aperta (zone physically open)
            return bool(bits & 1)

        # Fallback: children dict (may be stale)
        if project.sai2_zones is None:
            return None
        zone = project.sai2_zones.get(self._zone_id)
        if zone is None:
            return None
        children = zone.get("children", {})
        for label in ("Aperta", "Aperto", "Open"):
            child = children.get(label)
            if child is not None:
                return child.get("value") == "1"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for diagnostics."""
        project = self.coordinator.vimarproject
        attrs: dict[str, Any] = {"zone_id": self._zone_id}

        if self._area_name:
            attrs["area_name"] = self._area_name

        # Decoded bitmask flags (live)
        zone_values = getattr(project, "sai2_zone_values", None)
        if zone_values is not None and self._zone_id in zone_values:
            raw = zone_values[self._zone_id]
            attrs["raw_bitmask"] = raw
            flags = _parse_sai2_zone_value(raw)
            attrs.update(flags)

        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info — all zones share the single SAI Alarm device."""
        return DeviceInfo(
            identifiers={(DOMAIN, "sai2_alarm")},
        )

