"""Base entities for Govee Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoveeConfigEntry
from .coordinator import GoveeCoordinator


class GoveeBaseEntity(CoordinatorEntity[GoveeCoordinator]):
    """Base class for Govee entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: GoveeConfigEntry, device_id: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._device_id = device_id
        self._device = self.coordinator.data[device_id].info
        self._attr_available = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("govee_cloud", self._device_id)},
            manufacturer="Govee",
            model=self._device.get("sku"),
            name=self._device.get("deviceName") or self._device_id,
        )

    def _get_value(self, instance: str) -> Any | None:
        return self.coordinator.get_capability_value(self._device_id, instance)

    def _set_value(self, instance: str, value: Any) -> None:
        self.coordinator.set_capability_value(self._device_id, instance, value)
