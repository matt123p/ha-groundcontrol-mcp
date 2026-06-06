import asyncio
from unittest.mock import MagicMock
from custom_components.ha_groundcontrol.http_api import GroundControlServer

def test_mcp_tool_execution() -> None:
    # Mock HomeAssistant
    hass = MagicMock()
    
    server = GroundControlServer(hass, "127.0.0.1", 8210)
    
    # Run the async tool execution synchronously via asyncio.run
    res = asyncio.run(server.call_mcp_tool("unknown_tool", {}))
    assert "Unknown tool" in res["content"][0]["text"]
    assert res.get("isError") is True
