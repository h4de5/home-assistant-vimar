"""Platform for Vimar SAI2 alarm control panel integration."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SAI_PIN, DEVICE_TYPE_ALARM as CURR_PLATFORM, DOMAIN
from .vimar_coordinator import VimarDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Maps SAI2 child state labels to HA alarm states.
# Priority order: Allarme is checked first, then the armed/disarmed states.
SAI2_STATE_MAP = {
    "Disinserito": AlarmControlPanelState.DISARMED,
    "Inserito INT": AlarmControlPanelState.ARMED_HOME,
    "Inserito ON": AlarmControlPanelState.ARMED_AWAY,
    "Inserito PAR": AlarmControlPanelState.ARMED_NIGHT,
    "Allarme": AlarmControlPanelState.TRIGGERED,
}

# SAI2 SOAP command codes for service-vimarsai2allgroupsset
SAI2_CMD_OFF = 0   # Disarm
SAI2_CMD_ON = 1    # Arm away (all sensors)
SAI2_CMD_INT = 2   # Arm home (internal sensors only)
SAI2_CMD_PAR = 3   # Arm night (partial)


def _parse_sai2_area_value(value: str) -> str:
    """Map SAI2 group CURRENT_VALUE bitmask from DPADD_OBJECT to state label.

    The SAI2 group object in DPADD_OBJECT stores its live state as an
    8-character binary bitmask (e.g. '00001001'). Confirmed bit mapping
    from browser inspection + live testing:

        Bit 5 (0b00100000): Allarme
        Bit 3 (0b00001000): Inserito PAR  <- confirmed '00001001'
        Bit 2 (0b00000100): Inserito INT  <- confirmed by user test
        Bit 1 (0b00000010): Inserito ON   <- confirmed by user test
        Bit 0 (0b00000001): armed-active flag (set whenever any mode is active)
        All zeros           Disinserito
    """
    if not value or all(c == "0" for c in value):
        return "Disinserito"
    try:
        bits = int(value, 2)
    except ValueError:
        _LOGGER.warning("SAI2: unrecognised CURRENT_VALUE format: '%s'", value)
        return "Disinserito"

    if bits & (1 << 5):
        return "Allarme"
    if bits & (1 << 3):
        return "Inserito PAR"
    if bits & (1 << 2):
        return "Inserito INT"
    if bits & (1 << 1):
        return "Inserito ON"
    # Bit 0 alone = armed but mode not decoded
    _LOGGER.warning("SAI2: armed state with unhandled bitmask '%s', assuming ARMED_AWAY", value)
    return "Inserito ON"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vimar Alarm Control Panel platform."""
    coordinator: VimarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    vimarproject = coordinator.vimarproject

    if vimarproject is None or vimarproject.sai2_groups is None:
        _LOGGER.debug("SAI2: no alarm areas found, skipping alarm platform")
        return

    # Register the single SAI Alarm device.
    # All alarm and zone entities will be nested under this device.
    sai_device_info: dict[str, Any] = {
        "identifiers": {(DOMAIN, "sai2_alarm")},
        "name": "SAI Alarm",
        "manufacturer": "Vimar",
        "model": "SAI2",
    }
    if coordinator.webserver_id:
        sai_device_info["via_device"] = (DOMAIN, coordinator.webserver_id)
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(config_entry_id=entry.entry_id, **sai_device_info)

    sai_pin = entry.data.get(CONF_SAI_PIN, "") or entry.options.get(CONF_SAI_PIN, "")
    if not sai_pin:
        _LOGGER.warning(
            "SAI2: no alarm PIN configured - alarm entities will be read-only. "
            "Set the SAI PIN in the integration options to enable arming/disarming."
        )

    entities: list[VimarAlarmControlPanel] = []
    for area_index, (group_id, group_data) in enumerate(
        vimarproject.sai2_groups.items(), start=1
    ):
        entities.append(
            VimarAlarmControlPanel(
                coordinator, group_id, group_data, area_index, sai_pin
            )
        )

    if entities:
        _LOGGER.info("Adding %d alarm_control_panel entities", len(entities))
        async_add_entities(entities)

    coordinator.devices_for_platform[CURR_PLATFORM] = entities


class VimarAlarmControlPanel(
    CoordinatorEntity[VimarDataUpdateCoordinator], AlarmControlPanelEntity
):
    """Representation of a Vimar SAI2 alarm area.

    Each named SAI2 group (area) is exposed as one alarm_control_panel entity.
    State is derived from the group's child objects (Disinserito, Inserito INT,
    Inserito ON, Inserito PAR, Allarme).
    """

    _attr_has_entity_name = True
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    # SAI2 authenticates via PIN sent with each command;
    # HA should NOT prompt for a code.
    _attr_code_arm_required = False

    def __init__(
        self,
        coordinator: VimarDataUpdateCoordinator,
        group_id: str,
        group_data: dict[str, Any],
        area_index: int,
        sai_pin: str,
    ) -> None:
        """Initialize the alarm control panel."""
        super().__init__(coordinator)
        self._group_id = group_id
        self._group_data = group_data
        self._area_index = area_index
        self._sai_pin = sai_pin
        self._attr_name = group_data["name"]
        self._attr_unique_id = f"vimar_sai2_{group_id}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.vimarproject is not None
            and self.coordinator.vimarproject.sai2_groups is not None
            and self._group_id in self.coordinator.vimarproject.sai2_groups
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state.

        Reads from sai2_area_values (live DPADD_OBJECT.CURRENT_VALUE bitmask)
        when available, falling back to the children dict from last discovery.
        """
        project = self.coordinator.vimarproject
        if project is None:
            return None

        # --- Primary: live bitmask from DPADD_OBJECT ---
        area_values = project.sai2_area_values
        if area_values is not None and self._group_id in area_values:
            raw = area_values[self._group_id]
            label = _parse_sai2_area_value(raw)
            _LOGGER.debug(
                "SAI2 group %s (%s): raw='%s' -> %s",
                self._group_id,
                self._group_data.get("name", "?"),
                raw,
                label,
            )
            return SAI2_STATE_MAP.get(label, AlarmControlPanelState.DISARMED)

        # --- Fallback: children dict (populated at discovery / optimistic) ---
        if project.sai2_groups is None:
            return None
        group = project.sai2_groups.get(self._group_id)
        if group is None:
            return None
        children = group.get("children", {})
        alarm_child = children.get("Allarme")
        if alarm_child and alarm_child.get("value") == "1":
            return AlarmControlPanelState.TRIGGERED
        for label, ha_state in SAI2_STATE_MAP.items():
            if label == "Allarme":
                continue
            child = children.get(label)
            if child and child.get("value") == "1":
                return ha_state
        return AlarmControlPanelState.DISARMED

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for diagnostics."""
        project = self.coordinator.vimarproject
        attrs: dict[str, Any] = {
            "area_index": self._area_index,
            "area_name": self._group_data.get("name", "?"),
        }
        if project and project.sai2_groups:
            group = project.sai2_groups.get(self._group_id, {})
            children = group.get("children", {})
            for label, child in children.items():
                attrs[f"sai2_{label}"] = child.get("value", "?")
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info — all areas share the single SAI Alarm device."""
        return DeviceInfo(
            identifiers={(DOMAIN, "sai2_alarm")},
        )

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._send_sai2_command(SAI2_CMD_OFF, "Disinserito")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home (INT) command."""
        await self._send_sai2_command(SAI2_CMD_INT, "Inserito INT")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away (ON) command."""
        await self._send_sai2_command(SAI2_CMD_ON, "Inserito ON")

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night (PAR) command."""
        await self._send_sai2_command(SAI2_CMD_PAR, "Inserito PAR")

    async def _send_sai2_command(self, command: int, state_label: str) -> None:
        """Send command to SAI2 area via service-vimarsai2allgroupsset.

        If switching between armed modes (e.g. PAR -> ON), the SAI2 system
        requires a disarm first. This method handles that automatically
        and invisibly: the UI shows the target state immediately.

        Args:
            command: SAI2 command code (0=OFF, 1=ON, 2=INT, 3=PAR)
            state_label: State label for optimistic update
        """
        if not self._sai_pin:
            _LOGGER.error(
                "SAI2: cannot send command, no PIN configured. "
                "Set the SAI PIN in the integration options."
            )
            return

        project = self.coordinator.vimarproject
        if project is None or project.sai2_groups is None:
            _LOGGER.error("SAI2: cannot send command, project not available")
            return

        group = project.sai2_groups.get(self._group_id)
        if group is None:
            _LOGGER.error("SAI2: group %s not found", self._group_id)
            return

        vimarconnection = self.coordinator.vimarconnection
        if vimarconnection is None:
            _LOGGER.error("SAI2: vimarconnection not available")
            return

        # Capture current state BEFORE optimistic update.
        was_armed = self.alarm_state not in (
            AlarmControlPanelState.DISARMED, None
        )

        # --- Optimistic update FIRST ---
        # Patch sai2_area_values and children immediately so the UI shows
        # the target state before any SOAP call.  This makes the intermediate
        # disarm (if needed) completely invisible to the user.
        optimistic_bitmask = {
            "Disinserito": "00000000",
            "Inserito INT": "00000101",   # bit2 + bit0
            "Inserito ON": "00000011",    # bit1 + bit0
            "Inserito PAR": "00001001",   # bit3 + bit0
        }
        expected = optimistic_bitmask.get(state_label, "00000000")
        if project.sai2_area_values is not None:
            project.sai2_area_values[self._group_id] = expected
        children = group.get("children", {})
        for label in SAI2_STATE_MAP:
            child = children.get(label)
            if child:
                child["value"] = "1" if label == state_label else "0"
        self.async_write_ha_state()

        # Protect optimistic value from being overwritten by the next slim
        # poll (server may not have processed the command yet).
        project.sai2_optimistic_until[self._group_id] = time.monotonic() + 5.0

        # --- Auto-disarm if switching between armed modes ---
        # Only needed when going from armed -> different armed mode.
        # Disarmed -> armed does not need this step.
        if command != SAI2_CMD_OFF and was_armed:
            _LOGGER.info(
                "SAI2: area %d (%s) is armed, disarming first",
                self._area_index, group["name"],
            )
            await self.hass.async_add_executor_job(
                vimarconnection.set_sai2_status,
                SAI2_CMD_OFF,
                self._area_index,
                self._sai_pin,
            )
            await asyncio.sleep(1.0)

        # --- Send target command ---
        _LOGGER.info(
            "SAI2: sending command %d to area %d (%s)",
            command, self._area_index, group["name"],
        )

        success = await self.hass.async_add_executor_job(
            vimarconnection.set_sai2_status,
            command,
            self._area_index,
            self._sai_pin,
        )

        if not success:
            _LOGGER.error("SAI2: command failed for area %s", group["name"])
