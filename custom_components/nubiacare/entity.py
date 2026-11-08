"""Shared entity helpers for Nubia Care devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from nubia_care import NubiaDevice

_DEFAULT_MANUFACTURER = "Nubia"
_MODEL_MANUFACTURER_PREFIXES = ("ZTE ",)


def create_device_info(device: NubiaDevice, device_id: str) -> DeviceInfo:
    """Create device registry information from Nubia device details."""
    model_name = device.model_name
    manufacturer = _DEFAULT_MANUFACTURER
    model = model_name or device.model

    if model_name is not None:
        for prefix in _MODEL_MANUFACTURER_PREFIXES:
            if model_name.startswith(prefix):
                manufacturer = prefix.strip()
                model = model_name.removeprefix(prefix).strip() or device.model
                break

    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        manufacturer=manufacturer,
        model=model,
        name=device.name or device.id,
    )
