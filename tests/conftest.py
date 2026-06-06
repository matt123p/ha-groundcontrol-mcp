import sys
from unittest.mock import MagicMock

# Create mock homeassistant module tree
ha = MagicMock()
ha.core = MagicMock()
ha.config_entries = MagicMock()
ha.helpers = MagicMock()
ha.helpers.area_registry = MagicMock()
ha.helpers.device_registry = MagicMock()
ha.helpers.entity_registry = MagicMock()
ha.helpers.person = MagicMock()
ha.helpers.person_registry = MagicMock()

# Inject into sys.modules
sys.modules["homeassistant"] = ha
sys.modules["homeassistant.core"] = ha.core
sys.modules["homeassistant.config_entries"] = ha.config_entries
sys.modules["homeassistant.helpers"] = ha.helpers
sys.modules["homeassistant.helpers.area_registry"] = ha.helpers.area_registry
sys.modules["homeassistant.helpers.device_registry"] = ha.helpers.device_registry
sys.modules["homeassistant.helpers.entity_registry"] = ha.helpers.entity_registry
sys.modules["homeassistant.helpers.person"] = ha.helpers.person
sys.modules["homeassistant.helpers.person_registry"] = ha.helpers.person_registry
