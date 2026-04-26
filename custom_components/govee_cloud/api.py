"""Async API client for Govee Cloud."""

from __future__ import annotations

import uuid
from typing import Any

from aiohttp import ClientSession


class GoveeApiError(Exception):
    """Base API error."""


class GoveeAuthError(GoveeApiError):
    """Invalid API key."""


class GoveeRateLimitError(GoveeApiError):
    """Rate limit reached."""


class GoveeClient:
    """Thin async wrapper around the Govee Open API."""

    def __init__(self, api_key: str, session: ClientSession) -> None:
        self._api_key = api_key
        self._session = session

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Govee-API-Key": self._api_key,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        async with self._session.request(
            method,
            url,
            headers=self._headers,
            json=json_body,
            timeout=30,
        ) as resp:
            if resp.status == 401:
                raise GoveeAuthError("Invalid Govee API key")
            if resp.status == 429:
                raise GoveeRateLimitError("Govee rate limit reached")
            resp.raise_for_status()
            data = await resp.json()

        if data.get("code") not in (200, None):
            capability = (json_body or {}).get("payload", {}).get("capability", {})
            capability_hint = ""
            if capability:
                capability_hint = (
                    f" capability_type={capability.get('type')}"
                    f" instance={capability.get('instance')}"
                    f" value={capability.get('value')!r}"
                )
            raise GoveeApiError(
                f"Govee API error: code={data.get('code')} message={data.get('message')}"
                f"{capability_hint}"
            )
        return data

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch devices and their capabilities."""
        data = await self._request("GET", "/user/devices")
        return data.get("data", [])

    async def async_get_device_state(self, sku: str, device: str) -> dict[str, Any]:
        """Fetch current state for a device.

        Note:
            Verify this payload against your current Govee docs.
            The integration is written to keep working even if state fetch fails.
        """
        data = await self._request(
            "POST",
            "/device/state",
            json_body={
                "requestId": str(uuid.uuid4()),
                "payload": {
                    "sku": sku,
                    "device": device,
                },
            },
        )
        return data.get("payload", {}) or data.get("data", {}) or {}

    async def async_control(
        self,
        sku: str,
        device: str,
        capability_type: str,
        instance: str,
        value: Any,
    ) -> dict[str, Any]:
        """Send a control command to a device."""
        return await self._request(
            "POST",
            "/device/control",
            json_body={
                "requestId": str(uuid.uuid4()),
                "payload": {
                    "sku": sku,
                    "device": device,
                    "capability": {
                        "type": capability_type,
                        "instance": instance,
                        "value": value,
                    },
                },
            },
        )


from .const import API_BASE
