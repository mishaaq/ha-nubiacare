"""Firmware update entities for Nubia Care devices."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError
from nubia_care import NubiaError, NubiaFirmware

from .const import DOMAIN
from .entity import NubiaCareDevice, create_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from nubia_care import NubiaAPI, NubiaSession

    from . import NubiaCareConfigEntry

_LOGGER = logging.getLogger(__name__)
_RELEASE_SUMMARY_MAX_LENGTH = 255
SCAN_INTERVAL = timedelta(hours=12)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: NubiaCareConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a firmware update entity for every configured device."""
    runtime_data = entry.runtime_data
    async_add_entities(
        [
            NubiaCareUpdateEntity(
                runtime_data.api,
                runtime_data.session,
                device,
                device.device_id,
            )
            for device in runtime_data.devices
        ],
        update_before_add=True,
    )


class NubiaCareUpdateEntity(UpdateEntity):
    """Represent the available firmware update for a Nubia Care device."""

    _attr_has_entity_name = True
    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_auto_update = True
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(
        self,
        api: NubiaAPI,
        session: NubiaSession,
        device: NubiaCareDevice,
        device_id: str,
    ) -> None:
        """Initialize the firmware update entity."""
        super().__init__()
        self._api = api
        self._session = session
        self._initial_device = device
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_firmware"
        self._firmware: NubiaFirmware | None = None
        self._update_firmware()

    async def async_update(self) -> None:
        """Fetch the latest firmware details for this device."""
        try:
            self._firmware = await self._api.async_get_device_firmware(
                self._session, self._device_id
            )
        except NubiaError as err:
            _LOGGER.warning(
                "Unable to fetch Nubia Care firmware version for device %s: %s",
                self._device_id,
                err,
            )
            self._firmware = None
        self._attr_available = True
        self._update_firmware()

    @override
    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Ask Nubia Care to install the available firmware update."""
        _ = backup, kwargs
        if self._available_version is None or (
            version is not None and version != self._available_version
        ):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="firmware_update_unavailable",
            )

        try:
            await self._api.async_install_device_firmware(
                self._session, self._device_id
            )
        except NubiaError as err:
            _LOGGER.exception(
                "Nubia Care firmware update request failed for device %s",
                self._device_id,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="install_update_failed",
                translation_placeholders={"reason": str(err)},
            ) from err
        await self.async_update()
        self.async_write_ha_state()

    async def async_release_notes(self) -> str | None:
        """Return the full release notes for the available firmware."""
        if self._firmware is None:
            return None
        return _non_empty(self._firmware.release_note)

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Associate this update entity with its Nubia Care device."""
        return create_device_info(
            self._device_id, replace(self._initial_device, firmware=self._firmware)
        )

    def _update_firmware(self) -> None:
        """Update cached entity values from the latest API response."""
        firmware = self._firmware
        installed_version = (
            _non_empty(firmware.device_firmware) if firmware is not None else None
        )
        reported_version = (
            _non_empty(firmware.firmware) if firmware is not None else None
        )
        self._available_version = (
            reported_version if reported_version != installed_version else None
        )
        self._attr_installed_version = installed_version
        self._attr_latest_version = reported_version or installed_version
        self._attr_release_summary = _format_release_summary(
            _non_empty(firmware.release_note) if firmware is not None else None,
            _non_empty(firmware.file_size) if firmware is not None else None,
        )


def _non_empty(value: str | None) -> str | None:
    """Normalize empty API strings to missing values."""
    if not value:
        return None
    return value


def _format_release_summary(
    release_note: str | None, file_size: str | None
) -> str | None:
    """Include package size in the update entity's supported summary field."""
    if file_size is None:
        return release_note

    size_summary = f"Package size: {file_size}"
    if len(size_summary) >= _RELEASE_SUMMARY_MAX_LENGTH:
        return size_summary[:_RELEASE_SUMMARY_MAX_LENGTH]
    if release_note is None:
        return size_summary

    note_length = max(0, _RELEASE_SUMMARY_MAX_LENGTH - len(size_summary) - 2)
    if len(release_note) > note_length and note_length:
        release_note = f"{release_note[: note_length - 1]}…"
    else:
        release_note = release_note[:note_length]
    return f"{release_note}\n\n{size_summary}"[:_RELEASE_SUMMARY_MAX_LENGTH]
