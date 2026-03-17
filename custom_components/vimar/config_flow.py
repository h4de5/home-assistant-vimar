"""Config flow for the Vimar Security System component."""

import re

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.config_entries import ConfigFlowResult as FlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
from homeassistant.util import slugify

from .const import (
    _LOGGER,
    CONF_CERTIFICATE,
    CONF_COVER_POSITION_MODE,
    CONF_DELETE_AND_RELOAD_ALL_ENTITIES,
    CONF_DEVICES_BINARY_SENSOR_RE,
    CONF_DEVICES_LIGHTS_RE,
    CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN,
    CONF_GLOBAL_CHANNEL_ID,
    CONF_IGNORE_PLATFORM,
    CONF_OVERRIDE,
    CONF_SAI_PIN,
    CONF_SCHEMA,
    CONF_SECURE,
    CONF_TITLE,
    CONF_USE_VIMAR_NAMING,
    COVER_POSITION_MODES,
    DEFAULT_CERTIFICATE,
    DEFAULT_COVER_POSITION_MODE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SECURE,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .vimar_coordinator import VimarDataUpdateCoordinator


class VimarFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vimar."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self.reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        schema = get_schema_config_user(user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            title = (
                user_input.pop(CONF_TITLE, "")
                or user_input.get(CONF_HOST)
                or user_input.get(CONF_USERNAME)
            )
            unique_id = slugify(title)
            try:
                coordinator = VimarDataUpdateCoordinator(
                    self.hass, entry=None, vimarconfig=user_input
                )
                await coordinator.validate_vimar_credentials()
            except Exception as ex:
                set_errors_from_ex(ex, errors)

            if not errors:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Handle re-authentication when credentials become invalid.
        
        This flow is triggered automatically when:
        - Login fails with invalid credentials
        - Session expires and cannot be renewed
        - Certificate validation fails
        """
        self.reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> FlowResult:
        """Confirm re-authentication and update credentials."""
        errors: dict[str, str] = {}
        
        if self.reauth_entry is None:
            return self.async_abort(reason="reauth_failed")

        if user_input is not None:
            # Merge existing config with new credentials
            new_config = {**self.reauth_entry.data, **user_input}
            
            try:
                coordinator = VimarDataUpdateCoordinator(
                    self.hass, entry=None, vimarconfig=new_config
                )
                await coordinator.validate_vimar_credentials()
            except Exception as ex:
                set_errors_from_ex(ex, errors)
            
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.reauth_entry,
                    data=new_config,
                )
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        # Show form with only credentials that might have changed
        schema = vol.Schema({
            vol.Required(
                CONF_USERNAME,
                default=self.reauth_entry.data.get(CONF_USERNAME)
            ): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "host": self.reauth_entry.data.get(CONF_HOST, "unknown"),
            },
        )

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        _LOGGER.info("VIMAR async_step_import")
        if self._async_current_entries():
            _LOGGER.warning("Only one configuration of Vimar is allowed.")
            return self.async_abort(reason="single_instance_allowed")
        user_input = import_config.copy()
        title = (
            user_input.pop(CONF_TITLE, "")
            or user_input.get(CONF_HOST)
            or user_input.get(CONF_USERNAME)
        )
        user_input.pop(CONF_OVERRIDE, "")  # remove override non gestito da config_flow
        schema = user_input.pop(CONF_SCHEMA, "https")
        user_input[CONF_SECURE] = schema == "https"
        if schema == "https" and user_input.get(CONF_CERTIFICATE, "") != "":
            user_input[CONF_VERIFY_SSL] = True
        unique_id = slugify(title)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the Home Assistant remote integration."""

    def __init__(self):
        """Initialize remote_homeassistant options flow."""
        self.options: dict = {}
        self.schema: dict = {}
        self.schema_vol: vol.Schema | None = None
        self.errors: dict[str, str] = {}
        self.user_input: dict = {}
        self.options_with_user_input: dict = {}

    def _ensure_options_initialized(self):
        """Initialize options from config_entry if not already done."""
        if not self.options:
            self.options.update(self.config_entry.data or {})
            self.options.update(self.config_entry.options or {})

    def _init_schema(self, user_input, schema):
        self.schema = schema
        self.schema_vol = vol.Schema(schema)
        self.errors: dict[str, str] = {}
        self.user_input = user_input
        self.options_with_user_input = self.options.copy()
        if user_input:
            self._dict_update(self.options_with_user_input)

    def _option_changed(self, key):
        original = self.config_entry.data.get(key, self.config_entry.options.get(key, ""))
        new = self.options.get(key, "")
        return original != new

    def _validate_regex(self, key):
        search_regex = self.options_with_user_input.get(key, "")
        if search_regex:
            try:
                re.search(search_regex, "x", re.IGNORECASE)
            except Exception as err:
                _LOGGER.error(
                    "Error occurred in validate_regex. Key: '%s', Regex: '%s' - %s",
                    key,
                    search_regex,
                    str(err),
                )
                self.errors[key] = "regex_not_valid"

    def _options_update(self):
        self._dict_update(self.options)

    def _dict_update(self, options):
        for key in self.schema.keys():  # set all values in form, if not present remove it
            value = self.user_input.get(str(key))
            options[str(key)] = value
            if value is None:  # remove None value, problem to save in json!
                options.pop(str(key))

    def _async_show_form_step(self, step):
        return self.async_show_form(step_id=step, data_schema=self.schema_vol, errors=self.errors)

    def _async_save_options(self):
        self._options_update()
        self.hass.config_entries.async_update_entry(self.config_entry, data=self.options)
        return self.async_create_entry(title="", data={})

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        self._ensure_options_initialized()
        self._init_schema(user_input, get_schema_options_init(user_input or self.options))
        if user_input is not None:
            try:
                coordinator = VimarDataUpdateCoordinator(
                    self.hass, entry=self.config_entry, vimarconfig=self.options_with_user_input
                )
                await coordinator.validate_vimar_credentials()
            except Exception as ex:
                set_errors_from_ex(ex, self.errors)

        if user_input is not None and not self.errors:
            self._options_update()
            return await self.async_step_two()

        return self._async_show_form_step("init")

    async def async_step_two(self, user_input=None):
        """Manage domain and entity filters."""
        self._init_schema(user_input, get_schema_options_two(user_input or self.options))

        if user_input is not None:
            self._validate_regex(CONF_DEVICES_LIGHTS_RE)
            self._validate_regex(CONF_DEVICES_BINARY_SENSOR_RE)
        if user_input is not None and not self.errors:
            try:
                coordinator = VimarDataUpdateCoordinator(
                    self.hass, entry=self.config_entry, vimarconfig=self.options_with_user_input
                )
                await coordinator.validate_vimar_credentials()
                await self.hass.async_add_executor_job(coordinator.vimarproject.update, True)
            except Exception as ex:
                set_errors_from_ex(ex, self.errors)

        if user_input is not None and not self.errors:
            self._options_update()
            for key in [
                CONF_USE_VIMAR_NAMING,
                CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN,
                CONF_DEVICES_LIGHTS_RE,
                CONF_DEVICES_BINARY_SENSOR_RE,
            ]:
                if self._option_changed(key):
                    self.options[CONF_DELETE_AND_RELOAD_ALL_ENTITIES] = True
                    break
            return await self.async_step_three()

        return self._async_show_form_step("two")

    async def async_step_three(self, user_input=None):
        """Manage domain and entity filters."""
        self._init_schema(user_input, get_schema_options_three(user_input or self.options))

        if user_input is not None and not self.errors:
            return self._async_save_options()

        return self._async_show_form_step("three")


def set_errors_from_ex(ex: Exception, errors: dict[str, str]):
    """Map exceptions to user-friendly error messages."""
    exstr = str(ex)
    if "Log In Fallito" in exstr:  # message returned from vimar
        errors["base"] = "invalid_auth"
    elif (
        "HTTP error occurred" in exstr
        or "Client Error:" in exstr
        or "ConnectTimeoutError" in exstr
        or "NewConnectionError" in exstr
    ) or "HTTP timeout occurred" in exstr:
        errors["base"] = "cannot_connect"
    elif "SSLError" in exstr:
        errors["base"] = "invalid_cert"
    elif "Saving certificate failed" in exstr:
        errors["base"] = "save_cert_failed"
    else:
        _LOGGER.error("Unexpected error during validation: %s", exstr)
        errors["base"] = "unknown"


def get_vol_default(config: dict | None, key, default=None):
    if config:
        return config.get(key) or vol.UNDEFINED
    return default or vol.UNDEFINED


def get_vol_descr(config: dict | None, key, default=None):
    def_value = get_vol_default(config, key, default)
    res = ({"suggested_value": def_value}) if def_value and def_value is not vol.UNDEFINED else {}
    return res


def get_schema_config_user(config: dict | None = None) -> dict:
    """Return a shcema configuration dict for HACS."""
    config = config if config and CONF_HOST in config else None
    schema = {
        vol.Required(CONF_TITLE, description=get_vol_descr(config, CONF_TITLE)): str,
        vol.Required(CONF_HOST, description=get_vol_descr(config, CONF_HOST)): str,
        vol.Required(CONF_PORT, description=get_vol_descr(config, CONF_PORT, DEFAULT_PORT)): int,
        vol.Required(
            CONF_SECURE, description=get_vol_descr(config, CONF_SECURE, DEFAULT_SECURE)
        ): bool,
        vol.Required(
            CONF_VERIFY_SSL, description=get_vol_descr(config, CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        ): bool,
        vol.Required(CONF_USERNAME, description=get_vol_descr(config, CONF_USERNAME)): str,
        vol.Required(CONF_PASSWORD, description=get_vol_descr(config, CONF_PASSWORD)): str,
        vol.Optional(
            CONF_SAI_PIN,
            description=get_vol_descr(config, CONF_SAI_PIN),
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Optional(
            CONF_CERTIFICATE,
            description=get_vol_descr(config, CONF_CERTIFICATE, DEFAULT_CERTIFICATE),
        ): str,
    }
    return schema


def get_schema_options_init(config: dict | None = None) -> dict:
    """Return a shcema configuration dict for HACS."""
    schema = get_schema_config_user(config=config)
    schema.pop(CONF_TITLE, "")
    return schema


def get_schema_options_two(config: dict | None = None) -> dict:
    """Return a shcema configuration dict for HACS."""
    if config is None:
        config = {}
    config = config if CONF_TIMEOUT in config else None
    if config and not config.get(CONF_SCAN_INTERVAL):
        config[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
    domains = sorted(PLATFORMS)
    schema = {
        vol.Required(
            CONF_TIMEOUT, description=get_vol_descr(config, CONF_TIMEOUT, DEFAULT_TIMEOUT)
        ): int,
        vol.Required(
            CONF_SCAN_INTERVAL,
            description=get_vol_descr(config, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): int,
        vol.Optional(
            CONF_GLOBAL_CHANNEL_ID, description=get_vol_descr(config, CONF_GLOBAL_CHANNEL_ID)
        ): int,
        vol.Optional(
            CONF_IGNORE_PLATFORM, description=get_vol_descr(config, CONF_IGNORE_PLATFORM)
        ): cv.multi_select(domains),
        vol.Optional(
            CONF_COVER_POSITION_MODE,
            description=get_vol_descr(config, CONF_COVER_POSITION_MODE, DEFAULT_COVER_POSITION_MODE),
        ): vol.In(COVER_POSITION_MODES),
        vol.Optional(
            CONF_USE_VIMAR_NAMING, description=get_vol_descr(config, CONF_USE_VIMAR_NAMING)
        ): bool,
        vol.Optional(
            CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN,
            description=get_vol_descr(config, CONF_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN),
        ): bool,
        vol.Optional(
            CONF_DEVICES_LIGHTS_RE, description=get_vol_descr(config, CONF_DEVICES_LIGHTS_RE)
        ): str,
        vol.Optional(
            CONF_DEVICES_BINARY_SENSOR_RE,
            description=get_vol_descr(config, CONF_DEVICES_BINARY_SENSOR_RE),
        ): str,
    }
    return schema


def get_schema_options_three(config: dict | None = None) -> dict:
    """Return a shcema configuration dict for HACS."""
    schema = {
        vol.Optional(
            CONF_DELETE_AND_RELOAD_ALL_ENTITIES,
            description=get_vol_descr(config, CONF_DELETE_AND_RELOAD_ALL_ENTITIES),
        ): bool,
    }
    return schema
