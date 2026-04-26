"""Select platform for Govee Cloud."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GoveeConfigEntry
from .entity import GoveeBaseEntity

SELECT_CAP_TYPES = {
    "devices.capabilities.mode",
    "devices.capabilities.dynamic_scene",
    "devices.capabilities.work_mode",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoveeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    known: set[tuple[str, str]] = set()

    def _add_new() -> None:
        entities = []

        for dev_id, data in coordinator.data.items():
            for cap in data.info.get("capabilities", []):
                if cap.get("type") not in SELECT_CAP_TYPES:
                    continue
                options = cap.get("parameters", {}).get("options", [])
                if not options:
                    continue

                instance = cap.get("instance")
                if not instance:
                    continue

                key = (dev_id, instance)
                if key in known:
                    continue

                known.add(key)
                entities.append(GoveeOptionSelect(entry, dev_id, cap))

        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class GoveeOptionSelect(GoveeBaseEntity, SelectEntity):
    """Enum-based capability exposed as a select."""

    _attr_should_poll = False

    def __init__(self, entry: GoveeConfigEntry, device_id: str, capability: dict) -> None:
        super().__init__(entry, device_id)
        self._capability = capability
        self._cap_type = capability["type"]
        self._instance = capability["instance"]
        self._options_map = {
            str(opt["name"]): opt["value"]
            for opt in capability.get("parameters", {}).get("options", [])
        }
        self._reverse_map = {value: name for name, value in self._options_map.items()}
        self._attr_unique_id = f"{device_id}_{self._instance}"
        self._attr_options = list(self._options_map.keys())

    @property
    def name(self) -> str:
        return self._instance

    @property
    def current_option(self) -> str | None:
        value = self._get_value(self._instance)
        return self._reverse_map.get(value)

    async def async_select_option(self, option: str) -> None:
        value = self._options_map[option]
        await self._entry.runtime_data.client.async_control(
            self._device["sku"],
            self._device_id,
            self._cap_type,
            self._instance,
            value,
        )
        self._set_value(self._instance, value)
        self.async_write_ha_state()
