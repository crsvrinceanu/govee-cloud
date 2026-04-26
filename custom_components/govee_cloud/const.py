"""Constants for the Govee Cloud integration."""

from __future__ import annotations

DOMAIN = "govee_cloud"

CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15

API_BASE = "https://openapi.api.govee.com/router/api/v1"

PLATFORMS = ["light", "switch", "number", "select", "sensor"]
