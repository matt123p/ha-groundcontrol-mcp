from __future__ import annotations

import os
from typing import Any

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from .const import API_BASE_PATH, INTEGRATION_VERSION


async def async_get_areas(hass: HomeAssistant, search_string: str | None = None) -> list[dict[str, Any]]:
    area_registry = ar.async_get(hass)
    areas = [
        {
            "area_id": getattr(area, "id", getattr(area, "area_id", None)),
            "name": area.name,
        }
        for area in area_registry.async_list_areas()
    ]

    if search_string:
        query = search_string.lower()
        areas = [area for area in areas if query in (area["name"] or "").lower()]

    return areas


async def async_get_entities(
    hass: HomeAssistant,
    domain: str | None = None,
    area_id: str | None = None,
) -> list[dict[str, Any]]:
    entity_registry = er.async_get(hass)
    entities = []

    for entry in entity_registry.entities.values():
        entry_domain = entry.entity_id.split(".", 1)[0]
        if domain and entry_domain != domain:
            continue
        if area_id and entry.area_id != area_id:
            continue

        entities.append(
            {
                "entity_id": entry.entity_id,
                "original_name": entry.original_name or entry.name,
                "platform": entry.platform,
                "device_class": entry.device_class,
                "area_id": entry.area_id,
                "device_id": entry.device_id,
            }
        )

    return entities


async def async_get_devices(
    hass: HomeAssistant,
    area_id: str | None = None,
    manufacturer: str | None = None,
) -> list[dict[str, Any]]:
    device_registry = dr.async_get(hass)
    devices = []

    for device in device_registry.devices.values():
        if area_id and device.area_id != area_id:
            continue
        if manufacturer and device.manufacturer != manufacturer:
            continue

        devices.append(
            {
                "device_id": device.id,
                "name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "area_id": device.area_id,
            }
        )

    return devices


async def async_get_people(
    hass: HomeAssistant,
    search_string: str | None = None,
) -> list[dict[str, Any]]:
    import inspect
    people = []
    raw_persons = []

    # Method 1: Try using the internal person component storage collection in hass.data
    person_data = hass.data.get("person")
    if person_data:
        if hasattr(person_data, "async_items"):
            try:
                res = person_data.async_items()
                if inspect.isawaitable(res):
                    raw_persons = await res
                else:
                    raw_persons = res
            except Exception:
                pass
        elif hasattr(person_data, "items"):
            try:
                raw_persons = list(person_data.items())
            except Exception:
                pass

    # Method 2: Fallback to importing components.person or helpers.person dynamically
    if not raw_persons:
        person_mod = None
        try:
            from homeassistant.components import person as person_mod
        except ImportError:
            try:
                from homeassistant.helpers import person as person_mod
            except ImportError:
                pass

        if person_mod:
            try:
                if hasattr(person_mod, "async_get_registry"):
                    reg = await person_mod.async_get_registry(hass)
                elif hasattr(person_mod, "async_get"):
                    reg = person_mod.async_get(hass)
                    if inspect.isawaitable(reg):
                        reg = await reg
                else:
                    reg = None

                if reg:
                    persons_list = getattr(reg, "persons", None)
                    if persons_list is None:
                        persons_list = getattr(reg, "people", None)
                    if persons_list is None and hasattr(reg, "async_list_people"):
                        persons_list = reg.async_list_people()
                        if inspect.isawaitable(persons_list):
                            persons_list = await persons_list

                    if persons_list:
                        if isinstance(persons_list, dict):
                            raw_persons = list(persons_list.values())
                        else:
                            raw_persons = list(persons_list)
            except Exception:
                pass

    # Process extracted raw person items (from Method 1 or Method 2)
    if raw_persons:
        for entry in raw_persons:
            if isinstance(entry, dict):
                person_id = entry.get("id") or entry.get("person_id")
                name = entry.get("name")
                user_id = entry.get("user_id")
                area_id = entry.get("area_id")
                device_id = entry.get("device_id")
            else:
                person_id = getattr(entry, "id", None) or getattr(entry, "person_id", None)
                name = getattr(entry, "name", None)
                user_id = getattr(entry, "user_id", None)
                area_id = getattr(entry, "area_id", None)
                device_id = getattr(entry, "device_id", None)

            people.append(
                {
                    "person_id": person_id,
                    "name": name,
                    "user_id": user_id,
                    "area_id": area_id,
                    "device_id": device_id,
                }
            )

    # Method 3: Ultimate fallback using the Home Assistant State Machine
    if not people:
        try:
            states = hass.states.async_all("person")
            for state in states:
                people.append(
                    {
                        "person_id": state.entity_id.split(".", 1)[1],
                        "name": state.name,
                        "user_id": state.attributes.get("user_id"),
                        "area_id": None,
                        "device_id": None,
                    }
                )
        except Exception:
            pass

    if search_string:
        query = search_string.lower()
        people = [
            person
            for person in people
            if query in (person["name"] or "").lower()
            or query in (person["person_id"] or "").lower()
        ]

    return people


async def async_get_services(hass: HomeAssistant, domain: str | None = None) -> list[dict[str, Any]]:
    services = []
    service_map = hass.services.async_services()

    for service_domain, service_objects in service_map.items():
        if domain and service_domain != domain:
            continue

        for service_name, service_handler in service_objects.items():
            services.append(
                {
                    "domain": service_domain,
                    "service": service_name,
                    "fields": _extract_service_fields(service_handler),
                }
            )

    return services


def _extract_service_fields(service_handler: Any) -> list[dict[str, Any]]:
    schema = getattr(service_handler, "schema", None)
    if schema is None:
        return []

    if isinstance(schema, dict):
        return [
            {"name": str(key), "schema": repr(value)} for key, value in schema.items()
        ]

    return [{"name": "raw", "schema": repr(schema)}]


async def async_get_event_types(hass: HomeAssistant) -> list[str]:
    event_types = list(hass.bus.async_listeners().keys())
    return sorted(event_types)


async def async_search_configuration(hass: HomeAssistant, query: str) -> list[dict[str, Any]]:
    query_lower = query.lower()
    results: list[dict[str, Any]] = []

    areas = await async_get_areas(hass)
    for entry in areas:
        if query_lower in (entry["name"] or "").lower():
            results.append({"type": "area", "id": entry["area_id"], "name": entry["name"]})

    entities = await async_get_entities(hass)
    for entry in entities:
        if query_lower in (entry["original_name"] or "").lower() or query_lower in entry["entity_id"].lower():
            results.append({"type": "entity", "id": entry["entity_id"], "name": entry["original_name"]})

    devices = await async_get_devices(hass)
    for entry in devices:
        if query_lower in (entry["name"] or "").lower() or (entry["manufacturer"] and query_lower in entry["manufacturer"].lower()):
            results.append({"type": "device", "id": entry["device_id"], "name": entry["name"]})

    people = await async_get_people(hass)
    for entry in people:
        if query_lower in (entry["name"] or "").lower() or query_lower in (entry["person_id"] or "").lower():
            results.append({"type": "person", "id": entry["person_id"], "name": entry["name"]})

    return results[:5]


async def async_get_info(hass: HomeAssistant, host: str, port: int) -> dict[str, Any]:
    return {
        "service_name": "HA GroundControl MCP",
        "integration_version": INTEGRATION_VERSION,
        "description": (
            "A Home Assistant schema mapper that exposes static registry metadata to external agents "
            "and LLM-based assistants without returning live entity state or sensitive attribute data."
        ),
        "purpose": (
            "Provide exact Home Assistant areas, entities, devices, people, services, events, "
            "and secret key names so external tools can generate safe, context-aware automations and firmware."
        ),
        "when_to_use": [
            "When an external assistant needs the exact Home Assistant entity_id for a device.",
            "When a code generator needs Home Assistant service schema without live runtime state.",
            "When you need a schema-only mapping of areas, devices, people, and events.",
        ],
        "listen_host": host,
        "listen_port": port,
        "listen_help": "Use 0.0.0.0 to bind to all interfaces or a specific IP address for one interface.",
        "base_path": API_BASE_PATH,
        "endpoints": [
            {
                "name": "areas",
                "path": f"{API_BASE_PATH}/areas",
                "description": "List all Home Assistant areas.",
            },
            {
                "name": "entities",
                "path": f"{API_BASE_PATH}/entities",
                "description": "List entity registry metadata without live state.",
                "query_parameters": ["domain", "area_id"],
            },
            {
                "name": "devices",
                "path": f"{API_BASE_PATH}/devices",
                "description": "List device registry metadata.",
                "query_parameters": ["area_id", "manufacturer"],
            },
            {
                "name": "people",
                "path": f"{API_BASE_PATH}/people",
                "description": "List Home Assistant people entities.",
                "query_parameters": ["search_string"],
            },
            {
                "name": "services",
                "path": f"{API_BASE_PATH}/services",
                "description": "List Home Assistant services and best-effort schema for service fields.",
                "query_parameters": ["domain"],
            },
            {
                "name": "event_types",
                "path": f"{API_BASE_PATH}/event_types",
                "description": "List registered Home Assistant event types.",
            },
            {
                "name": "search",
                "path": f"{API_BASE_PATH}/search",
                "description": "Fuzzy search areas, entities, devices, and people by name.",
                "query_parameters": ["q"],
            },
            {
                "name": "secrets_keys",
                "path": f"{API_BASE_PATH}/secrets_keys",
                "description": "List secret key names from Home Assistant secrets.yaml.",
            },
        ],
    }


async def async_get_esphome_secrets_keys(hass: HomeAssistant) -> list[str]:
    secrets_path = hass.config.path("secrets.yaml")
    if not os.path.isfile(secrets_path):
        return []

    with open(secrets_path, encoding="utf-8") as fp:
        contents = yaml.safe_load(fp)

    if isinstance(contents, dict):
        return list(contents.keys())

    return []
