"""Shared entity helpers for Nubia Care devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from nubia_care import NubiaDevice as NubiaDeviceInfo

_DEFAULT_MANUFACTURER = "Nubia"
_MODEL_MANUFACTURER_PREFIXES = ("ZTE ",)


@dataclass(frozen=True, slots=True)
class NubiaCareDevice:
    """Combine device details that describe a Nubia Care device."""

    device_id: str
    device_info: NubiaDeviceInfo
    model_name: str | None = None


def create_device_info(device_id: str, device: NubiaCareDevice) -> DeviceInfo:
    """Create device registry information from Nubia device details."""
    device_info = device.device_info
    model_name = device.model_name
    manufacturer = _DEFAULT_MANUFACTURER
    model = model_name or device_info.model

    if model_name is not None:
        for prefix in _MODEL_MANUFACTURER_PREFIXES:
            if model_name.startswith(prefix):
                manufacturer = prefix.strip()
                model = model_name.removeprefix(prefix).strip() or device_info.model
                break

    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        manufacturer=manufacturer,
        model=model,
        name=device_info.name or device_info.id,
    )
