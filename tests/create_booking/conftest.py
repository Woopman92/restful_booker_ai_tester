"""Unique payloads and response tracking for all creation tests."""

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

from tests.create_booking.support import CreationTracker
from tests.support import ApiClient


@pytest.fixture
def booking_payload() -> dict[str, Any]:
    """Build fresh valid data that can be modified by a single test.

    Returns:
        dict[str, Any]: Booking fields with unique guest names and valid dates.
    """
    unique = uuid4().hex
    return {
        'firstname': f'QA{unique}',
        'lastname': f'Test{unique}',
        'totalprice': 123,
        'depositpaid': True,
        'bookingdates': {'checkin': '2030-06-15', 'checkout': '2030-06-20'},
        'additionalneeds': 'Breakfast',
    }


@pytest.fixture(autouse=True)
def creation_tracker(api: ApiClient, booking_payload: dict[str, Any]) -> Iterator[CreationTracker]:
    """Track response IDs and clean up even when creation assertions fail.

    Args:
        api: Session-backed API client.
        booking_payload: Mutable data for the current test.

    Yields:
        CreationTracker: Registry installed as a temporary session response hook.

    Raises:
        AssertionError: Cleanup or lookup of unexpectedly created data fails.
    """
    tracker = CreationTracker(api, booking_payload, {key: booking_payload[key] for key in ('firstname', 'lastname')})
    api.session.hooks['response'].append(tracker.capture)
    try:
        yield tracker
    finally:
        api.session.hooks['response'].remove(tracker.capture)
        tracker.cleanup()
