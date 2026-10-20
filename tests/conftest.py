"""Function-scoped test data with guaranteed cleanup after assertions fail."""

import os
from collections.abc import Callable
from collections.abc import Iterator
from uuid import uuid4

import pytest
import requests

from constants import BASE_URL
from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME
from tests.support import ApiClient
from tests.support import Booking


@pytest.fixture(scope='session')
def api() -> Iterator[ApiClient]:
    """Provide a reusable unauthenticated HTTP session with a finite timeout.

    Yields:
        ApiClient: Shared client configured from the BOOKER_BASE_URL and
        BOOKER_TIMEOUT environment variables. The session closes at teardown.
    """
    with requests.Session() as session:
        session.headers.update({'Accept': 'application/json'})
        yield ApiClient(
            session,
            BASE_URL,
            float(os.getenv('BOOKER_TIMEOUT', '10')),
        )


@pytest.fixture
def create_booking(api: ApiClient) -> Iterator[Callable[..., Booking]]:
    """Create unique bookings and attempt deletion of every owned ID at teardown.

    Args:
        api: Client used to create and delete test-owned bookings.

    Yields:
        Callable[..., Booking]: Factory accepting optional firstname and lastname
        overrides. Every registered booking is deleted at teardown.

    Raises:
        AssertionError: Cleanup fails for one or more registered bookings.
    """
    owned_ids: list[int] = []

    def create(**overrides: str) -> Booking:
        """Create one booking, registering its ID before validating its payload.

        Args:
            **overrides: Optional firstname and lastname values. Omitted names
                are generated using a UUID.

        Returns:
            Booking: Created booking ID and its original request payload.

        Raises:
            AssertionError: The creation status, booking ID or payload is unexpected.
            requests.RequestException: The creation request fails.
            requests.exceptions.JSONDecodeError: The response is not valid JSON.
        """
        unique = uuid4().hex
        payload = {
            'firstname': overrides.get('firstname', f'QA{unique}'),
            'lastname': overrides.get('lastname', f'Test{unique}'),
            'totalprice': 123,
            'depositpaid': True,
            'bookingdates': {'checkin': '2030-06-15', 'checkout': '2030-06-20'},
            'additionalneeds': 'API test',
        }
        response = api.create_booking(payload)
        assert response.status_code == 200, f'Cannot create test data: {response.status_code}: {response.text[:500]}'
        body = response.json()
        assert type(body.get('bookingid')) is int, f'Missing integer bookingid: {body!r}'
        owned_ids.append(body['bookingid'])
        assert body.get('booking') == payload, f'Service changed test data: {body!r}'
        return Booking(body['bookingid'], payload)

    yield create

    errors = []
    for booking_id in reversed(owned_ids):
        try:
            response = api.delete_booking(
                booking_id,
                auth=(BOOKER_USERNAME, BOOKER_PASSWORD),
            )
            if response.status_code != 201:
                errors.append(f'ID {booking_id}: HTTP {response.status_code}')
        except requests.RequestException as error:
            errors.append(f'ID {booking_id}: {error}')
    assert not errors, 'Cleanup failed: ' + '; '.join(errors)


@pytest.fixture
def booking(create_booking: Callable[..., Booking]) -> Booking:
    """Create an isolated booking for the current test.

    Args:
        create_booking: Factory that creates and registers bookings for cleanup.

    Returns:
        Booking: Newly created booking with unique guest names.

    Raises:
        AssertionError: The factory receives an unexpected creation response.
        requests.RequestException: The creation request fails.
    """
    return create_booking()
