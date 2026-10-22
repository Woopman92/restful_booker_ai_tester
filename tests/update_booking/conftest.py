"""Isolated replacement payloads, authentication and deleted booking data."""

from collections.abc import Iterator
from copy import deepcopy
from datetime import date
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest

from checkers.bookings import booking_ids
from checkers.update_booking import check_update_booking_response
from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME
from helpers.models import Booking
from tests.client import ApiClient


@pytest.fixture
def basic_auth() -> tuple[str, str]:
    """Provide valid credentials independently of tested authentication failures.

    Returns:
        tuple[str, str]: Username and password used for Basic authentication.
    """
    return BOOKER_USERNAME, BOOKER_PASSWORD


@pytest.fixture
def replacement_payload(booking: Booking) -> dict[str, Any]:
    """Build a complete replacement with every value different from the original.

    Args:
        booking: Test-owned booking whose original payload must remain unchanged.

    Returns:
        dict[str, Any]: Independent data with suffixed strings, an incremented price,
        an inverted deposit flag and both dates shifted one day forward.
    """
    payload = deepcopy(booking.payload)
    payload.update({
        'firstname': booking.payload['firstname'] + 'Updated',
        'lastname': booking.payload['lastname'] + 'Changed',
        'totalprice': booking.payload['totalprice'] + 1,
        'depositpaid': not booking.payload['depositpaid'],
        'bookingdates': {
            field: (date.fromisoformat(booking.payload['bookingdates'][field]) + timedelta(days=1)).isoformat()
            for field in ('checkin', 'checkout')
        },
        'additionalneeds': booking.payload['additionalneeds'] + 'Updated',
    })
    return payload


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


@pytest.fixture
def deleted_booking(api: ApiClient, basic_auth: tuple[str, str]) -> Iterator[Booking]:
    """Provide a deleted owned ID and clean up any record unexpectedly recreated by PUT.

    Args:
        api: Client used for lifecycle operations.
        basic_auth: Valid credentials used only for setup and cleanup.

    Yields:
        Booking: ID and original fields of the deleted booking.

    Raises:
        AssertionError: Creation, deletion, recovery lookup or cleanup fails.
        ValueError: A response is not valid JSON.
        requests.RequestException: A setup or cleanup request fails.
    """
    unique = uuid4().hex
    payload = {
        'firstname': 'QA' + unique,
        'lastname': 'Test' + unique,
        'totalprice': 123,
        'depositpaid': True,
        'bookingdates': {'checkin': '2030-06-15', 'checkout': '2030-06-20'},
        'additionalneeds': 'Breakfast',
    }
    try:
        response = api.create_booking(payload)
        assert response.status_code == 200
        booking_id = response.json()['bookingid']
        assert type(booking_id) is int
        response = api.delete_booking(booking_id, auth=basic_auth)
        assert response.status_code == 201
        yield Booking(booking_id, payload)
    finally:
        response = api.get_bookings(params={'lastname': payload['lastname']})
        remaining_ids = booking_ids(response)
        errors = []
        for owned_id in remaining_ids:
            try:
                response = api.delete_booking(owned_id, auth=basic_auth)
                if response.status_code != 201:
                    errors.append(f'ID {owned_id}: HTTP {response.status_code}')
            except Exception as error:
                errors.append(f'ID {owned_id}: {error}')
        assert not errors, 'Deleted-ID cleanup failed: ' + '; '.join(errors)
