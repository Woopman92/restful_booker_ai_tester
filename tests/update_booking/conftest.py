"""Initial update state for repeated full replacement tests."""

from copy import deepcopy
from typing import Any

import pytest

from checkers.update_booking import check_update_booking_response
from helpers.models import Booking
from tests.client import ApiClient


@pytest.fixture
def updated_booking(
    api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
) -> Booking:
    """Perform the first full update before a repeated-update test.

    Args:
        api: Client used to update the owned booking.
        booking: Original record registered for cleanup by its creation fixture.
        replacement_payload: Complete data to send in both update requests.
        basic_auth: Valid Basic authentication credentials.

    Returns:
        Booking: Original ID and an independent copy of the first update payload.

    Raises:
        AssertionError: The first update response or its booking values are invalid.
        ValueError: JSON or a calendar date cannot be parsed.
        requests.RequestException: The update request fails.
    """
    response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
    check_update_booking_response(response, replacement_payload)
    return Booking(booking.booking_id, deepcopy(replacement_payload))
