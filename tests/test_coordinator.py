"""Tests for the Nubia Care data coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

from nubia_care import (
    NubiaAPI,
    NubiaDeviceConfiguration,
    NubiaDeviceState,
    NubiaSession,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nubiacare.const import DOMAIN
from custom_components.nubiacare.coordinator import (
    CONFIGURATION_UPDATE_INTERVAL,
    NubiaCareConfigurationCoordinator,
    NubiaCareCoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_device_coordinator_fetches_state_only(hass: HomeAssistant) -> None:
    """Fetch device state without coupling it to configuration refreshes."""
    config_entry = MockConfigEntry(domain=DOMAIN)
    config_entry.add_to_hass(hass)
    api = MagicMock(spec=NubiaAPI)
    device_state = NubiaDeviceState({"imei": "device-1"})
    api.async_get_device = AsyncMock(return_value=device_state)
    api.async_get_device_configuration = AsyncMock(
        return_value=NubiaDeviceConfiguration({"disBan": []})
    )
    session = NubiaSession(openid="open-id", accesstoken="token")
    coordinator = NubiaCareCoordinator(
        hass,
        config_entry,
        api,
        session,
        "device-1",
    )

    await coordinator.async_refresh()
    data = coordinator.data

    assert data is device_state
    api.async_get_device.assert_awaited_once_with(session, "device-1")
    api.async_get_device_configuration.assert_not_awaited()


async def test_configuration_coordinator_fetches_settings_every_five_minutes(
    hass: HomeAssistant,
) -> None:
    """Fetch settings independently on the five-minute schedule."""
    config_entry = MockConfigEntry(domain=DOMAIN)
    config_entry.add_to_hass(hass)
    api = MagicMock(spec=NubiaAPI)
    configuration = NubiaDeviceConfiguration({"disBan": []})
    api.async_get_device_configuration = AsyncMock(return_value=configuration)
    session = NubiaSession(openid="open-id", accesstoken="token")
    coordinator = NubiaCareConfigurationCoordinator(
        hass,
        config_entry,
        api,
        session,
        "device-1",
    )

    await coordinator.async_refresh()

    assert coordinator.data is configuration
    assert coordinator.update_interval == CONFIGURATION_UPDATE_INTERVAL
    api.async_get_device_configuration.assert_awaited_once_with(session, "device-1")
