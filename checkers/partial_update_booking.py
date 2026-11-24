"""Partial-update response, schema and persistence checks."""

from typing import Any

from requests import Response

from checkers.common import check_booking_field_types
from checkers.common import check_booking_values
from checkers.common import check_calendar_dates
from checkers.common import json_body
from checkers.errors import ResponseValuesMismatch
from tests.client import ApiClient


def check_partial_update_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Check all fields, including values that should remain unchanged after PATCH.

    Args:
        response: JSON response to the partial update.
        expected_payload: Full expected booking state.

    Raises:
        ResponseValuesMismatch: A booking value differs.
        AssertionError: Media type or schema is invalid.
        ValueError: The response is not valid JSON.
    """
    booking = json_body(response)
    check_booking_field_types(booking)
    # A malformed calendar string in a structurally valid PATCH response is a value mismatch.
    try:
        check_calendar_dates(booking)
    except (ValueError, AssertionError) as error:
        raise ResponseValuesMismatch(f"Invalid booking date: {booking['bookingdates']!r}") from error
    check_booking_values(booking, expected_payload)


def check_serialization_error(response: Response, expected_message: str) -> None:
    """Record a successful HTTP status carrying an unstructured serialization error.

    Args:
        response: PATCH or GET response for a record with null bookingdates.
        expected_message: Observed serialization error text.

    Raises:
        AssertionError: Media type or error message differs.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'text/html'
    assert response.text == expected_message


def check_unreadable_booking(api: ApiClient, booking_id: int, expected_message: str) -> None:
    """Verify that the owned record remains unreadable after a malformed date update.

    Args:
        api: Client used for the independent retrieval.
        booking_id: ID of the test-owned booking.
        expected_message: Observed error text expected from GET.

    Raises:
        AssertionError: Response metadata or error message differs.
        requests.RequestException: Retrieval fails.
    """
    response = api.get_booking(booking_id)
    check_serialization_error(response, expected_message)
