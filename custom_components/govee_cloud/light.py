"""Light platform for Govee Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    LightEntityFeature,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GoveeConfigEntry
from .entity import GoveeBaseEntity


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
    if _has_cap(device, "powerSwitch"):
        return True
    if any(cap.get("instance") in LIGHT_MARKER_INSTANCES for cap in capabilities):
        return True
    if _has_cap(device, "powerSwitch") and any(
        cap.get("type") in LIGHT_CAPABILITY_TYPES for cap in capabilities
    ):
        return True
    return False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoveeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    def _add_new() -> None:
        current = {
            dev_id
            for dev_id, data in coordinator.data.items()
            if _is_light(data.info)
        }
        new_ids = current - known
        if new_ids:
            known.update(new_ids)
            async_add_entities([GoveeLight(entry, dev_id) for dev_id in new_ids])

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class GoveeLight(GoveeBaseEntity, LightEntity):
    """Representation of a Govee light."""

    _attr_should_poll = False

    def __init__(self, entry: GoveeConfigEntry, device_id: str) -> None:
        super().__init__(entry, device_id)
        self._attr_unique_id = f"{device_id}_light"
        if _has_cap(self._device, "lightScene"):
            self._attr_supported_features = LightEntityFeature.EFFECT
        else:
            self._attr_supported_features = LightEntityFeature(0)

    @property
    def name(self) -> str:
        return self._device.get("deviceName") or self._device_id

    @property
    def supported_color_modes(self):
        modes = set()
        if _has_cap(self._device, "colorRgb"):
            modes.add(ColorMode.RGB)
        if _has_cap(self._device, "colorTemperatureK"):
            modes.add(ColorMode.COLOR_TEMP)
        if not modes and _has_cap(self._device, "brightness"):
            modes.add(ColorMode.BRIGHTNESS)
        return modes or {ColorMode.ONOFF}

    @property
    def color_mode(self):
        supported = self.supported_color_modes
        if ColorMode.RGB in supported:
            return ColorMode.RGB
        if ColorMode.COLOR_TEMP in supported:
            return ColorMode.COLOR_TEMP
        if ColorMode.BRIGHTNESS in supported:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def is_on(self):
        value = self._get_value("powerSwitch")
        if value is None:
            return None
        return value == 1

    @property
    def brightness(self):
        value = self._get_value("brightness")
        if value is None:
            return None
        return round((int(value) / 100) * 255)

    @property
    def rgb_color(self):
        value = self._get_value("colorRgb")
        if value is None:
            return None
        value = int(value)
        return ((value >> 16) & 255, (value >> 8) & 255, value & 255)

    @property
    def color_temp_kelvin(self):
        value = self._get_value("colorTemperatureK")
        return int(value) if value is not None else None

    @property
    def effect_list(self):
        cap = _cap_by_instance(self._device, "lightScene")
        if cap:
            return [opt["name"] for opt in cap["parameters"].get("options", [])]
        return None

    @property
    def effect(self):
        current = self._get_value("lightScene")
        if current is None:
            return None
        scene_map = self.effect_map
        for name, value in scene_map.items():
            if value == current:
                return name
        return None

    @property
    def effect_map(self):
        cap = _cap_by_instance(self._device, "lightScene")
        if cap:
            return {
                opt["name"]: opt["value"]
                for opt in cap["parameters"].get("options", [])
            }
        return {}

    async def async_turn_on(self, **kwargs):
        client = self._entry.runtime_data.client
        sku = self._device["sku"]
        power_cap = _cap_by_instance(self._device, "powerSwitch")
        brightness_cap = _cap_by_instance(self._device, "brightness")
        rgb_cap = _cap_by_instance(self._device, "colorRgb")
        temp_cap = _cap_by_instance(self._device, "colorTemperatureK")
        scene_cap = _cap_by_instance(self._device, "lightScene")

        if power_cap:
            await client.async_control(
                sku,
                self._device_id,
                power_cap["type"],
                "powerSwitch",
                1,
            )
            self._set_value("powerSwitch", 1)

        if ATTR_BRIGHTNESS in kwargs and brightness_cap:
            percent = max(1, round((kwargs[ATTR_BRIGHTNESS] / 255) * 100))
            await client.async_control(
                sku,
                self._device_id,
                brightness_cap["type"],
                "brightness",
                percent,
            )
            self._set_value("brightness", percent)

        if ATTR_RGB_COLOR in kwargs and rgb_cap:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            rgb = (r << 16) + (g << 8) + b
            await client.async_control(
                sku,
                self._device_id,
                rgb_cap["type"],
                "colorRgb",
                rgb,
            )
            self._set_value("colorRgb", rgb)

        if ATTR_COLOR_TEMP_KELVIN in kwargs and temp_cap:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            await client.async_control(
                sku,
                self._device_id,
                temp_cap["type"],
                "colorTemperatureK",
                kelvin,
            )
            self._set_value("colorTemperatureK", kelvin)

        if ATTR_EFFECT in kwargs and scene_cap:
            scene_map = self.effect_map
            effect = kwargs[ATTR_EFFECT]
            if effect in scene_map:
                scene_value = scene_map[effect]
                await client.async_control(
                    sku,
                    self._device_id,
                    scene_cap["type"],
                    "lightScene",
                    scene_value,
                )
                self._set_value("lightScene", scene_value)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        power_cap = _cap_by_instance(self._device, "powerSwitch")
        if power_cap:
            await self._entry.runtime_data.client.async_control(
                self._device["sku"],
                self._device_id,
                power_cap["type"],
                "powerSwitch",
                0,
            )
            self._set_value("powerSwitch", 0)
        self.async_write_ha_state()
