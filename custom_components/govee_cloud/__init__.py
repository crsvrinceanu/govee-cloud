"""The Govee Cloud integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GoveeClient
from .coordinator import GoveeCoordinator
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS


@dataclass
class GoveeRuntimeData:
    """Runtime data for a config entry."""

    client: GoveeClient
    coordinator: GoveeCoordinator


GoveeConfigEntry = ConfigEntry[GoveeRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GoveeConfigEntry) -> bool:
    """Set up Govee Cloud from a config entry."""
    session = async_get_clientsession(hass)
    client = GoveeClient(entry.data[CONF_API_KEY], session)
    coordinator = GoveeCoordinator(
        hass,
        client,
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = GoveeRuntimeData(
        client=client,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GoveeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
