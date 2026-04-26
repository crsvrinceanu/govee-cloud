"""Config flow for Govee Cloud."""

from __future__ import annotations

import hashlib

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GoveeApiError, GoveeAuthError, GoveeClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)
        ),
    }
)


class GoveeCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Govee Cloud."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = GoveeClient(user_input[CONF_API_KEY], session)

            try:
                devices = await client.async_get_devices()
                api_hash = hashlib.sha256(
                    user_input[CONF_API_KEY].encode("utf-8")
                ).hexdigest()[:12]
                await self.async_set_unique_id(f"govee_cloud_{api_hash}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Govee Cloud ({len(devices)} devices)",
                    data={CONF_API_KEY: user_input[CONF_API_KEY]},
                    options={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
                )
            except GoveeAuthError:
                errors["base"] = "invalid_auth"
            except GoveeApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return GoveeOptionsFlow(config_entry)


class GoveeOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Govee Cloud."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
