"""Vimar Update State coordinator."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry, SOURCE_REAUTH
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, PlatformNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    _LOGGER,
    CONF_CERTIFICATE,
    CONF_GLOBAL_CHANNEL_ID,
    CONF_IGNORE_PLATFORM,
    CONF_OVERRIDE,
    CONF_SECURE,
    DEFAULT_CERTIFICATE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
    PLATFORMS,
)
from .vimar_device_customizer import VimarDeviceCustomizer
from .vimarlink.vimarlink import VimarLink, VimarProject

log = _LOGGER


class VimarDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    vimarconnection: VimarLink | None = None
    vimarproject: VimarProject | None = None
    _timeout: float = DEFAULT_TIMEOUT
    webserver_id = ""
    entity_unique_id_prefix = ""
    _first_update_data_executed = False
    _platforms_registered = False
    _last_devices_hash = ""
    _consecutive_auth_failures = 0
    _reauth_triggered = False

    # --- slim-poll state (class-level defaults, overridden as instance attrs in __init__) ---
    _slim_poll_active: bool = False
    _last_device_count: int = -1

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, vimarconfig: ConfigType) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.vimarconfig = vimarconfig
        self.devices_for_platform = {}
        if entry:
            self.entity_unique_id_prefix = entry.unique_id or ""

        # FIX #2: initialize mutable attributes as instance-level to avoid sharing
        # across multiple coordinator instances (e.g. two Vimar config entries).
        self._device_state_hashes: dict[str, str] = {}
        self._changed_device_ids: set[str] = set()
        self._known_status_ids: list[int] = []

        timeout = vimarconfig.get(CONF_TIMEOUT) or DEFAULT_TIMEOUT
        if timeout > 0:
            self._timeout = float(timeout)
        uptade_interval = float(vimarconfig.get(CONF_SCAN_INTERVAL) or DEFAULT_SCAN_INTERVAL)
        if uptade_interval < 1:
            uptade_interval = DEFAULT_SCAN_INTERVAL
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=uptade_interval), config_entry=entry
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        _LOGGER.debug("Updating coordinator..")

        # FIX #23b: svuota il set a inizio ciclo cosi' ogni poll parte pulito.
        # I listener (_handle_coordinator_update) vengono chiamati DOPO il
        # return di questo metodo, quindi il set e' ancora pieno quando serve.
        # request_statemachine_update() puo' aggiungere device_id in qualsiasi
        # momento: se arriva DOPO questo reset ma PRIMA di _detect_state_changes
        # verra' comunque incluso nel newly_changed del ciclo successivo tramite
        # il confronto hash (lo stato locale e' gia' stato aggiornato da
        # _apply_state_change).
        self._changed_device_ids = set()

        try:
            if self.vimarproject is None:
                raise PlatformNotReady

            if self.vimarconnection is None or not self.vimarconnection.is_logged():
                async with async_timeout.timeout(self._timeout):
                    await self.validate_vimar_credentials()

            async with async_timeout.timeout(self._timeout):
                forced = not self._first_update_data_executed or not self._platforms_registered

                if forced or not self._slim_poll_active:
                    _LOGGER.debug("Vimar: running full discovery")
                    devices = await self.hass.async_add_executor_job(self.vimarproject.update, True)

                    if devices and len(devices) > 0:
                        self._known_status_ids = self._collect_status_ids(devices)
                        # Include SAI2 alarm CIDs in slim poll
                        if self.vimarproject.sai2_groups or self.vimarproject.sai2_zones:
                            sai2_ids = self.vimarconnection.get_sai2_status_ids(
                                self.vimarproject.sai2_groups,
                                self.vimarproject.sai2_zones,
                            )
                            self._known_status_ids.extend(sai2_ids)
                        self._last_device_count = len(devices)
                        self._slim_poll_active = True
                        _LOGGER.debug(
                            "Vimar: discovery complete - %d devices, %d status IDs indexed for slim poll",
                            len(devices),
                            len(self._known_status_ids),
                        )
                else:
                    _LOGGER.debug(
                        "Vimar: slim poll (%d status IDs)", len(self._known_status_ids)
                    )
                    slim_results = await self.hass.async_add_executor_job(
                        self.vimarconnection.get_status_only, self._known_status_ids
                    )

                    if slim_results is None:
                        _LOGGER.debug(
                            "Vimar: slim poll returned None (transient), keeping previous state"
                        )
                        return self.vimarproject.devices

                    self._apply_slim_results(self.vimarproject.devices, slim_results)
                    # Update SAI2 zone/group children from slim poll results
                    if self.vimarproject.sai2_groups or self.vimarproject.sai2_zones:
                        self.vimarconnection.update_sai2_from_slim(
                            self.vimarproject.sai2_groups,
                            self.vimarproject.sai2_zones,
                            slim_results,
                        )
                    # Refresh SAI2 live area values — DPADD_OBJECT.CURRENT_VALUE
                    # for SAI2 group IDs updates immediately after commands,
                    # unlike the DPAD_SAI2GATEWAY_SAI2GROUPCHILDREN view.
                    if self.vimarproject.sai2_groups:
                        group_ids = list(self.vimarproject.sai2_groups.keys())
                        fresh_values = await self.hass.async_add_executor_job(
                            self.vimarconnection.get_sai2_area_values, group_ids
                        )
                        if fresh_values is not None:
                            # Merge fresh values but skip group_ids that have
                            # a pending optimistic update (command in flight).
                            now = time.monotonic()
                            guard = self.vimarproject.sai2_optimistic_until
                            if self.vimarproject.sai2_area_values is None:
                                self.vimarproject.sai2_area_values = {}
                            for gid, val in fresh_values.items():
                                if guard.get(gid, 0) > now:
                                    continue  # optimistic value still protected
                                self.vimarproject.sai2_area_values[gid] = val
                    # Refresh SAI2 zone values (physical sensor states)
                    if self.vimarproject.sai2_zones:
                        zone_ids = list(self.vimarproject.sai2_zones.keys())
                        fresh_zone_values = await self.hass.async_add_executor_job(
                            self.vimarconnection.get_sai2_area_values, zone_ids
                        )
                        if fresh_zone_values is not None:
                            self.vimarproject.sai2_zone_values = fresh_zone_values
                    devices = self.vimarproject.devices

                    current_count = len(devices)
                    if current_count != self._last_device_count:
                        _LOGGER.info(
                            "Vimar: topology change detected (%d \u2192 %d devices), scheduling rediscovery",
                            self._last_device_count,
                            current_count,
                        )
                        self._slim_poll_active = False
                        self._last_device_count = current_count

            if not devices or len(devices) == 0:
                raise UpdateFailed("Could not find any devices on Vimar Webserver")

            if not self._first_update_data_executed:
                self._first_update_data_executed = True

            # FIX #22 + #23b: _changed_device_ids e' stato resettato a inizio
            # ciclo; ora lo popola con le novita' rilevate in questo poll.
            newly_changed = self._detect_state_changes(devices)
            self._changed_device_ids.update(newly_changed)

            if not self.last_update_success or self._last_devices_hash == "":
                self._reload_entry_if_devices_changed()

            self._consecutive_auth_failures = 0

            # FIX #23: log compatto, solo slim poll (platforms_registered=True).
            if _LOGGER.isEnabledFor(logging.DEBUG) and self._platforms_registered:
                self._log_poll_summary(devices)

            return devices

        except ConfigEntryAuthFailed:
            self._handle_auth_failure()
            raise
        except TimeoutError:
            _LOGGER.warning("Timeout communicating with Vimar web server")
            raise UpdateFailed("Timeout communicating with Vimar web server")
        except aiohttp.ClientError as err:
            _LOGGER.warning("Client error communicating with Vimar: %s", err)
            raise UpdateFailed(f"Client error: {err}")
        except Exception as err:
            if self._is_auth_error(err):
                self._handle_auth_failure()
                raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
            raise UpdateFailed(f"Error communicating with API: {err}")

    # ------------------------------------------------------------------
    # Poll summary log
    # ------------------------------------------------------------------

    def _log_poll_summary(self, devices: dict) -> None:
        """Emit two DEBUG lines: updated device names and skipped device names.

        FIX #23b: usa un set seen_ids per deduplicare i device fisici.
        I sensori multi-entity (es. CHMisuratore con 7 sub-sensori) hanno
        tutte le sub-entity con lo stesso _device_id: senza deduplicazione
        lo stesso nome verrebbe listato N volte. Con seen_ids ogni device
        fisico appare una sola volta, indipendentemente da quante entity
        HA ha creato per esso.
        """
        updated_names: list[str] = []
        skipped_names: list[str] = []
        seen_ids: set[str] = set()

        for platform_entities in self.devices_for_platform.values():
            for entity in platform_entities:
                device_id = getattr(entity, "_device_id", None)
                if device_id is None:
                    continue
                # VimarStatusSensor non e' nel device tree
                if device_id not in devices:
                    continue
                # deduplicazione: ogni device fisico una sola volta
                if device_id in seen_ids:
                    continue
                seen_ids.add(device_id)

                friendly = (
                    devices[device_id].get("device_friendly_name")
                    or devices[device_id].get("object_name")
                    or device_id
                )
                if device_id in self._changed_device_ids:
                    updated_names.append(friendly)
                else:
                    skipped_names.append(friendly)

        if updated_names:
            _LOGGER.debug("Updated  (%d): %s", len(updated_names), ", ".join(updated_names))
        if skipped_names:
            _LOGGER.debug("Skipped  (%d): %s", len(skipped_names), ", ".join(skipped_names))

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _is_auth_error(self, error: Exception) -> bool:
        """Check if error is authentication related."""
        error_str = str(error).lower()
        auth_indicators = [
            "log in fallito",
            "invalid credentials",
            "unauthorized",
            "401",
            "authentication failed",
            "login failed",
        ]
        return any(indicator in error_str for indicator in auth_indicators)

    def _handle_auth_failure(self) -> None:
        """Handle authentication failure by triggering reauth flow."""
        self._consecutive_auth_failures += 1

        if not self._reauth_triggered and self._consecutive_auth_failures >= 2:
            _LOGGER.warning(
                "Authentication failed %d times, triggering re-authentication flow",
                self._consecutive_auth_failures
            )
            self._reauth_triggered = True

            if self.entry:
                self.entry.async_start_reauth(self.hass)

    # ------------------------------------------------------------------
    # Slim-poll helpers
    # ------------------------------------------------------------------

    def _collect_status_ids(self, devices: dict) -> list[int]:
        """Extract all status_id integers from all known devices."""
        ids: set[int] = set()
        for device in devices.values():
            for status in device.get("status", {}).values():
                sid = status.get("status_id")
                if sid is not None:
                    try:
                        ids.add(int(sid))
                    except (ValueError, TypeError):
                        pass
        return list(ids)

    def _apply_slim_results(self, devices: dict, slim_results: list) -> None:
        """Patch CURRENT_VALUE from slim poll into existing device tree."""
        index: dict[str, tuple[str, str]] = {}
        for device_id, device in devices.items():
            for status_name, status in device.get("status", {}).items():
                sid = status.get("status_id")
                if sid is not None:
                    index[str(sid)] = (device_id, status_name)

        for row in slim_results:
            sid = str(row.get("status_id", ""))
            val = row.get("status_value")
            if sid in index:
                dev_id, sname = index[sid]
                devices[dev_id]["status"][sname]["status_value"] = val

    # ------------------------------------------------------------------
    # Existing methods
    # ------------------------------------------------------------------

    async def init_vimarproject(self) -> None:
        """Init VimarLink and VimarProject from entry config."""
        self._last_devices_hash = ""
        self._first_update_data_executed = False
        self._platforms_registered = False
        self._slim_poll_active = False
        self._known_status_ids = []
        self._last_device_count = -1
        self._consecutive_auth_failures = 0
        self._reauth_triggered = False
        self._device_state_hashes = {}
        self.devices_for_platform = {}
        vimarconfig = self.vimarconfig
        schema = "https" if vimarconfig.get(CONF_SECURE) else "http"
        host = vimarconfig.get(CONF_HOST)
        port = vimarconfig.get(CONF_PORT)
        username = vimarconfig.get(CONF_USERNAME)
        password = vimarconfig.get(CONF_PASSWORD)
        certificate = None
        if schema == "https" and vimarconfig.get(CONF_VERIFY_SSL):
            certificate = vimarconfig.get(CONF_CERTIFICATE, DEFAULT_CERTIFICATE)
        timeout = vimarconfig.get(CONF_TIMEOUT)
        global_channel_id = vimarconfig.get(CONF_GLOBAL_CHANNEL_ID)
        device_overrides = vimarconfig.get(CONF_OVERRIDE) or []

        vimarconnection = VimarLink(schema, host, port, username, password, certificate, timeout)
        device_customizer = VimarDeviceCustomizer(vimarconfig, device_overrides)

        def device_customizer_fn(device):
            device_customizer.customize_device(device)

        vimarproject = VimarProject(vimarconnection, device_customizer_fn)

        if global_channel_id is not None:
            vimarproject.global_channel_id = global_channel_id

        self.vimarconnection = vimarconnection
        self.vimarproject = vimarproject

    async def validate_vimar_credentials(self) -> None:
        """Validate Vimar credential config."""
        if self.vimarconnection is None:
            await self.init_vimarproject()
        try:
            if self.vimarconnection is None:
                raise PlatformNotReady("Vimar connection not initialized")
            valid_login = await self.hass.async_add_executor_job(self.vimarconnection.check_login)
            if not valid_login:
                raise ConfigEntryAuthFailed("Invalid credentials")
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            if self._is_auth_error(err):
                raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
            raise err

    async def async_register_devices_platforms(self):
        """Execute async_forward_entry_setup for each platform."""
        self.devices_for_platform = {}
        ignored_platforms = self.vimarconfig.get(CONF_IGNORE_PLATFORM) or []
        platforms = [
            i for i in PLATFORMS if i not in ignored_platforms or i == DEVICE_TYPE_BINARY_SENSOR
        ]
        await self.hass.config_entries.async_forward_entry_setups(self.entry, platforms)

        self._platforms_registered = True
        if len(self.devices_for_platform) > 0:
            await self.async_remove_old_devices()

    def _reload_entry_if_devices_changed(self):
        if self.vimarproject:
            devices = self.vimarproject.devices
            if devices is not None and len(devices) > 0:
                # FIX #13: O(n) join instead of O(n^2) string concatenation in loop.
                hash_parts: list[str] = []
                for device_id, device in devices.items():
                    hash_parts.append(
                        str(device["object_id"])
                        + "_"
                        + str(device["room_ids"])
                        + device["object_type"]
                        + device["object_name"]
                        + device["room_name"]
                    )
                devices_hash = "_".join(hash_parts)
                if devices_hash != self._last_devices_hash:
                    if self._last_devices_hash == "":
                        self._last_devices_hash = devices_hash
                    else:
                        self._last_devices_hash = devices_hash
                        if self._platforms_registered:
                            self.reload_entry()

    def reload_entry(self):
        """Reload_entry function if platforms_registered (updating entry)."""
        options = self.entry.options.copy()
        if options.get("fake_update_value", "") == "1":
            options.pop("fake_update_value")
        else:
            options["fake_update_value"] = "1"
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    async def async_remove_old_devices(self):
        """Clear unused devices and entities.

        FIX #12: configured_devices was built as a list of str(identifiers),
        but device_registry entries expose identifiers as a frozenset of tuples.
        The string comparison `str(frozenset) in list_of_str` would almost never
        match because Python's frozenset str representation is non-deterministic
        in ordering. Fix: store identifiers as the native frozenset and compare
        with the frozenset from the registry directly.
        """
        configured_device_ids: set[frozenset] = set()
        configured_entities: list[str] = []
        entities_to_be_removed: list[str] = []
        devices_to_be_removed: list[str] = []

        for devices in self.devices_for_platform.values():
            for device in devices:
                if hasattr(device, "device_info") and device.device_info:
                    raw_identifiers = (device.device_info or {}).get("identifiers")
                    if raw_identifiers:
                        configured_device_ids.add(frozenset(raw_identifiers))
                unique_id = device.unique_id
                if unique_id:
                    configured_entities.append(unique_id)

        entity_registry = er.async_get(self.hass)
        entity_entries = er.async_entries_for_config_entry(entity_registry, self.entry.entry_id)
        for entity_entry in entity_entries:
            identifier = entity_entry.unique_id
            if (
                identifier
                and identifier not in configured_entities
                and entity_entry.entity_id not in entities_to_be_removed
            ):
                entities_to_be_removed.append(entity_entry.entity_id)

        for entity_id in entities_to_be_removed:
            entity_registry.async_remove(entity_id)

        device_registry = dr.async_get(self.hass)
        device_registry_entries = dr.async_entries_for_config_entry(
            device_registry, self.entry.entry_id
        )
        for device_entry in device_registry_entries:
            device_identifiers_frozen = frozenset(device_entry.identifiers)
            if (
                device_identifiers_frozen not in configured_device_ids
                and device_entry.id not in devices_to_be_removed
            ):
                devices_to_be_removed.append(device_entry.id)

        for device_id in devices_to_be_removed:
            device_registry.async_remove_device(device_id)

    def _hash_device_state(self, device: dict) -> str:
        """Generate hash of device state for change detection."""
        state_data = {
            "object_id": device["object_id"],
            "status": device.get("status", {}),
        }
        state_json = json.dumps(state_data, sort_keys=True)
        return hashlib.md5(state_json.encode()).hexdigest()

    def _detect_state_changes(self, devices: dict[str, dict]) -> set[str]:
        """Detect which devices have changed states.

        Returns only the set of newly-changed device IDs detected in this
        poll cycle. The caller is responsible for merging into
        _changed_device_ids (use .update(), NOT direct assignment) so that
        IDs added by request_statemachine_update() between two poll cycles
        are preserved.
        """
        changed_ids = set()

        for device_id, device in devices.items():
            new_hash = self._hash_device_state(device)
            old_hash = self._device_state_hashes.get(device_id)

            if old_hash is None:
                changed_ids.add(device_id)
                log.debug("New device detected: %s", device_id)
            elif new_hash != old_hash:
                changed_ids.add(device_id)
                if log.isEnabledFor(10):
                    log.debug(
                        "Device %s (%s) state changed",
                        device_id,
                        device.get("device_friendly_name", "unknown"),
                    )

            self._device_state_hashes[device_id] = new_hash

        return changed_ids
