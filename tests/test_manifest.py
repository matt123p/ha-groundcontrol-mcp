import json
from pathlib import Path


def test_root_hacs_manifest_exists() -> None:
    root_manifest = Path(__file__).parents[1] / "hacs.json"
    assert root_manifest.exists(), "Root HACS hacs.json is missing"

    payload = json.loads(root_manifest.read_text(encoding="utf-8"))
    assert payload["name"] == "HA GroundControl MCP"
    assert payload["content_in_root"] is False
    assert "domains" in payload


def test_integration_manifest_exists() -> None:
    integration_manifest = Path(__file__).parents[1] / "custom_components" / "ha_groundcontrol" / "manifest.json"
    assert integration_manifest.exists(), "Integration manifest.json is missing"

    payload = json.loads(integration_manifest.read_text(encoding="utf-8"))
    assert payload["domain"] == "ha_groundcontrol"
    assert payload["version"] == "0.1.3"
    assert payload["iot_class"] == "local_polling"
    assert payload["config_flow"] is True
