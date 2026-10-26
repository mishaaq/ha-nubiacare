"""Device trackers for Nubia Care watches."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import cached_property
from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import TrackerEntity
from homeassistant.core import callback

from .entity import create_device_info

if TYPE_CHECKING:
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
    """Set up a tracker for every device in the Nubia Care account."""
    coordinator = entry.runtime_data
    added_device_ids: set[str] = set()
    entities: dict[str, NubiaCareTracker] = {}

    @callback
    def add_new_devices() -> None:
        devices = [
            (device, device_id)
            for device in coordinator.data
            if (device_id := device.id) is not None
            and device_id not in added_device_ids
        ]
        if devices:
            added_device_ids.update(device_id for _, device_id in devices)
            new_entities = [
                NubiaCareTracker(coordinator, device, device_id)
                for device, device_id in devices
            ]
            entities.update(
                {
                    device_id: entity
                    for (_, device_id), entity in zip(
                        devices, new_entities, strict=True
                    )
                }
            )
            async_add_entities(new_entities)
        new_device_ids = {device_id for _, device_id in devices}
        for device_id, entity in entities.items():
            if device_id not in new_device_ids:
                entity.update_from_coordinator()

    entry.async_on_unload(coordinator.async_add_listener(add_new_devices))
    add_new_devices()


class NubiaCareTracker(TrackerEntity):
    """Represent a Nubia Care device's latest location."""

    _attr_has_entity_name = True
    _attr_translation_key = "location"
    _attr_source_type = SourceType.GPS

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[list[NubiaDevice]],
        device: NubiaDevice,
        device_id: str,
    ) -> None:
        """Initialize the tracker."""
        super().__init__()
        self._coordinator = coordinator
        self._device_id = device_id
        self._initial_device = device
        self._attr_unique_id = device_id
        self._attr_available = coordinator.last_update_success
        self._update_location()

    def _update_location(self) -> None:
        """Update cached tracker coordinates from the latest API data."""
        location = self._device.location if self._device is not None else None
        if location is None:
            self._attr_latitude = None
            self._attr_longitude = None
            self._attr_location_accuracy = 0
            return
        latitude = _coordinate(location.latitude, -90, 90)
        longitude = _coordinate(location.longitude, -180, 180)
        self._attr_latitude = latitude[0] if latitude is not None else None
        self._attr_longitude = longitude[0] if longitude is not None else None
        accuracy = _accuracy(location.radius)
        self._attr_location_accuracy = accuracy if accuracy is not None else 0

    @callback
    def update_from_coordinator(self) -> None:
        """Update coordinates when the coordinator fetches new device data."""
        self._update_location()
        self._attr_available = (
            self._coordinator.last_update_success and self._device is not None
        )
        self.async_write_ha_state()

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return the Nubia Care watch represented by this tracker."""
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
