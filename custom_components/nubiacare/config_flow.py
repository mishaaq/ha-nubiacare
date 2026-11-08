"""Config flow for the Nubia Care integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow as HomeAssistantConfigFlow
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from nubia_care import (
    NubiaAPI,
    NubiaAuth,
    NubiaAuthenticationError,
    NubiaError,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): vol.All(str, vol.Length(min=1)),
        vol.Required(CONF_PASSWORD): vol.All(str, vol.Length(min=1)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> str:
    """
    Validate the user input allows us to connect.

    Log in and fetch the account's devices before creating the config entry.
    """
    auth = NubiaAuth(async_get_clientsession(hass))
    session = await auth.async_login(data[CONF_USERNAME], data[CONF_PASSWORD])
    await NubiaAPI(auth).async_get_devices(session)
    return data[CONF_USERNAME]


class ConfigFlow(HomeAssistantConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nubia Care."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                username = await validate_input(self.hass, user_input)
            except NubiaAuthenticationError:
                errors["base"] = "invalid_auth"
            except NubiaError:
                _LOGGER.exception("Unable to validate Nubia Care account")
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error setting up Nubia Care")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(username.casefold())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=username, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
