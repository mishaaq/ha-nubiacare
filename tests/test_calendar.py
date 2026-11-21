"""Tests for Nubia Care focus-mode calendars."""

from datetime import UTC, datetime

from custom_components.nubiacare.calendar import _events_for_schedule


def test_events_for_schedule_expands_enabled_weekdays_and_intervals() -> None:
    """Include enabled rule intervals on their configured weekdays."""
    schedule = (
        {
            "ruleId": "monday-rule",
            "week": "1000000",
            "name": "Monday",
            "status": "1",
            "del": 0,
            "interval": [
                {
                    "intervalName": "am",
                    "beginTime": "10:15",
                    "endTime": "14:55",
                    "status": 1,
                },
                {
                    "intervalName": "pm",
                    "beginTime": "17:00",
                    "endTime": "18:00",
                    "status": 2,
                },
            ],
        },
        {
            "ruleId": "tuesday-rule",
            "week": "0100000",
            "name": "Tuesday",
            "status": 1,
            "interval": [
                {
                    "intervalName": "am",
                    "beginTime": "07:30",
                    "endTime": "11:55",
                    "status": "1",
                }
            ],
        },
        {
            "ruleId": "disabled-rule",
            "week": "0010000",
            "name": "Disabled",
            "status": "2",
            "interval": [
                {
                    "intervalName": "am",
                    "beginTime": "07:30",
                    "endTime": "14:00",
                    "status": 1,
                }
            ],
        },
    )

    events = _events_for_schedule(
        schedule,
        datetime(2026, 11, 23, tzinfo=UTC),
        datetime(2026, 11, 30, tzinfo=UTC),
    )

    assert [(event.summary, event.start, event.end, event.uid) for event in events] == [
        (
            "Monday",
            datetime(2026, 11, 23, 10, 15, tzinfo=UTC),
            datetime(2026, 11, 23, 14, 55, tzinfo=UTC),
            "monday-rule:2026-11-23:am",
        ),
        (
            "Tuesday",
            datetime(2026, 11, 24, 7, 30, tzinfo=UTC),
            datetime(2026, 11, 24, 11, 55, tzinfo=UTC),
            "tuesday-rule:2026-11-24:am",
        ),
    ]


def test_events_for_schedule_filters_to_requested_window() -> None:
    """Return only events overlapping the requested time range."""
    schedule = (
        {
            "ruleId": "monday-rule",
            "week": "1000000",
            "name": "Monday",
            "status": "1",
            "interval": [
                {
                    "intervalName": "am",
                    "beginTime": "10:15",
                    "endTime": "14:55",
                    "status": 1,
                }
            ],
        },
    )

    events = _events_for_schedule(
        schedule,
        datetime(2026, 11, 23, 12, 0, tzinfo=UTC),
        datetime(2026, 11, 23, 13, 0, tzinfo=UTC),
    )

    assert len(events) == 1
    assert events[0].summary == "Monday"
