"""The Nubia Care integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

import probatio
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from nubia_care import (
    NubiaAPI,
    NubiaAuth,
    NubiaAuthenticationError,
    NubiaDevice,
    NubiaError,
    NubiaSession,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]
UPDATE_INTERVAL = timedelta(minutes=10)
LOCATION_REQUEST_DELAY = 10


@dataclass(slots=True)
class NubiaCareRuntimeData:
    """Data shared by Nubia Care platforms and actions."""

    api: NubiaAPI
    session: NubiaSession
    coordinator: DataUpdateCoordinator[list[NubiaDevice]]


type NubiaCareConfigEntry = ConfigEntry[NubiaCareRuntimeData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Register Nubia Care actions."""

    async def async_refresh_location(call: ServiceCall) -> None:
        """Ask the selected Nubia Care watch to report its location."""
        device, entry = service.async_get_device_and_config_entry(
            hass, DOMAIN, call.data[ATTR_DEVICE_ID]
        )
        device_id = next(
            (
                identifier
                for domain, identifier in device.identifiers
                if domain == DOMAIN
            ),
            None,
        )
        if device_id is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_not_supported",
            )

        runtime_data = entry.runtime_data
        try:
            await runtime_data.api.async_request_last_location(
                runtime_data.session, device_id
            )
        except NubiaError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="request_location_failed",
            ) from err
        await asyncio.sleep(LOCATION_REQUEST_DELAY)
        await runtime_data.coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "refresh_location",
        async_refresh_location,
        schema=probatio.Schema({probatio.Required(ATTR_DEVICE_ID): cv.string}),
    )
    return True


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
    entry.runtime_data = NubiaCareRuntimeData(
        api=api,
        session=session,
        coordinator=coordinator,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NubiaCareConfigEntry) -> bool:
    """Unload a Nubia Care config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
