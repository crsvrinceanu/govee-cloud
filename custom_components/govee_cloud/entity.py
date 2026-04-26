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

    @staticmethod
    def _is_on_value(value: Any) -> bool | None:
        """Normalize on/off values coming from Govee."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "on", "true", "opened", "open", "enable", "enabled"}:
                return True
            if normalized in {"0", "off", "false", "closed", "close", "disable", "disabled"}:
                return False
        return None

    @staticmethod
    def _power_value_candidates(capability: dict[str, Any] | None, turn_on: bool) -> list[Any]:
        """Build likely accepted payloads for power-like capabilities."""
        candidates: list[Any] = []

        options = (capability or {}).get("parameters", {}).get("options", [])
        positive_words = {"on", "true", "enable", "enabled", "open", "opened", "start"}
        negative_words = {"off", "false", "disable", "disabled", "close", "closed", "stop"}

        for option in options:
            name = str(option.get("name", "")).strip().lower()
            value = option.get("value")
            if turn_on and any(word in name for word in positive_words):
                candidates.append(value)
            if not turn_on and any(word in name for word in negative_words):
                candidates.append(value)

        if turn_on:
            candidates.extend([1, True, "1", "on", "ON", "true", "enabled"])
        else:
            candidates.extend([0, False, "0", "off", "OFF", "false", "disabled"])

        unique: list[Any] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return unique
