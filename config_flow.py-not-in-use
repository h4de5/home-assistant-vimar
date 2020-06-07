"""Config flow for Vimar component."""

# see: https://developers.home-assistant.io/docs/data_entry_flow_index
# search for: config_flow: https://github.com/home-assistant/core/find/dev
from homeassistant import config_entries

from .const import DOMAIN


@config_entries.HANDLERS.register(DOMAIN)
class VimarFlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_setup(self, user_input):
        """Import a config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data=user_input)
