"""Coordinator for Govee Cloud data."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoveeApiError, GoveeClient

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoveeDeviceData:
    """Container for one device."""

    info: dict[str, Any]
    state: dict[str, Any] = field(default_factory=dict)


class GoveeCoordinator(DataUpdateCoordinator[dict[str, GoveeDeviceData]]):
    """Fetch data and lightweight state for all devices from Govee."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GoveeClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="govee_cloud",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._known_states: dict[str, dict[str, Any]] = {}
        self._refresh_count = 0

    def _should_refresh_state(self, device: dict[str, Any]) -> bool:
        """Return whether the device should get a /device/state refresh now."""
        capabilities = device.get("capabilities", [])
        device_id = device["device"]

        # Prime every device once so HA starts with real values.
        if device_id not in self._known_states:
            return True

        # Afterwards, refresh on a slower cadence to stay friendlier to Govee rate limits.
        if any(cap.get("type") == "devices.capabilities.property" for cap in capabilities):
            return self._refresh_count == 0

        return self._refresh_count == 0

    @staticmethod
    def _normalize_state_value(instance: str, raw_value: Any) -> Any:
        """Normalize Govee state values into the scalar Home Assistant expects."""
        if not isinstance(raw_value, dict):
            return raw_value

        preferred_keys: dict[str, tuple[str, ...]] = {
            "sensorTemperature": ("currentTemperature", "temperature"),
            "sensorHumidity": ("currentHumidity", "humidity"),
            "workMode": ("workMode", "mode"),
            "mode": ("mode",),
            "sliderTemperature": ("targetTemperature", "currentTemperature", "temperature"),
        }

        for key in preferred_keys.get(instance, ()):
            if key in raw_value:
                return raw_value[key]

        if "value" in raw_value:
            return raw_value["value"]

        scalar_items = [
            value for key, value in raw_value.items() if key != "unit" and not isinstance(value, dict)
        ]
        if len(scalar_items) == 1:
            return scalar_items[0]

        return raw_value

    async def _async_refresh_device_state(self, device: dict[str, Any]) -> dict[str, Any]:
        """Fetch current capability values for one device."""
        try:
            payload = await self.client.async_get_device_state(device["sku"], device["device"])
        except GoveeApiError as err:
            _LOGGER.debug("State refresh failed for %s: %s", device["device"], err)
            return {}

        states: dict[str, Any] = {}
        for capability in payload.get("capabilities", []):
            instance = capability.get("instance")
            if not instance:
                continue
            value = capability.get("state", {}).get("value")
            states[instance] = self._normalize_state_value(instance, value)

        return states

    async def _async_update_data(self) -> dict[str, GoveeDeviceData]:
        try:
            devices = await self.client.async_get_devices()
            result: dict[str, GoveeDeviceData] = {}
            states_by_device: dict[str, dict[str, Any]] = {}

            devices_to_refresh = [dev for dev in devices if self._should_refresh_state(dev)]
            if devices_to_refresh:
                refreshed_states = await asyncio.gather(
                    *(self._async_refresh_device_state(dev) for dev in devices_to_refresh)
                )
                states_by_device = {
                    dev["device"]: states
                    for dev, states in zip(devices_to_refresh, refreshed_states, strict=False)
                }

            for dev in devices:
                device_id = dev["device"]
                merged_state = self._known_states.get(device_id, {}).copy()
                if device_id in states_by_device:
                    merged_state.update(states_by_device[device_id])
                    self._known_states[device_id] = merged_state.copy()

                result[device_id] = GoveeDeviceData(
                    info=dev,
                    state=merged_state,
                )

            self._refresh_count = (self._refresh_count + 1) % 10
            return result

        except GoveeApiError as err:
            raise UpdateFailed(str(err)) from err

    def get_capability_value(self, device_id: str, instance: str) -> Any | None:
        """Return cached capability value, if any."""
        return self._known_states.get(device_id, {}).get(instance)

    def set_capability_value(self, device_id: str, instance: str, value: Any) -> None:
        """Store a capability value optimistically and push state update."""
        self._known_states.setdefault(device_id, {})[instance] = value
        if self.data and device_id in self.data:
            self.data[device_id].state[instance] = value
        self.async_update_listeners()
