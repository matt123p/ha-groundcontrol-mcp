This is a brilliant architectural constraint. By completely isolating the **configuration/schema** from the **live data/state**, you drastically reduce the context window size, improve the LLM's focus, and eliminate privacy or security concerns about the LLM knowing whether you are home or what your bedroom camera is doing.

To make this the ultimate vibe-coding companion, your MCP server needs to act as a "Schema Mapper." It needs to expose the exact structure of your Home Assistant (HA) instance so the LLM can perfectly map hardware buttons, screens, and microcontrollers to your specific setup.

Here is the comprehensive feature set and tool design your MCP server should expose.

---

### **1. The Core Registry Tools**

Home Assistant is built on "Registries" (static databases of what exists, regardless of current state). Your MCP server should expose these directly via HA’s WebSocket API or REST API.

#### **`get_areas`**

* **Purpose:** Allows the LLM to understand the physical layout of the house so it can group code properly (e.g., "Write an ESPHome config for a new multi-sensor in the Living Room").
* **Input Parameters:** None (or optional `search_string`).
* **Exposed Data:** * `area_id` (The internal ID needed for code, e.g., `living_room`)
* `name` (The friendly name, e.g., "Living Room")



#### **`get_entities`**

* **Purpose:** The absolute most critical tool. If the user says "Make a button to toggle the kitchen lights," the LLM needs to know the exact `entity_id`.
* **Input Parameters:** `domain` (optional, e.g., `light`, `switch`), `area_id` (optional).
* **Exposed Data:**
* `entity_id` (e.g., `light.kitchen_overhead`)
* `original_name` (e.g., "Kitchen Overhead Light")
* `platform` (e.g., `hue`, `esphome`, `zha` — useful so the LLM knows what system it’s talking to)
* `device_class` (e.g., `temperature`, `motion` — critical for the LLM to choose the right ESPHome sensor type or OpenHASP icon)
* *Strict Exclusion:* Do **not** return the `state` or live `attributes` objects.



#### **`get_devices`**

* **Purpose:** To understand the hardware tree. Devices group entities together.
* **Input Parameters:** `area_id` (optional), `manufacturer` (optional).
* **Exposed Data:**
* `device_id`
* `name`
* `manufacturer` & `model` (e.g., "IKEA of Sweden", "TRADFRI bulb") — This helps the LLM understand the capabilities of the target device.



---

### **2. The Action & Automation Tools**

To write satellite code that *does* things, the LLM needs to know what actions are legally allowed by your HA instance.

#### **`get_services` (or `get_actions`)**

* **Purpose:** Exposes the schema for how to trigger things in HA. If the LLM is writing an ESPHome `api.services` block, it needs to know the required parameters.
* **Input Parameters:** `domain` (e.g., `light`).
* **Exposed Data:**
* Service names (e.g., `turn_on`, `turn_off`, `toggle`)
* **Fields Schema:** What arguments does this service take? (e.g., `brightness` [0-255], `rgb_color` [Array of 3 ints], `transition` [float]).



#### **`get_event_types`**

* **Purpose:** For devices that trigger custom events (like an ESPHome remote control firing a `esphome.button_pressed` event), the LLM needs to know what events already exist in the system to avoid conflicts or to hook into existing automations.
* **Input Parameters:** None.
* **Exposed Data:** A list of custom event strings registered in HA.

---

### **3. The Vibe-Coding Helper Tools**

Since this is specifically for generating satellite code, you can add tools that bridge HA data with the target firmware context.

#### **`search_configuration`**

* **Purpose:** A fuzzy-search tool. Vibe-coding requests are often vague ("Link it to my 3D printer plug"). The LLM can use this tool to pass the string "3D printer" and get back matching areas, devices, or entities without knowing the exact domain.
* **Input Parameters:** `query` (string).
* **Exposed Data:** A mixed array of the top 5 matching entities/areas based on name matching.

#### **`get_esphome_secrets_keys`**

* **Purpose:** Good security practice. When generating ESPHome YAML, the LLM shouldn't hardcode Wi-Fi passwords.
* **Input Parameters:** None.
* **Exposed Data:** Only the *keys* (not the values) from the user's `secrets.yaml` (e.g., `wifi_ssid`, `wifi_password`, `mqtt_username`). The LLM can then inject `!secret wifi_ssid` into the generated code accurately.

---

### **How the Vibe-Coding Loop Works**

If you set it up this way, here is exactly how the LLM will behave when you prompt: *"Build me an OpenHASP config for a screen on my desk. It needs to control the desk lamp and show the temperature of the office."*

1. **LLM calls `search_configuration("desk lamp")**` -> Discovers `light.office_desk_lamp`.
2. **LLM calls `get_entities(domain="sensor", area_id="office")**` -> Discovers `sensor.office_multisensor_temperature`.
3. **LLM calls `get_services(domain="light")**` -> Verifies that `light.toggle` is a valid service for the OpenHASP button tap action.
4. **LLM generates the perfect JSONL code**, natively mapped to your exact Home Assistant environment, without ever knowing that your desk lamp is currently turned off or what the actual temperature is.

