"""Device trackers for Nubia Care watches."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import cached_property
from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import TrackerEntity
from homeassistant.core import callback
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
    """Set up a tracker for every device in the Nubia Care account."""
    async_add_entities(
        NubiaCareTracker(entry.runtime_data.coordinators[device.device_id], device)
        for device in entry.runtime_data.devices
    )


class NubiaCareTracker(  # pyright: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[NubiaCareCoordinator], TrackerEntity
):
    """Represent a Nubia Care device's latest location."""

    _attr_has_entity_name = True
    _attr_translation_key = "location"
    _attr_source_type = SourceType.GPS

    def __init__(
        self,
        coordinator: NubiaCareCoordinator,
        device: NubiaCareDevice,
    ) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self._initial_device = device
        self._attr_extra_state_attributes: dict[str, str] = {}
        self._attr_unique_id = device.device_id
        self._update_location()

    def _update_location(self) -> None:
        """Update cached tracker coordinates from the latest API data."""
        location = self.coordinator.data.location
        self._attr_extra_state_attributes.clear()
        if location is None:
            self._attr_latitude = None
            self._attr_longitude = None
            self._attr_location_accuracy = 0
            return
        self._attr_extra_state_attributes["location_query_type"] = (
            location.location_query_type
        )
        latitude = _coordinate(location.latitude, -90, 90)
        longitude = _coordinate(location.longitude, -180, 180)
        self._attr_latitude = latitude[0] if latitude is not None else None
        self._attr_longitude = longitude[0] if longitude is not None else None
        accuracy = _accuracy(location.radius)
        self._attr_location_accuracy = accuracy if accuracy is not None else 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update coordinates when the coordinator fetches new device data."""
        self._update_location()
        super()._handle_coordinator_update()

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return the Nubia Care watch represented by this tracker."""
        return create_device_info(self._initial_device)


def _coordinate(value: Any, minimum: int, maximum: int) -> tuple[float, str] | None:
    """Validate a GPS coordinate and retain its original precision."""
    if isinstance(value, bool):
        return None
    try:
        coordinate = Decimal(str(value))
    except InvalidOperation, TypeError, ValueError:
        return None
    if not coordinate.is_finite() or not minimum <= coordinate <= maximum:
        return None
    return float(coordinate), str(value)


def _accuracy(value: Any) -> float | None:
    """Validate a GPS accuracy radius in meters."""
    if isinstance(value, bool):
        return None
    try:
        accuracy = Decimal(str(value))
    except InvalidOperation, TypeError, ValueError:
        return None
    if not accuracy.is_finite() or accuracy < 0:
        return None
    return float(accuracy)
