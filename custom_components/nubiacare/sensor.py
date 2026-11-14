"""Battery sensors for Nubia Care devices."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NubiaCareCoordinator
from .entity import NubiaCareDevice, create_device_info

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import NubiaCareConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: NubiaCareConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a battery sensor for every device with a valid ID."""
    async_add_entities(
        NubiaCareBatterySensor(
            entry.runtime_data.coordinators[device.device_id], device
        )
        for device in entry.runtime_data.devices
    )


class NubiaCareBatterySensor(  # pyright: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[NubiaCareCoordinator], SensorEntity
):
    """Represent a Nubia Care device's current battery level."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: NubiaCareCoordinator,
        device: NubiaCareDevice,
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._initial_device = device
        self._attr_unique_id = f"{device.device_id}_battery"

    @property
    @override
    def native_value(self) -> int | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the current battery level."""
        return self.coordinator.data.battery_level

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Associate this sensor with its Nubia Care watch."""
        return create_device_info(self._initial_device)
