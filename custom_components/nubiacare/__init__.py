"""The Nubia Care integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from nubia_care import (
    NubiaAPI,
    NubiaAuth,
    NubiaAuthenticationError,
    NubiaDevice,
    NubiaError,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]
UPDATE_INTERVAL = timedelta(minutes=10)

type NubiaCareConfigEntry = ConfigEntry[DataUpdateCoordinator[list[NubiaDevice]]]


async def async_setup_entry(hass: HomeAssistant, entry: NubiaCareConfigEntry) -> bool:
    """Set up Nubia Care from a config entry."""
    auth = NubiaAuth(async_get_clientsession(hass))
    try:
        session = await auth.async_login(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
    except NubiaAuthenticationError as err:
        message = "Nubia Care rejected the credentials"
        raise ConfigEntryAuthFailed(message) from err
    except NubiaError as err:
        message = f"Unable to connect to Nubia Care: {err}"
        raise ConfigEntryNotReady(message) from err

    api = NubiaAPI(auth)

    try:
        devices = await api.async_get_devices(session)
    except NubiaError as err:
        message = f"Unable to fetch Nubia Care devices: {err}"
        raise ConfigEntryNotReady(message) from err
    device_ids = [
        device_id for device in devices if (device_id := device.id) is not None
    ]

    async def async_update_devices() -> list[NubiaDevice]:
        """Fetch current details for the configured account devices."""
        try:
            return await asyncio.gather(
                *(api.async_get_device(session, device_id) for device_id in device_ids)
            )
        except NubiaError as err:
            message = f"Unable to fetch Nubia Care device details: {err}"
            raise UpdateFailed(message) from err

    coordinator = DataUpdateCoordinator(
        hass,
        config_entry=entry,
        logger=logging.getLogger(__name__),
        name=DOMAIN,
        update_interval=UPDATE_INTERVAL,
        update_method=async_update_devices,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NubiaCareConfigEntry) -> bool:
    """Unload a Nubia Care config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
