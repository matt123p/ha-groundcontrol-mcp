# HA GroundControl MCP

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


A Home Assistant custom integration and HACS-compatible repository that exposes schema-only Home Assistant registry tools through a dedicated MCP HTTP server.

## Features

- `get_areas` — enumerate Home Assistant areas
- `get_entities` — retrieve entity registry metadata without live state
- `get_devices` — retrieve device registry metadata
- `get_services` — list available service names and best-effort field schema
- `get_event_types` — list registered event types from the HA event bus
- `get_people` — retrieve defined Home Assistant people entries
- `search_configuration` — fuzzy search over areas, devices, people, and entities
- `get_esphome_secrets_keys` — list secret keys from `secrets.yaml`
- Integration options to configure the host and port the MCP HTTP server listens on

## Installation

If you already have HACS installed, click the badge below to add this repository automatically:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=matt123p&repository=ha-groundcontrol-mcp&category=integration)

Alternatively, add it manually:
1. Go to **HACS** -> **Custom repositories** (three dots in top-right).
2. Add `https://github.com/matt123p/ha-groundcontrol-mcp` as an **Integration** repository.
3. Download the **HA GroundControl MCP** integration and restart Home Assistant.

### Don't have HACS?
HACS (Home Assistant Community Store) is a custom component manager. To install HACS, refer to the [HACS Installation Guide](https://hacs.xyz/docs/setup/prerequisites).

## Configuration
1. Go to **Settings** -> **Devices & Services** -> **+ Add Integration**.
2. Search and select **HA GroundControl MCP** to set it up.


## Co-pilot / Antigravity Setup

1. Install the integration in Home Assistant and configure the MCP server host and port.
2. Verify the server is reachable, for example:
   - `http://<ha-host>:8210/ha_groundcontrol`
3. Create a Home Assistant long-lived access token:
   - Settings -> Users -> Long-Lived Access Tokens
4. Configure your assistant to use the MCP endpoint:
   - Base URL: `http://<ha-host>:<port>/ha_groundcontrol`
   - Authorization: `Bearer <long-lived-access-token>`
5. If your assistant supports custom MCP metadata, point it at the root endpoint so it can discover the service description and endpoints.

## API Endpoints

Once installed, the integration provides a dedicated MCP HTTP server at the configured host and port, with endpoints under `/ha_groundcontrol`.

### Examples

If the server is configured to listen on `0.0.0.0:8210`, the endpoints are:

- `GET http://<ha-host>:8210/ha_groundcontrol`
- `GET http://<ha-host>:8210/ha_groundcontrol/areas`
- `GET http://<ha-host>:8210/ha_groundcontrol/entities?domain=light&area_id=living_room`
- `GET http://<ha-host>:8210/ha_groundcontrol/devices?manufacturer=IKEA`
- `GET http://<ha-host>:8210/ha_groundcontrol/people?search_string=Matt`
- `GET http://<ha-host>:8210/ha_groundcontrol/services?domain=light`
- `GET http://<ha-host>:8210/ha_groundcontrol/event_types`
- `GET http://<ha-host>:8210/ha_groundcontrol/search?q=printer`
- `GET http://<ha-host>:8210/ha_groundcontrol/secrets_keys`

## HACS

This repository is HACS-compatible with a root `manifest.json` and a Home Assistant integration manifest in `custom_components/ha_groundcontrol/manifest.json`.
