"""Battery sensors for Nubia Care devices."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback

from .entity import create_device_info

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
    from nubia_care import NubiaDevice

    from . import NubiaCareConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: NubiaCareConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a battery sensor for every device with a valid ID."""
    coordinator = entry.runtime_data
    sensors = [
        NubiaCareBatterySensor(coordinator, device, device_id)
        for device in coordinator.data
        if (device_id := device.id) is not None
    ]

    @callback
    def update_sensors() -> None:
        """Refresh all battery sensors after coordinator updates."""
        for sensor in sensors:
            sensor.update_from_coordinator()

    entry.async_on_unload(coordinator.async_add_listener(update_sensors))
    async_add_entities(sensors)


class NubiaCareBatterySensor(SensorEntity):
    """Represent a Nubia Care device's current battery level."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_value: str | int | float | None | date | datetime | Decimal = None

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[list[NubiaDevice]],
        device: NubiaDevice,
        device_id: str,
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__()
        self._coordinator = coordinator
        self._device_id = device_id
        self._initial_device = device
        self._attr_unique_id = f"{device_id}_battery"
        self._update_battery()

    @callback
    def update_from_coordinator(self) -> None:
        """Refresh the battery level after the coordinator updates."""
        self._update_battery()
        self.async_write_ha_state()

    def _update_battery(self) -> None:
        """Update cached battery state and availability."""
        device = self._device
        self._attr_native_value = device.battery_level if device is not None else None
        self._attr_available = (
            self._coordinator.last_update_success and device is not None
        )

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Associate this sensor with its Nubia Care watch."""
        device = self._device or self._initial_device
        return create_device_info(device, self._device_id)

    @property
    def _device(self) -> NubiaDevice | None:
        """Return the latest coordinator data for this device."""
        return next(
            (
                device
                for device in self._coordinator.data
                if device.id == self._device_id
            ),
            None,
        )
