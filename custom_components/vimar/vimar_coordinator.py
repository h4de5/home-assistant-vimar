import asyncio
import aiohttp
import logging
import os
from datetime import timedelta
from pickle import DEFAULT_PROTOCOL
from typing import Tuple

import async_timeout
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
from homeassistant.exceptions import PlatformNotReady, ConfigEntryNotReady
from homeassistant.core import Config, HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant import config_entries
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import (device_registry as dr, entity_registry as er)
from homeassistant.helpers.device_registry import DeviceRegistry
from .vimar_device_customizer import VimarDeviceCustomizer

from .const import *
from .const import _LOGGER
from .vimarlink.vimarlink import VimarApiError, VimarLink, VimarProject

log = _LOGGER


class VimarDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    vimarconnection : VimarLink = None
    vimarproject : VimarProject = None
    _timeout : float = DEFAULT_TIMEOUT
    webserver_id = ""
    entity_unique_id_prefix = ""
    _init_executed = False

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, vimarconfig: ConfigType
    ) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.vimarconfig = vimarconfig
        self.platforms = []
        self.devices_for_platform = {}
        timeout = vimarconfig.get(CONF_TIMEOUT) or DEFAULT_TIMEOUT
        if timeout > 0:
            self._timeout = float(timeout)

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=8)
        )

    def init_available_platforms(self):
        """Init platforms variable with AVAILABLE_PLATFORMS excluding ignored_platforms"""
        self._init_executed = True
        #self.platforms.append("switch")
        ignored_platforms = self.vimarconfig.get(CONF_IGNORE_PLATFORM)
        for platform in PLATFORMS:
            if not ignored_platforms or platform not in ignored_platforms:
                self.platforms.append(platform)

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        _LOGGER.debug("Updating coordinator..")

        try:
            #if not logged, execute login with another timeout
            if self.vimarconnection is None or not self.vimarconnection.is_logged():
                async with async_timeout.timeout(self._timeout):
                    await self.validate_vimar_credentials()

            async with async_timeout.timeout(self._timeout):
                return await self.hass.async_add_executor_job(self.vimarproject.update)
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        except asyncio.TimeoutError:
            raise
        except aiohttp.ClientError:
            raise
        #except ApiAuthError as err:
        #    # Raising ConfigEntryAuthFailed will cancel future updates
        #    # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #    raise ConfigEntryAuthFailed from err
        #except ApiError as err:
        except BaseException as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def init_vimarproject(self) -> None:
        vimarconfig = self.vimarconfig
        schema = vimarconfig.get(CONF_SCHEMA)
        host = vimarconfig.get(CONF_HOST)
        port = vimarconfig.get(CONF_PORT)
        username = vimarconfig.get(CONF_USERNAME)
        password = vimarconfig.get(CONF_PASSWORD)
        certificate = vimarconfig.get(CONF_CERTIFICATE)
        timeout = vimarconfig.get(CONF_TIMEOUT)
        global_channel_id = vimarconfig.get(CONF_GLOBAL_CHANNEL_ID)
        # ignored_platforms = vimarconfig.get(CONF_IGNORE_PLATFORM)
        # spunto per override: https://github.com/teharris1/insteon2/blob/master/__init__.py
        device_overrides = vimarconfig.get(CONF_OVERRIDE, [])

        # initialize a new VimarLink object
        vimarconnection = VimarLink(
            schema, host, port, username, password, certificate, timeout
        )

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
        #host = self.vimarconfig.get(CONF_HOST)
        try:
            valid_login = await self.hass.async_add_executor_job(self.vimarconnection.check_login)
            if not valid_login:
                raise PlatformNotReady
            #res = await self.hass.async_add_executor_job(self.vimarconnection.check_session)
            #res1 = res
        #except VimarApiError as err:
        #    _LOGGER.error("Webserver %s: %s", host, str(err))
        #    valid_login = False
        except BaseException as err:
            #_LOGGER.error("Login Exception: %s", str(err))
            raise err
        #self._valid_login = valid_login
        #if not valid_login:
        #    raise PlatformNotReady

    async def async_remove_old_devices(self):
        """Clear unused devices and entities"""
        if not self._init_executed:
            return
        configured_devices = []
        configured_entities = []
        entities_to_be_removed = []
        devices_to_be_removed = []
        for devices in self.devices_for_platform.values():
            for device in devices:
                if hasattr(device, 'device_info'):
                    identifier = str((device.device_info or {}).get("identifiers", ""))
                    configured_devices.append(identifier)
                unique_id = device.unique_id
                configured_entities.append(unique_id)

        entity_registry = await er.async_get_registry(self.hass)
        entity_entries = er.async_entries_for_config_entry(entity_registry, self.entry.entry_id)
        for entity_entry in entity_entries:
            identifier = entity_entry.unique_id
            if identifier and identifier not in configured_entities and entity_entry.entity_id not in entities_to_be_removed:
                entities_to_be_removed.append(entity_entry.entity_id)

        for enity_id in entities_to_be_removed:
            entity_registry.async_remove(enity_id)

        device_registry = await dr.async_get_registry(self.hass)
        device_registry_entities = dr.async_entries_for_config_entry(device_registry, self.entry.entry_id)
        for device_entry in device_registry_entities:
            identifier = str(device_entry.identifiers)
            if identifier and identifier not in configured_devices and device_entry.id not in devices_to_be_removed:
                devices_to_be_removed.append(device_entry.id)

        for device_id in devices_to_be_removed:
            device_registry.async_remove_device(device_id)

