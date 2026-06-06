from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_AUTH_TOKEN,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DOMAIN,
)


class GroundControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_LISTEN_HOST, default=DEFAULT_LISTEN_HOST): str,
                        vol.Optional(CONF_LISTEN_PORT, default=DEFAULT_LISTEN_PORT): int,
                        vol.Optional(CONF_AUTH_TOKEN, default=""): str,
                    }
                ),
            )

        return self.async_create_entry(title="HA GroundControl", data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GroundControlOptionsFlowHandler(config_entry)


class GroundControlOptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)

    async def async_step_init(self, user_input=None):
        if user_input is None:
            current_options = {
                CONF_LISTEN_HOST: self.config_entry.options.get(
                    CONF_LISTEN_HOST,
                    self.config_entry.data.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST),
                ),
                CONF_LISTEN_PORT: self.config_entry.options.get(
                    CONF_LISTEN_PORT,
                    self.config_entry.data.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT),
                ),
                CONF_AUTH_TOKEN: self.config_entry.options.get(
                    CONF_AUTH_TOKEN,
                    self.config_entry.data.get(CONF_AUTH_TOKEN, ""),
                ),
            }
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_LISTEN_HOST, default=current_options[CONF_LISTEN_HOST]): str,
                        vol.Optional(CONF_LISTEN_PORT, default=current_options[CONF_LISTEN_PORT]): int,
                        vol.Optional(CONF_AUTH_TOKEN, default=current_options[CONF_AUTH_TOKEN]): str,
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)
