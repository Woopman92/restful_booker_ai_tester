"""Data for reading an ID that belongs to a deleted test-owned booking."""

from collections.abc import Iterator
from uuid import uuid4

import pytest

from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME
from tests.client import ApiClient


@pytest.fixture
def deleted_booking_id(api: ApiClient) -> Iterator[int]:
    """Create and delete an owned booking without leaving duplicate teardown work.

    Args:
        api: Client used for creating and deleting the isolated record.

    Yields:
        int: ID of a booking deleted by this fixture.

    Raises:
        AssertionError: Creation or deletion fails.
        requests.RequestException: A setup or cleanup request fails.
        ValueError: The creation response is not valid JSON.
    """
    unique = uuid4().hex
    payload = {
        'firstname': f'QA{unique}',
        'lastname': f'Test{unique}',
        'totalprice': 123,
        'depositpaid': True,
        'bookingdates': {'checkin': '2030-06-15', 'checkout': '2030-06-20'},
        'additionalneeds': 'Deleted booking read test',
    }
    response = api.create_booking(payload)
    assert response.status_code == 200, 'Cannot create owned booking'
    body = response.json()
    assert type(body.get('bookingid')) is int
    booking_id = body['bookingid']
    deleted = False
    try:
        response = api.delete_booking(booking_id, auth=(BOOKER_USERNAME, BOOKER_PASSWORD))
        deleted = response.status_code == 201
        assert deleted, f'Cannot delete owned booking {booking_id}: HTTP {response.status_code}'
        yield booking_id
    finally:
        if not deleted:
            response = api.delete_booking(booking_id, auth=(BOOKER_USERNAME, BOOKER_PASSWORD))
            assert response.status_code == 201, f'Cleanup failed for owned booking {booking_id}'
