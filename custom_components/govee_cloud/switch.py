"""Switch platform for Govee Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GoveeConfigEntry
from .entity import GoveeBaseEntity
from .api import GoveeApiError

LIGHT_MARKER_INSTANCES = {
    "brightness",
    "colorRgb",
    "colorTemperatureK",
    "lightScene",
    "segmentedColorRgb",
    "segmentedBrightness",
    "online",
    "workMode",
}

LIGHT_CAPABILITY_TYPES = {
    "devices.capabilities.on_off",
    "devices.capabilities.range",
    "devices.capabilities.color_setting",
    "devices.capabilities.dynamic_scene",
    "devices.capabilities.mode",
    "devices.capabilities.work_mode",
}


def _has_cap(device: dict[str, Any], instance: str) -> bool:
    return any(cap.get("instance") == instance for cap in device.get("capabilities", []))


def _cap_by_instance(device: dict[str, Any], instance: str) -> dict[str, Any] | None:
    for cap in device.get("capabilities", []):
        if cap.get("instance") == instance:
            return cap
    return None


def _is_light(device: dict[str, Any]) -> bool:
    capabilities = device.get("capabilities", [])
    if any(cap.get("instance") in LIGHT_MARKER_INSTANCES for cap in capabilities):
        return True
    if _has_cap(device, "powerSwitch") and any(
        cap.get("type") in LIGHT_CAPABILITY_TYPES for cap in capabilities
    ):
        return True
    return False


def _switch_instances(device: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    # Non-light devices still get a main power switch entity.
    if _has_cap(device, "powerSwitch") and not _is_light(device):
        cap = _cap_by_instance(device, "powerSwitch")
        if cap and cap.get("type") in {
            "devices.capabilities.on_off",
            "devices.capabilities.toggle",
        }:
            out.append((cap["type"], "powerSwitch"))

    return out


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
            for cap_type, instance in _switch_instances(data.info):
                key = (dev_id, instance)
                if key in known:
                    continue
                known.add(key)
                entities.append(GoveeCapabilitySwitch(entry, dev_id, cap_type, instance))

        if entities:
            async_add_entities(entities)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class GoveeCapabilitySwitch(GoveeBaseEntity, SwitchEntity):
    """Representation of a boolean capability as a switch."""

    _attr_should_poll = False

    def __init__(self, entry: GoveeConfigEntry, device_id: str, cap_type: str, instance: str) -> None:
        super().__init__(entry, device_id)
        self._cap_type = cap_type
        self._instance = instance
        self._attr_unique_id = f"{device_id}_{instance}"

    @property
    def name(self) -> str:
        if self._instance == "powerSwitch":
            return "Power"
        return self._instance

    @property
    def is_on(self):
        value = self._get_value(self._instance)
        return self._is_on_value(value)

    async def async_turn_on(self, **kwargs):
        capability = _cap_by_instance(self._device, self._instance)
        last_error: GoveeApiError | None = None
        for candidate in self._power_value_candidates(capability, True):
            try:
                await self._entry.runtime_data.client.async_control(
                    self._device["sku"],
                    self._device_id,
                    self._cap_type,
                    self._instance,
                    candidate,
                )
                self._set_value(self._instance, candidate)
                last_error = None
                break
            except GoveeApiError as err:
                last_error = err
        if last_error is not None:
            raise last_error
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        capability = _cap_by_instance(self._device, self._instance)
        last_error: GoveeApiError | None = None
        for candidate in self._power_value_candidates(capability, False):
            try:
                await self._entry.runtime_data.client.async_control(
                    self._device["sku"],
                    self._device_id,
                    self._cap_type,
                    self._instance,
                    candidate,
                )
                self._set_value(self._instance, candidate)
                last_error = None
                break
            except GoveeApiError as err:
                last_error = err
        if last_error is not None:
            raise last_error
        self.async_write_ha_state()
