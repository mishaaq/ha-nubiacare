"""Data update coordinator for Nubia Care devices."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, override

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from nubia_care import NubiaAPI, NubiaDeviceState, NubiaError, NubiaSession

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import NubiaCareConfigEntry

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(minutes=10)


class NubiaCareCoordinator(DataUpdateCoordinator[NubiaDeviceState]):
    """Fetch current state for one Nubia Care device."""

    config_entry: NubiaCareConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: NubiaCareConfigEntry,
        api: NubiaAPI,
        session: NubiaSession,
        device_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._api = api
        self._session = session
        self._device_id = device_id

    @override
    async def _async_update_data(self) -> NubiaDeviceState:
        """Fetch current state for this device."""
        try:
            device_state = await self._api.async_get_device(
                self._session, self._device_id
            )
        except NubiaError as err:
            message = (
                f"Unable to fetch Nubia Care device details for {self._device_id}: "
                f"{err}"
            )
            raise UpdateFailed(message) from err
        if device_state.id != self._device_id:
            message = (
                f"Nubia Care returned state for unexpected device {device_state.id!r}"
            )
            raise UpdateFailed(message)
        return device_state
