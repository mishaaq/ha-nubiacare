"""Focus-mode calendars for Nubia Care devices."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, time, timedelta
from functools import cached_property
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .coordinator import NubiaCareConfigurationCoordinator
from .entity import NubiaCareDevice, create_device_info

PARALLEL_UPDATES = 0
_DAYS_PER_WEEK = 7

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
    """Set up a focus-mode calendar for each configured device."""
    _ = _hass
    async_add_entities(
        NubiaCareFocusCalendar(
            entry.runtime_data.configuration_coordinators[device.device_id],
            device,
        )
        for device in entry.runtime_data.devices
    )


class NubiaCareFocusCalendar(  # pyright: ignore[reportIncompatibleVariableOverride]
    CoordinatorEntity[NubiaCareConfigurationCoordinator], CalendarEntity
):
    """Represent enabled focus-mode periods as weekly calendar events."""

    _attr_has_entity_name = True
    _attr_translation_key = "focus_mode"

    def __init__(
        self,
        coordinator: NubiaCareConfigurationCoordinator,
        device: NubiaCareDevice,
    ) -> None:
        """Initialize the focus-mode calendar."""
        super().__init__(coordinator)
        self._initial_device = device
        self._attr_unique_id = f"{device.device_id}_focus_mode"

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the current or next scheduled focus-mode period."""
        now = dt_util.now()
        events = _events_for_schedule(
            self.coordinator.data.focus_schedule,
            now,
            now + timedelta(days=8),
        )
        return events[0] if events else None

    @override
    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return scheduled focus-mode periods within the requested range."""
        _ = hass
        return _events_for_schedule(
            self.coordinator.data.focus_schedule,
            start_date,
            end_date,
        )

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Associate this calendar with its Nubia Care device."""
        return create_device_info(self._initial_device)


def _events_for_schedule(
    schedule: tuple[Mapping[str, Any], ...],
    start_date: datetime,
    end_date: datetime,
) -> list[CalendarEvent]:
    """Expand enabled weekly rules into dated focus-mode events."""
    timezone = start_date.tzinfo or UTC
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone)
    if start_date >= end_date:
        return []

    events: list[CalendarEvent] = []
    for day_offset in range((end_date.date() - start_date.date()).days + 1):
        event_date = start_date.date() + timedelta(days=day_offset)
        for rule in schedule:
            week = rule.get("week")
            name = rule.get("name")
            intervals = rule.get("interval")
            if (
                not _is_enabled(rule.get("status"))
                or not isinstance(week, str)
                or len(week) != _DAYS_PER_WEEK
                or week[event_date.weekday()] != "1"
                or not isinstance(name, str)
                or not name.strip()
                or not isinstance(intervals, list)
            ):
                continue
            rule_id = rule.get("ruleId")
            for interval_index, interval in enumerate(intervals):
                if not isinstance(interval, Mapping) or not _is_enabled(
                    interval.get("status")
                ):
                    continue
                begin_time = _parse_time(interval.get("beginTime"))
                end_time = _parse_time(interval.get("endTime"))
                if begin_time is None or end_time is None or begin_time >= end_time:
                    continue
                event_start = datetime.combine(event_date, begin_time, tzinfo=timezone)
                event_end = datetime.combine(event_date, end_time, tzinfo=timezone)
                if event_start >= end_date or event_end <= start_date:
                    continue
                interval_name = interval.get("intervalName")
                event_uid = (
                    f"{rule_id}:{event_date.isoformat()}:{interval_name}"
                    if isinstance(rule_id, str) and isinstance(interval_name, str)
                    else f"{name}:{event_date.isoformat()}:{interval_index}"
                )
                events.append(
                    CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=name,
                        uid=event_uid,
                    )
                )
    return sorted(events, key=lambda event: event.start_datetime_local)


def _is_enabled(value: Any) -> bool:
    """Return whether a Nubia Care status value represents enabled."""
    return value == "1" or (
        isinstance(value, int) and not isinstance(value, bool) and value == 1
    )


def _parse_time(value: Any) -> time | None:
    """Parse a local HH:MM schedule time."""
    if not isinstance(value, str):
        return None
    try:
        parsed = time.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return None
    return parsed
