# Govee Cloud for Home Assistant

Custom Home Assistant integration for controlling Govee devices through the Govee OpenAPI.

## Features

- Config flow support
- Light entities for supported Govee lights
- Switch entities for supported on/off devices
- Select entities for supported scene and mode capabilities
- Number entities for supported numeric capabilities
- Sensor entities for supported read-only property capabilities

## Installation with HACS

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the menu and choose `Custom repositories`.
4. Add `https://github.com/crsvrinceanu/govee-cloud`.
5. Choose `Integration` as the category.
6. Install `Govee Cloud`.
7. Restart Home Assistant.
8. Go to `Settings -> Devices & Services -> Add Integration`.
9. Search for `Govee Cloud`.

## Manual installation

Copy `custom_components/govee_cloud` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

You need a Govee API key from the Govee Developer Platform:

https://developer.govee.com/

## Repository

- GitHub user: `crsvrinceanu`
- Repository: `govee-cloud`

## Notes

This integration uses the Govee cloud API, so it requires internet access and is subject to Govee API limits and supported model availability.
