from __future__ import annotations

import asyncio
import json
import logging
import uuid
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_runner import AppRunner, TCPSite
from homeassistant.core import HomeAssistant

from .const import API_BASE_PATH, INTEGRATION_VERSION
from .helpers import (
    async_get_areas,
    async_get_devices,
    async_get_esphome_secrets_keys,
    async_get_entities,
    async_get_event_types,
    async_get_people,
    async_get_services,
    async_search_configuration,
)

_LOGGER = logging.getLogger(__name__)


class GroundControlServer:
    def __init__(self, hass: HomeAssistant, host: str, port: int, auth_token: str | None = None) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.app = web.Application()
        self.connections: dict[str, web.StreamResponse] = {}

        # MCP SSE Endpoints
        self.app.router.add_get(API_BASE_PATH, self.handle_sse)
        self.app.router.add_get(f"{API_BASE_PATH}/", self.handle_sse)
        self.app.router.add_get(f"{API_BASE_PATH}/sse", self.handle_sse)
        self.app.router.add_post(f"{API_BASE_PATH}/messages", self.handle_post_message)

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

    def _is_authorized(self, request: Request) -> bool:
        if not self.auth_token:
            return True
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False
        token = auth_header.split(" ", 1)[1].strip()
        return token == self.auth_token

    async def handle_sse(self, request: Request) -> web.StreamResponse:
        if not self._is_authorized(request):
            return web.Response(text="Unauthorized", status=401)

        session_id = uuid.uuid4().hex
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        await response.prepare(request)

        # Send the client endpoint details where it should POST JSON-RPC payloads
        post_endpoint = f"{API_BASE_PATH}/messages?session_id={session_id}"
        await response.write(f"event: endpoint\ndata: {post_endpoint}\n\n".encode())

        self.connections[session_id] = response
        _LOGGER.debug("MCP client connected: session_id=%s", session_id)

        try:
            while True:
                await asyncio.sleep(30)
                await response.write(b": keep-alive\n\n")
        except asyncio.CancelledError:
            pass
        finally:
            self.connections.pop(session_id, None)
            _LOGGER.debug("MCP client disconnected: session_id=%s", session_id)

        return response

    async def handle_post_message(self, request: Request) -> web.Response:
        if not self._is_authorized(request):
            return web.Response(text="Unauthorized", status=401)

        session_id = request.query.get("session_id")
        if not session_id or session_id not in self.connections:
            return web.Response(text="Session not found", status=400)

        try:
            body = await request.json()
        except Exception:
            return web.Response(text="Invalid JSON", status=400)

        # Process standard JSON-RPC 2.0 payload asynchronously to not block message ingestion
        asyncio.create_task(self.process_json_rpc(session_id, body))

        return web.Response(text="Accepted", status=202)

    async def process_json_rpc(self, session_id: str, payload: dict) -> None:
        conn = self.connections.get(session_id)
        if not conn:
            return

        method = payload.get("method")
        msg_id = payload.get("id")

        def make_response(result: dict | list | None = None, error: dict | None = None) -> dict:
            resp = {"jsonrpc": "2.0"}
            if msg_id is not None:
                resp["id"] = msg_id
            if error is not None:
                resp["error"] = error
            else:
                resp["result"] = result
            return resp

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "HA GroundControl MCP",
                        "version": INTEGRATION_VERSION,
                    }
                }
                await self.send_to_sse(conn, make_response(result=result))

            elif method == "notifications/initialized":
                pass

            elif method == "tools/list":
                tools = [
                    {
                        "name": "get_areas",
                        "description": (
                            "Allows understanding the physical layout of the house so you can group code properly. "
                            "Returns a list of areas with area_id and name."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "search_string": {
                                    "type": "string",
                                    "description": "Optional query to search areas by name."
                                }
                            }
                        }
                    },
                    {
                        "name": "get_entities",
                        "description": (
                            "Retrieve entity registry metadata without live state. "
                            "Extremely critical to get the exact entity_id."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "Optional filter by domain (e.g. light, switch)."
                                },
                                "area_id": {
                                    "type": "string",
                                    "description": "Optional filter by area ID."
                                }
                            }
                        }
                    },
                    {
                        "name": "get_devices",
                        "description": (
                            "Retrieve device registry metadata to understand the hardware tree. "
                            "Devices group entities together."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "area_id": {
                                    "type": "string",
                                    "description": "Optional filter by area ID."
                                },
                                "manufacturer": {
                                    "type": "string",
                                    "description": "Optional filter by manufacturer."
                                }
                            }
                        }
                    },
                    {
                        "name": "get_people",
                        "description": "Retrieve defined Home Assistant people entries.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "search_string": {
                                    "type": "string",
                                    "description": "Optional filter by name or ID."
                                }
                            }
                        }
                    },
                    {
                        "name": "get_services",
                        "description": (
                            "Exposes the schema for how to trigger things in Home Assistant (e.g. toggle, turn_on, etc.)."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "Optional filter by domain (e.g. light)."
                                }
                            }
                        }
                    },
                    {
                        "name": "get_event_types",
                        "description": "List registered custom event types from the Home Assistant event bus.",
                        "inputSchema": {
                            "type": "object"
                        }
                    },
                    {
                        "name": "search_configuration",
                        "description": (
                            "Fuzzy-search tool. Pass a search query and get back matching areas, devices, people, and entities."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The fuzzy search query (e.g. 'printer', 'living room')."
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "get_esphome_secrets_keys",
                        "description": (
                            "Expose keys (without values) from the user's secrets.yaml. "
                            "Useful to avoid hardcoding secrets in generated YAML configs."
                        ),
                        "inputSchema": {
                            "type": "object"
                        }
                    }
                ]
                await self.send_to_sse(conn, make_response(result={"tools": tools}))

            elif method == "tools/call":
                params = payload.get("params", {})
                name = params.get("name")
                arguments = params.get("arguments", {})

                tool_result = await self.call_mcp_tool(name, arguments)
                await self.send_to_sse(conn, make_response(result=tool_result))

            else:
                error = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
                await self.send_to_sse(conn, make_response(error=error))

        except Exception as e:
            _LOGGER.exception("Error processing MCP JSON-RPC payload")
            error = {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
            await self.send_to_sse(conn, make_response(error=error))

    async def call_mcp_tool(self, name: str, arguments: dict) -> dict:
        try:
            if name == "get_areas":
                data = await async_get_areas(self.hass, arguments.get("search_string"))
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "get_entities":
                data = await async_get_entities(
                    self.hass,
                    domain=arguments.get("domain"),
                    area_id=arguments.get("area_id")
                )
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "get_devices":
                data = await async_get_devices(
                    self.hass,
                    area_id=arguments.get("area_id"),
                    manufacturer=arguments.get("manufacturer")
                )
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "get_people":
                data = await async_get_people(
                    self.hass,
                    search_string=arguments.get("search_string")
                )
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "get_services":
                data = await async_get_services(
                    self.hass,
                    domain=arguments.get("domain")
                )
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "get_event_types":
                data = await async_get_event_types(self.hass)
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "search_configuration":
                query = arguments.get("query")
                if not query:
                    return {
                        "content": [{"type": "text", "text": "Error: Missing required argument 'query'"}],
                        "isError": True
                    }
                data = await async_search_configuration(self.hass, query)
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            elif name == "get_esphome_secrets_keys":
                data = await async_get_esphome_secrets_keys(self.hass)
                return {"content": [{"type": "text", "text": json.dumps(data)}]}

            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                    "isError": True
                }
        except Exception as err:
            _LOGGER.exception("Error calling tool %s", name)
            return {
                "content": [{"type": "text", "text": f"Error calling tool {name}: {str(err)}"}],
                "isError": True
            }

    async def send_to_sse(self, conn: web.StreamResponse, data: dict) -> None:
        payload_str = json.dumps(data)
        await conn.write(f"data: {payload_str}\n\n".encode())
