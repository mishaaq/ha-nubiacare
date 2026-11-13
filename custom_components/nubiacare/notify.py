"""Notify entities for Nubia Care watches."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, override

from homeassistant.components.notify import NotifyEntity
from homeassistant.exceptions import HomeAssistantError
from nubia_care import NubiaError, NubiaMessageTooLongError

from .const import DOMAIN
from .entity import NubiaCareDevice, create_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from nubia_care import NubiaAPI, NubiaSession

    from . import NubiaCareConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    _: HomeAssistant,
    entry: NubiaCareConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a text notifier for every Nubia Care device."""
    runtime_data = entry.runtime_data
    async_add_entities(
        NubiaCareNotifier(
            runtime_data.api,
            runtime_data.session,
            device,
            device.device_id,
        )
        for device in runtime_data.devices
    )


class NubiaCareNotifier(NotifyEntity):
    """Send text messages to a Nubia Care device."""

    _attr_has_entity_name = True
    _attr_translation_key = "message"

    def __init__(
        self,
        api: NubiaAPI,
        session: NubiaSession,
        device: NubiaCareDevice,
        device_id: str,
    ) -> None:
        """Initialize the notifier."""
        super().__init__()
        self._api = api
        self._session = session
        self._initial_device = device
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_notify"

    @override
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a text message to the device."""
        _ = title
        try:
            await self._api.async_send_text_message(
                self._session, self._device_id, message
            )
        except NubiaMessageTooLongError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="message_too_long",
                translation_placeholders={"max_length": str(err.max_length)},
            ) from err
        except NubiaError as err:
            _LOGGER.exception(
                "Nubia Care message sending failed for device %s", self._device_id
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="send_message_failed",
                translation_placeholders={"reason": str(err)},
            ) from err

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Associate this notifier with its Nubia Care HA device."""
        return create_device_info(self._device_id, self._initial_device)
