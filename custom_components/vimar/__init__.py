"""Vimar Platform integration."""


import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_USERNAME,
    SERVICE_RELOAD,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

from .const import (
    _LOGGER,
    CONF_CERTIFICATE,
    CONF_DELETE_AND_RELOAD_ALL_ENTITIES,
    CONF_GLOBAL_CHANNEL_ID,
    CONF_IGNORE_PLATFORM,
    CONF_OVERRIDE,
    CONF_SCHEMA,
    DEFAULT_CERTIFICATE,
    DEFAULT_PORT,
    DEFAULT_SCHEMA,
    DEFAULT_TIMEOUT,
    DEFAULT_USERNAME,
    DOMAIN,
    DOMAIN_CONFIG_YAML,
)
from .vimar_coordinator import VimarDataUpdateCoordinator

log = _LOGGER

CONFIG_DOMAIN_SCHEMA = {
    vol.Optional(CONF_HOST): cv.string,
    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_SCHEMA, default=DEFAULT_SCHEMA): cv.string,
    vol.Optional(CONF_CERTIFICATE, default=DEFAULT_CERTIFICATE): vol.Any(cv.string, None),
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Range(min=2, max=60),
    vol.Optional(CONF_GLOBAL_CHANNEL_ID): vol.Range(min=1, max=99999),
    vol.Optional(CONF_IGNORE_PLATFORM, default=[]): vol.All(cv.ensure_list, [cv.string]),
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


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up from config."""
    hass.data.setdefault(DOMAIN, {})

    await add_services(hass)

    # if there are no configuration.yaml settings then terminate
    if config.get(DOMAIN) is None:
        # We get here if the integration is set up using config flow
        return True

    conf = config.get(DOMAIN, {})
    hass.data.setdefault(DOMAIN_CONFIG_YAML, conf)

    if CONF_USERNAME in conf:
        configured = set(entry for entry in hass.config_entries.async_entries(DOMAIN))

        if len(configured) == 0:
            log.info("Importing configuration from yaml...after you can remove from yaml")
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data=conf.copy(),
                )
            )
        else:
            log.debug("Configuration from yaml already imported: you can remove from yaml")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vimar from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if entry.unique_id is None:
        log.info("vimar unique id was None")
        unique_id = slugify(entry.title)
        hass.config_entries.async_update_entry(entry, unique_id=unique_id)

    vimarconfig = (entry.options or {}).copy()
    if CONF_HOST not in vimarconfig:
        vimarconfig.update(entry.data or {})

    # Copy CONF_OVERRIDE from YAML only when present and not None.
    # FIX #5: using `yamlconf.get(cfg) or []` instead of `yamlconf.get(cfg)`
    # avoids storing None in vimarconfig when the key is absent from YAML.
    # dict.get() returns None both when the key is missing AND when its value
    # is explicitly None, so the old fallback default=[] had no effect in
    # the second case, causing VimarDeviceCustomizer to receive None and crash.
    yamlconf = hass.data.get(DOMAIN_CONFIG_YAML, {})
    for cfg in [CONF_OVERRIDE]:
        vimarconfig[cfg] = yamlconf.get(cfg) or []

    coordinator = VimarDataUpdateCoordinator(hass, entry=entry, vimarconfig=vimarconfig)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await coordinator.init_vimarproject()

    # FIX #6: always use async_config_entry_first_refresh() unconditionally.
    # async_setup_entry is only ever called by HA when the entry is in state
    # SETUP_IN_PROGRESS, so the old if/else branch was redundant.
    # More importantly, the string comparison `entry.state.name == "SETUP_IN_PROGRESS"`
    # used a non-public API (enum .name) that could silently break on any HA rename.
    # async_config_entry_first_refresh() is the HA-recommended call here: it
    # propagates ConfigEntryNotReady correctly on first-run failures.
    await coordinator.async_config_entry_first_refresh()

    if (entry.data or {}).get(CONF_DELETE_AND_RELOAD_ALL_ENTITIES):
        options = entry.data.copy()
        options.pop(CONF_DELETE_AND_RELOAD_ALL_ENTITIES)
        await coordinator.async_remove_old_devices()
        hass.config_entries.async_update_entry(entry, data=options)

    async def setup_then_listen() -> None:
        await coordinator.async_register_devices_platforms()
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    hass.async_create_task(setup_then_listen())

    return True


async def add_services(hass: HomeAssistant):
    """Add services."""

    async def service_update_call(call):
        forced = call.data.get("forced")
        for item in hass.data[DOMAIN].values():
            coordinator: VimarDataUpdateCoordinator = item
            await coordinator.validate_vimar_credentials()
            if coordinator.vimarproject:
                await hass.async_add_executor_job(coordinator.vimarproject.update, forced)

    hass.services.async_register(DOMAIN, SERVICE_UPDATE, service_update_call, SERVICE_UPDATE_SCHEMA)

    async def service_exec_vimar_sql_call(call):
        data = call.data
        sql = data.get("sql")
        for item in hass.data[DOMAIN].values():
            coordinator: VimarDataUpdateCoordinator = item
            await coordinator.validate_vimar_credentials()
            if coordinator.vimarconnection:
                payload = await hass.async_add_executor_job(
                    coordinator.vimarconnection._request_vimar_sql, sql
                )
                _LOGGER.info(
                    SERVICE_EXEC_VIMAR_SQL + " done: SQL: %s . Result: %s",
                    sql,
                    str(payload),
                )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXEC_VIMAR_SQL,
        service_exec_vimar_sql_call,
        SERVICE_EXEC_VIMAR_SQL_SCHEMA,
    )

    async def _handle_reload(service):
        entries_to_reload = []
        for item in hass.data[DOMAIN].values():
            coordinator: VimarDataUpdateCoordinator = item
            entries_to_reload.append(coordinator.entry)
        for entry in entries_to_reload:
            await async_reload_entry(hass, entry)

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if entry.entry_id not in hass.data[DOMAIN]:
        return True
    coordinator: VimarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    platforms = list(coordinator.devices_for_platform.keys())
    unloaded = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unloaded and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
