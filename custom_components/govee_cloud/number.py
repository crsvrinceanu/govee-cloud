"""Number platform for Govee Cloud."""

from __future__ import annotations

from homeassistant.const import UnitOfTemperature
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GoveeConfigEntry
from .entity import GoveeBaseEntity

LIGHT_RANGE_INSTANCES = {"brightness"}
NUMBER_CAP_TYPES = {
    "devices.capabilities.range",
    "devices.capabilities.temperature_setting",
}


def _friendly_unit(unit: str | None) -> str | None:
    if unit == "unit.percent":
        return "%"
    if unit == "unit.celsius":
        return UnitOfTemperature.CELSIUS
    if unit == "unit.fahrenheit":
        return UnitOfTemperature.FAHRENHEIT
    return unit


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
                if cap.get("type") not in NUMBER_CAP_TYPES:
                    continue

                instance = cap.get("instance")
                if instance in LIGHT_RANGE_INSTANCES:
                    continue
                if not instance or "range" not in cap.get("parameters", {}):
                    continue

                key = (dev_id, instance)
                if key in known:
                    continue

                known.add(key)
                entities.append(GoveeRangeNumber(entry, dev_id, cap))

        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class GoveeRangeNumber(GoveeBaseEntity, NumberEntity):
    """Representation of a numeric Govee capability."""

    _attr_should_poll = False

    def __init__(self, entry: GoveeConfigEntry, device_id: str, capability: dict) -> None:
        super().__init__(entry, device_id)
        self._capability = capability
        self._instance = capability["instance"]
        self._attr_unique_id = f"{device_id}_{self._instance}"

        rng = capability["parameters"]["range"]
        self._attr_native_min_value = rng["min"]
        self._attr_native_max_value = rng["max"]
        self._attr_native_step = rng["precision"]
        self._attr_native_unit_of_measurement = _friendly_unit(
            capability["parameters"].get("unit")
        )

    @property
    def name(self):
        return self._instance

    @property
    def native_value(self):
        value = self._get_value(self._instance)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value)
        await self._entry.runtime_data.client.async_control(
            self._device["sku"],
            self._device_id,
            self._capability["type"],
            self._instance,
            int_value,
        )
        self._set_value(self._instance, int_value)
        self.async_write_ha_state()
