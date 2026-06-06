from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_AUTH_TOKEN,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DOMAIN,
)
from .http_api import GroundControlServer

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not entry.unique_id:
        hass.config_entries.async_update_entry(entry, unique_id=DOMAIN)

    options = {**entry.data, **entry.options}
    host = options.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST)
    port = options.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT)
    auth_token = options.get(CONF_AUTH_TOKEN)

    server = GroundControlServer(hass, host, port, auth_token)
    try:
        await server.start()
    except Exception as err:
        _LOGGER.error(
            "Failed to start HA GroundControl MCP server on %s:%s: %s",
            host,
            port,
            err,
        )
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = server
    _LOGGER.info("Started HA GroundControl MCP server on %s:%s", host, port)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    server = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if server:
        await server.stop()
    return True
