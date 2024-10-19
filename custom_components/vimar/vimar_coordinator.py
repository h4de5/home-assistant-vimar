"""Vimar Update State coordinator."""

import asyncio
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
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
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    _LOGGER,
    DOMAIN,
    DEFAULT_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    CONF_SECURE,
    CONF_CERTIFICATE,
    DEFAULT_CERTIFICATE,
    CONF_GLOBAL_CHANNEL_ID,
    CONF_OVERRIDE,
    CONF_IGNORE_PLATFORM,
    PLATFORMS,
    DEVICE_TYPE_BINARY_SENSOR,
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

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, vimarconfig: ConfigType) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.vimarconfig = vimarconfig
        self.devices_for_platform = {}
        if entry:
            self.entity_unique_id_prefix = entry.unique_id or ""
        timeout = vimarconfig.get(CONF_TIMEOUT) or DEFAULT_TIMEOUT
        if timeout > 0:
            self._timeout = float(timeout)
        uptade_interval = float(vimarconfig.get(CONF_SCAN_INTERVAL) or DEFAULT_SCAN_INTERVAL)
        if uptade_interval < 1:
            uptade_interval = DEFAULT_SCAN_INTERVAL
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=uptade_interval))

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        _LOGGER.debug("Updating coordinator..")

        try:
            if self.vimarproject is None:
                raise PlatformNotReady

            # if not logged, execute login with another timeout
            if self.vimarconnection is None or not self.vimarconnection.is_logged():
                async with async_timeout.timeout(self._timeout):
                    await self.validate_vimar_credentials()

            async with async_timeout.timeout(self._timeout):
                forced = not self._first_update_data_executed or not self._platforms_registered
                devices = await self.hass.async_add_executor_job(self.vimarproject.update, forced)

            if not devices or len(devices) == 0:
                raise UpdateFailed("Could not find any devices on Vimar Webserver")
            if not self._first_update_data_executed:
                self._first_update_data_executed = True
            # if last update failed, check devices changes and reload if need
            if not self.last_update_success or self._last_devices_hash == "":
                self._reload_entry_if_devices_changed()
            return devices
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        except asyncio.TimeoutError:
            raise
        except aiohttp.ClientError:
            raise
        # except ApiAuthError as err:
        #    # Raising ConfigEntryAuthFailed will cancel future updates
        #    # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #    raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        except BaseException as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def init_vimarproject(self) -> None:
        """Init VimarLink and VimarProject from entry config."""
        self._last_devices_hash = ""
        self._first_update_data_executed = False
        self._platforms_registered = False
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
        # ignored_platforms = vimarconfig.get(CONF_IGNORE_PLATFORM)
        # spunto per override: https://github.com/teharris1/insteon2/blob/master/__init__.py
        device_overrides = vimarconfig.get(CONF_OVERRIDE, [])

        # initialize a new VimarLink object
        vimarconnection = VimarLink(schema, host, port, username, password, certificate, timeout)

        device_customizer = VimarDeviceCustomizer(vimarconfig, device_overrides)

        def device_customizer_fn(device):
            device_customizer.customize_device(device)

        # will hold all the devices and their states
        vimarproject = VimarProject(vimarconnection, device_customizer_fn)

        if global_channel_id is not None:
            vimarproject.global_channel_id = global_channel_id

        self.vimarconnection = vimarconnection
        self.vimarproject = vimarproject

    async def validate_vimar_credentials(self) -> None:
        """Validate Vimar credential config."""
        if self.vimarconnection is None:
            await self.init_vimarproject()
        # Verify that passed in configuration works
        # starting it outside MainThread
        # host = self.vimarconfig.get(CONF_HOST)
        try:
            if self.vimarconnection is None:
                raise PlatformNotReady
            valid_login = await self.hass.async_add_executor_job(self.vimarconnection.check_login)
            if not valid_login:
                raise PlatformNotReady
            # res = await self.hass.async_add_executor_job(self.vimarconnection.check_session)
            # res1 = res
        # except VimarApiError as err:
        #    _LOGGER.error("Webserver %s: %s", host, str(err))
        #    valid_login = False
        except BaseException as err:
            # _LOGGER.error("Login Exception: %s", str(err))
            raise err
        # self._valid_login = valid_login
        # if not valid_login:
        #    raise PlatformNotReady

    async def async_register_devices_platforms(self):
        """Execute async_forward_entry_setup for each platform."""
        self.devices_for_platform = {}
        ignored_platforms = self.vimarconfig.get(CONF_IGNORE_PLATFORM) or []
        # DEVICE_TYPE_BINARY_SENSOR needed for webserver status sensor
        platforms = [i for i in PLATFORMS if i not in ignored_platforms or i == DEVICE_TYPE_BINARY_SENSOR]
        await self.hass.config_entries.async_forward_entry_setups(self.entry, platforms)
        
        self._platforms_registered = True
        if len(self.devices_for_platform) > 0:
            await self.async_remove_old_devices()

    def _reload_entry_if_devices_changed(self):
        if self.vimarproject:
            devices = self.vimarproject.devices
            if devices is not None and len(devices) > 0:
                devices_hash = ""
                for device_id, device in devices.items():
                    device_hash = (
                        str(device["object_id"])
                        + "_"
                        + str(device["room_ids"])
                        + device["object_type"]
                        + device["object_name"]
                        + device["room_name"]
                    )
                    devices_hash = devices_hash + "_" + device_hash
                if devices_hash != self._last_devices_hash:
                    if self._last_devices_hash == "":
                        self._last_devices_hash = devices_hash
                    else:
                        self._last_devices_hash = devices_hash
                        if self._platforms_registered:
                            self.reload_entry()

    def reload_entry(self):
        """Reload_entry function if platforms_registered (updating entry)."""
        # updating entry, force to reload it :) because added event in entry.add_update_listener(async_reload_entry)
        options = self.entry.options.copy()
        if options.get("fake_update_value", "") == "1":
            options.pop("fake_update_value")
        else:
            options["fake_update_value"] = "1"
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    async def async_remove_old_devices(self):
        """Clear unused devices and entities."""
        configured_devices = []
        configured_entities = []
        entities_to_be_removed = []
        devices_to_be_removed = []
        for devices in self.devices_for_platform.values():
            for device in devices:
                if hasattr(device, "device_info"):
                    identifier = str((device.device_info or {}).get("identifiers", ""))
                    configured_devices.append(identifier)
                unique_id = device.unique_id
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

        for enity_id in entities_to_be_removed:
            entity_registry.async_remove(enity_id)

        device_registry = dr.async_get(self.hass)
        device_registry_entities = dr.async_entries_for_config_entry(device_registry, self.entry.entry_id)
        for device_entry in device_registry_entities:
            identifier = str(device_entry.identifiers)
            if identifier and identifier not in configured_devices and device_entry.id not in devices_to_be_removed:
                devices_to_be_removed.append(device_entry.id)

        for device_id in devices_to_be_removed:
            device_registry.async_remove_device(device_id)
