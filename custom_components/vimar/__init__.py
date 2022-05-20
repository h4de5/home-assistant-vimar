"""Vimar Platform integration."""
import asyncio
import logging
import os
from datetime import timedelta
from platform import platform
from typing import Tuple

import async_timeout
from homeassistant.util import slugify
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    SERVICE_RELOAD
)
from homeassistant.exceptions import PlatformNotReady, ConfigEntryNotReady
from homeassistant.core import Config, HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant import config_entries
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import *
from .const import _LOGGER
from .vimar_coordinator import VimarDataUpdateCoordinator

log = _LOGGER

CONFIG_DOMAIN_SCHEMA = {
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_SCHEMA, default=DEFAULT_SCHEMA): cv.string,
    vol.Optional(CONF_CERTIFICATE, default=DEFAULT_CERTIFICATE): vol.Any(
        cv.string, None
    ),
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Range(min=2, max=60),
    vol.Optional(CONF_GLOBAL_CHANNEL_ID): vol.Range(min=1, max=99999),
    vol.Optional(CONF_IGNORE_PLATFORM, default=[]): vol.All(
        cv.ensure_list, [cv.string]
    ),
    vol.Optional(CONF_OVERRIDE, default=[]): cv.ensure_list,
}
CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(CONFIG_DOMAIN_SCHEMA)},
    extra=vol.ALLOW_EXTRA,
)

SERVICE_UPDATE = "update_entities"
SERVICE_UPDATE_SCHEMA = vol.Schema({vol.Optional("forced", default=True): cv.boolean})
SERVICE_EXEC_VIMAR_SQL = "exec_vimar_sql"
SERVICE_EXEC_VIMAR_SQL_SCHEMA = vol.Schema({vol.Required("sql"): cv.string})
SERVICE_RELOAD_DEFAULT = "reload_default"
SERVICE_RELOAD_DEFAULT_SCHEMA = vol.Schema({})

@asyncio.coroutine
async def async_setup(hass: HomeAssistant, config: Config):
    """Set up from config."""
    hass.data.setdefault(DOMAIN, {})

    await add_services(hass)

    # if there are no configuration.yaml settings then terminate
    if config.get(DOMAIN) is None:
        # We get her if the integration is set up using config flow
        return True

    conf = config.get(DOMAIN, {})
    hass.data.setdefault(DOMAIN_CONFIG_YAML, conf)

    if CONF_USERNAME in conf:
        # https://www.programcreek.com/python/?code=davesmeghead%2Fvisonic%2Fvisonic-master%2Fcustom_components%2Fvisonic%2F__init__.py
        # has there been a flow configured panel connection before
        configured = set(entry for entry in hass.config_entries.async_entries(DOMAIN))

        # if there is not a flow configured connection previously
        #   then create a flow connection from the configuration.yaml data
        if len(configured) == 0:
            # get the configuration.yaml settings and make a 'flow' task :)
            #   this will run 'async_step_import' in config_flow.py
            log.info("Importing configuration from yaml...after you can remove from yaml")
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf.copy()
                )
            )
        else:
            log.debug("Configuration from yaml already imported: you can remove from yaml")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """async_setup_entry"""
    hass.data.setdefault(DOMAIN, {})

    if entry.unique_id is None:
        log.info("vimar unique id was None")
        unique_id = slugify(entry.title)
        hass.config_entries.async_update_entry(entry, unique_id=unique_id)

    vimarconfig = (entry.options or {}).copy()
    if CONF_HOST not in vimarconfig:
        vimarconfig.update(entry.data or {})

    # Set default values on conf from yaml, that not can specified with flow
    yamlconf = hass.data.get(DOMAIN_CONFIG_YAML, {})
    for cfg in [CONF_OVERRIDE]:
        vimarconfig[cfg] = yamlconf.get(cfg)

    coordinator = VimarDataUpdateCoordinator(hass, entry=entry, vimarconfig=vimarconfig)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await coordinator.init_vimarproject()
    await coordinator.async_config_entry_first_refresh()
    coordinator.vimarproject.check_devices()

    coordinator.init_available_platforms()

    if (entry.data or {}).get(CONF_DELETE_AND_RELOAD_ALL_ENTITIES):
        options = entry.data.copy()
        options.pop(CONF_DELETE_AND_RELOAD_ALL_ENTITIES)
        await coordinator.async_remove_old_devices()
        hass.config_entries.async_update_entry(entry, data=options)


    async def setup_then_listen() -> None:
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_setup(entry, platform)
                for platform in PLATFORMS
            ]
        )

        await coordinator.async_remove_old_devices()
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    hass.async_create_task(setup_then_listen())

    return True


async def add_services(hass: HomeAssistant):
    """Add services."""
    async def service_update_call(call):
        forced = call.data.get("forced")
        for item in hass.data[DOMAIN].values():
            coordinator : VimarDataUpdateCoordinator = item
            await hass.async_add_executor_job(coordinator.validate_vimar_credentials)
            await hass.async_add_executor_job(coordinator.vimarproject.update, forced)

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE, service_update_call, SERVICE_UPDATE_SCHEMA
    )

    async def service_exec_vimar_sql_call(call):
        data = call.data
        sql = data.get("sql")
        for item in hass.data[DOMAIN].values():
            coordinator : VimarDataUpdateCoordinator = item
            await hass.async_add_executor_job(coordinator.validate_vimar_credentials)
            payload = await hass.async_add_executor_job(coordinator.vimarconnection._request_vimar_sql, sql)
            _LOGGER.info(
                SERVICE_EXEC_VIMAR_SQL + " done: SQL: %s . Result: %s", sql, str(payload)
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXEC_VIMAR_SQL,
        service_exec_vimar_sql_call,
        SERVICE_EXEC_VIMAR_SQL_SCHEMA,
    )

    #async def service_reload_default_call(call):
    #    entries_to_reload = []
    #    for item in hass.data[DOMAIN].values():
    #        coordinator : VimarDataUpdateCoordinator = item
    #        coordinator.init_available_platforms()
    #        coordinator.devices_for_platform = {} #set loaded devices as fake array empty :)
    #        await coordinator.async_remove_old_devices()
    #        entries_to_reload.append(coordinator.entry)
    #    for entry in entries_to_reload:
    #        await async_reload_entry(hass, entry)
    #
    #hass.services.async_register(
    #    DOMAIN,
    #    SERVICE_RELOAD_DEFAULT,
    #    service_reload_default_call,
    #    SERVICE_RELOAD_DEFAULT_SCHEMA,
    #)
    async def _handle_reload(service):
        entries_to_reload = []
        for item in hass.data[DOMAIN].values():
            coordinator : VimarDataUpdateCoordinator = item
            entries_to_reload.append(coordinator.entry)
        for entry in entries_to_reload:
            await async_reload_entry(hass, entry)

    hass.helpers.service.async_register_admin_service(
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    #coordinator : VimarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unloaded and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)