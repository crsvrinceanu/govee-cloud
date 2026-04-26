"""Sensor platform for Govee Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GoveeConfigEntry
from .entity import GoveeBaseEntity

PROPERTY_CAP_TYPE = "devices.capabilities.property"


def _friendly_unit(unit: str | None) -> str | None:
    if unit == "unit.percent":
        return PERCENTAGE
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
                if cap.get("type") != PROPERTY_CAP_TYPE:
                    continue

                instance = cap.get("instance")
                if not instance:
                    continue

                key = (dev_id, instance)
                if key in known:
                    continue

                known.add(key)
                entities.append(GoveePropertySensor(entry, dev_id, cap))

        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class GoveePropertySensor(GoveeBaseEntity, SensorEntity):
    """Representation of a read-only Govee property capability."""

    _attr_should_poll = False

    def __init__(self, entry: GoveeConfigEntry, device_id: str, capability: dict[str, Any]) -> None:
        super().__init__(entry, device_id)
        self._capability = capability
        self._instance = capability["instance"]
        self._attr_unique_id = f"{device_id}_{self._instance}"

        if self._instance == "sensorHumidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif self._instance == "sensorTemperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = _friendly_unit(
                capability.get("parameters", {}).get("unit")
            )
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_native_unit_of_measurement = _friendly_unit(
                capability.get("parameters", {}).get("unit")
            )

    @property
    def name(self) -> str:
        return self._instance

    @property
    def native_value(self) -> float | int | str | None:
        value = self._get_value(self._instance)
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return self._normalize_numeric_value(value)
        return str(value)

    def _normalize_numeric_value(self, value: int | float) -> float | int:
        """Scale raw sensor values when Govee reports fixed-point numbers."""
        if self._instance == "sensorTemperature" and abs(value) >= 1000:
            return round(value / 100, 2)
        if self._instance == "sensorHumidity" and value > 100:
            return round(value / 100, 2)
        return value
