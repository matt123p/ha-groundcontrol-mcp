from __future__ import annotations

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_runner import AppRunner, TCPSite
from homeassistant.core import HomeAssistant

from .const import API_BASE_PATH
from .helpers import (
    async_get_areas,
    async_get_devices,
    async_get_esphome_secrets_keys,
    async_get_entities,
    async_get_event_types,
    async_get_info,
    async_get_people,
    async_get_services,
    async_search_configuration,
)


class GroundControlServer:
    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.router.add_get(API_BASE_PATH, self.handle_request)
        self.app.router.add_get(f"{API_BASE_PATH}/", self.handle_request)
        self.app.router.add_get(f"{API_BASE_PATH}/{{resource}}", self.handle_request)
        self.runner = AppRunner(self.app)
        self.site: TCPSite | None = None

    async def start(self) -> None:
        await self.runner.setup()
        self.site = TCPSite(self.runner, self.host, self.port)
        await self.site.start()

    async def stop(self) -> None:
        if self.site:
            await self.site.stop()
        await self.runner.cleanup()

    async def handle_request(self, request: Request) -> web.Response:
        resource = request.match_info.get("resource")

        if not resource:
            return web.json_response(await async_get_info(self.hass, self.host, self.port))

        if resource == "areas":
            return web.json_response(
                await async_get_areas(self.hass, request.query.get("search_string"))
            )

        if resource == "entities":
            return web.json_response(
                await async_get_entities(
                    self.hass,
                    domain=request.query.get("domain"),
                    area_id=request.query.get("area_id"),
                )
            )

        if resource == "devices":
            return web.json_response(
                await async_get_devices(
                    self.hass,
                    area_id=request.query.get("area_id"),
                    manufacturer=request.query.get("manufacturer"),
                )
            )

        if resource == "people":
            return web.json_response(
                await async_get_people(
                    self.hass,
                    search_string=request.query.get("search_string"),
                )
            )

        if resource == "services":
            return web.json_response(
                await async_get_services(self.hass, domain=request.query.get("domain"))
            )

        if resource == "event_types":
            return web.json_response(await async_get_event_types(self.hass))

        if resource == "search":
            query = request.query.get("q")
            if not query:
                return web.json_response(
                    {"error": "Missing required query parameter: q"},
                    status=400,
                )
            return web.json_response(await async_search_configuration(self.hass, query))

        if resource == "secrets_keys":
            return web.json_response(await async_get_esphome_secrets_keys(self.hass))

        return web.json_response(
            {"error": f"Unknown resource: {resource}"},
            status=404,
        )
