"""Config flow for the Vimar Security System component."""
#https://aiqianji.com/home-assistant/core/raw/frenck-2020-0790/homeassistant/components/abode/config_flow.py

#from Vimarpy import Vimar
#from Vimarpy.exceptions import VimarException
from calendar import c
from requests.exceptions import ConnectTimeout, HTTPError
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import callback

from .__init__ import CONFIG_DOMAIN_SCHEMA
from .const import *
from .const import _LOGGER

from homeassistant.const import (CONF_HOST, CONF_PASSWORD, CONF_PORT,
                                 CONF_TIMEOUT, CONF_USERNAME, CONF_PASSWORD, CONF_USERNAME)
import homeassistant.helpers.config_validation as cv
from .vimar_coordinator import VimarDataUpdateCoordinator


#def get_vol_optional(name, config, default) -> Optional:
#    if name not in config and default is None:
#        return vol.Optional(name)
#    def_value = config.get(name, default)
#    if def_value:
#        return vol.Optional(name, default=def_value)
#    return vol.Optional(name)


@config_entries.HANDLERS.register(DOMAIN)
class VimarFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vimar."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        #self.data: dict[str, Any] = {}
        """Initialize."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        schema = get_schema_config_user(user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                coordinator = VimarDataUpdateCoordinator(self.hass, entry={}, vimarconfig=user_input)
                await coordinator.validate_vimar_credentials()
            except BaseException as ex:
                set_errors_from_ex(ex, errors)

            if not errors:
                title = user_input.pop(CONF_TITLE, "") or user_input.get(CONF_HOST) or user_input.get(CONF_USERNAME)
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), errors=errors
        )


    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        _LOGGER.info("VIMAR async_step_import")
        if self._async_current_entries():
            _LOGGER.warning("Only one configuration of Vimar is allowed.")
            return self.async_abort(reason="single_instance_allowed")
        user_input = import_config.copy()
        title = user_input.pop(CONF_TITLE, "") or user_input.get(CONF_HOST) or user_input.get(CONF_USERNAME)
        return self.async_create_entry(title=title, data=user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the Home Assistant remote integration."""

    def __init__(self, config_entry):
        """Initialize remote_homeassistant options flow."""
        self.config_entry = config_entry
        self.options = (config_entry.options or {}).copy()
        if CONF_HOST not in self.options:
            self.options.update(config_entry.data or {})
        self._init_schema({}, {})

    def _init_schema(self, user_input, schema):
        self.schema = schema
        self.schema_vol = vol.Schema(schema)
        self.errors: dict[str, str] = {}
        self.user_input = user_input
        self.options_with_user_input = self.options.copy()
        if user_input:
            self._dict_update(self.options_with_user_input)

    def _options_update(self):
        self._dict_update(self.options)

    def _dict_update(self, options):
        for key in self.schema.keys(): #set all values in form, if not present remove it
            value = self.user_input.get(str(key))
            options[str(key)] = value
            if value is None: #remove None value, problem to save in json!
                options.pop(str(key))

    def _async_show_form_step(self, step):
        return self.async_show_form(
            step_id=step, data_schema=self.schema_vol, errors=self.errors
        )

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        self._init_schema(user_input, get_schema_options_init(user_input or self.options))
        if user_input is not None:
            try:
                coordinator = VimarDataUpdateCoordinator(self.hass, entry={}, vimarconfig=self.options_with_user_input)
                await coordinator.validate_vimar_credentials()
            except BaseException as ex:
                set_errors_from_ex(ex, self.errors)

        if user_input is not None and not self.errors:
            self._options_update()
            return await self.async_step_two()

        return self._async_show_form_step("init")

    async def async_step_two(self, user_input=None):
        """Manage domain and entity filters."""
        self._init_schema(user_input, get_schema_options_two(user_input or self.options))

        if user_input is not None and not self.errors:
            self._options_update()
            return self.async_create_entry(title="", data=self.options)

        return self._async_show_form_step("two")


def set_errors_from_ex(ex: BaseException, errors: dict[str, str]):
    exstr = str(ex)
    if "Log In Fallito" in exstr: #message returned from vimar
        errors["base"] = "invalid_auth"
    elif "HTTP error occurred" in exstr or "Client Error:" in exstr or "ConnectTimeoutError" in exstr or "NewConnectionError" in exstr:
        errors["base"] = "cannot_connect"
    elif "SSLError" in exstr:
        errors["base"] = "invalid_cert"
    else:
        errors["base"] = "unknown"

def get_vol_default(config: dict, key, default = None):
    if config:
        return config.get(key) or vol.UNDEFINED
    return default or vol.UNDEFINED

def get_vol_descr(config: dict, key, default = None):
    def_value = get_vol_default(config, key, default)
    res = ({ "suggested_value": def_value }) if def_value and def_value is not vol.UNDEFINED else {}
    return res

def get_schema_config_user(config: dict = {}) -> dict:
    """Return a shcema configuration dict for HACS."""
    config = config if CONF_HOST in (config or {}) else None
    schema = {
        vol.Required(CONF_TITLE, description=get_vol_descr(config, CONF_TITLE)): str,
        vol.Required(CONF_HOST, description=get_vol_descr(config, CONF_HOST)): str,
        vol.Required(CONF_USERNAME, description=get_vol_descr(config, CONF_USERNAME)): str,
        vol.Required(CONF_PASSWORD, description=get_vol_descr(config, CONF_PASSWORD)): str,
        vol.Required(CONF_SCHEMA, description=get_vol_descr(config, CONF_SCHEMA, DEFAULT_SCHEMA)): str,
        vol.Required(CONF_PORT, description=get_vol_descr(config, CONF_PORT, DEFAULT_PORT)): int,
        vol.Optional(CONF_CERTIFICATE, description=get_vol_descr(config, CONF_CERTIFICATE, DEFAULT_CERTIFICATE)): str,
    }
    return schema

def get_schema_options_init(config: dict = {}) -> dict:
    """Return a shcema configuration dict for HACS."""
    schema = get_schema_config_user(config=config)
    schema.pop(CONF_TITLE, "")
    return schema

def get_schema_options_two(config: dict = {}) -> dict:
    """Return a shcema configuration dict for HACS."""
    config = config or {}
    config = config if CONF_TIMEOUT in config else None
    domains = sorted(PLATFORMS)
    schema = {
        vol.Required(CONF_TIMEOUT, description=get_vol_descr(config, CONF_TIMEOUT, DEFAULT_TIMEOUT)): int,
        vol.Optional(CONF_GLOBAL_CHANNEL_ID, description=get_vol_descr(config, CONF_GLOBAL_CHANNEL_ID)): int,
        vol.Optional(CONF_IGNORE_PLATFORM, description=get_vol_descr(config, CONF_IGNORE_PLATFORM)): cv.multi_select(domains),
        vol.Optional(CONF_USE_VIMAR_NAMING, description=get_vol_descr(config, CONF_USE_VIMAR_NAMING)): bool,
        vol.Optional(CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN, description=get_vol_descr(config, CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN)): bool,
        vol.Optional(CONF_DEVICES_LIGHTS_RE, description=get_vol_descr(config, CONF_DEVICES_LIGHTS_RE)): str,
        vol.Optional(CONF_DELETE_AND_RELOAD_ALL_ENTITIES): bool,
    }
    return schema