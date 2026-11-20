"""Tests for the Nubia Care config flow."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from nubia_care import (
    NubiaAuthenticationError,
    NubiaError,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nubiacare.config_flow import validate_input
from custom_components.nubiacare.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

TEST_USER_INPUT = {
    CONF_USERNAME: "user@example.com",
    CONF_PASSWORD: "password",
}


async def test_user_form(hass: HomeAssistant) -> None:
    """Test the initial config flow form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert result.get("errors") == {}


async def test_successful_config_flow(hass: HomeAssistant) -> None:
    """Test a successful config flow creates an entry."""
    with patch(
        "custom_components.nubiacare.config_flow.validate_input",
        return_value="user@example.com",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=TEST_USER_INPUT,
        )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "user@example.com"
    assert result.get("data") == TEST_USER_INPUT


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (NubiaAuthenticationError("Invalid credentials"), "invalid_auth"),
        (NubiaError("Unable to connect"), "cannot_connect"),
        (RuntimeError("Unexpected error"), "unknown"),
    ],
)
async def test_config_flow_errors(
    hass: HomeAssistant,
    exception: Exception,
    error: str,
) -> None:
    """Test config flow validation errors."""
    with patch(
        "custom_components.nubiacare.config_flow.validate_input",
        side_effect=exception,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=TEST_USER_INPUT,
        )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert result.get("errors") == {"base": error}


async def test_duplicate_config_entry(hass: HomeAssistant) -> None:
    """Test duplicate accounts are aborted."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_USER_INPUT,
        unique_id="user@example.com",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.nubiacare.config_flow.validate_input",
        return_value="USER@EXAMPLE.COM",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=TEST_USER_INPUT,
        )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_validate_input(hass: HomeAssistant) -> None:
    """Test account validation logs in and fetches devices."""
    session = MagicMock()
    auth = MagicMock()
    auth.async_login = AsyncMock(return_value=session)
    api = MagicMock()
    api.async_get_devices = AsyncMock(return_value=[])

    with (
        patch(
            "custom_components.nubiacare.config_flow.NubiaAuth",
            return_value=auth,
        ),
        patch(
            "custom_components.nubiacare.config_flow.NubiaAPI",
            return_value=api,
        ),
    ):
        result = await validate_input(hass, TEST_USER_INPUT)

    assert result == "user@example.com"
    auth.async_login.assert_awaited_once_with("user@example.com", "password")
    api.async_get_devices.assert_awaited_once_with(session)
