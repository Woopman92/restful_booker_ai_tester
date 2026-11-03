"""Function-scoped test data with guaranteed cleanup after assertions fail."""

import os
from collections.abc import Callable
from collections.abc import Iterator
from copy import deepcopy
from datetime import date
from datetime import timedelta
from time import sleep
from typing import Any
from uuid import uuid4

import pytest
import requests

from checkers.common import booking_ids
from checkers.create_token import check_created_token
from checkers.delete_booking import check_deleted_booking
from constants import BASE_URL
from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME
from constants import PING_ATTEMPTS
from constants import PING_PATH
from constants import PING_RETRY_DELAY
from helpers.models import Booking
from tests.client import ApiClient


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


@pytest.fixture(scope='session', autouse=True)
def service_available(api: ApiClient) -> None:
    """Require a successful health check before running tests, allowing bounded retries.

    Args:
        api: Shared client used for the session health check.

    Raises:
        pytest.exit.Exception: Every attempt fails; stop the session with a nonzero exit code.
    """
    errors: list[str] = []
    for attempt in range(1, PING_ATTEMPTS + 1):
        try:
            response = api.ping()
        except requests.RequestException as error:
            errors.append(f'Attempt {attempt}: {type(error).__name__}: {error}')
        else:
            if response.status_code == 201:
                return
            errors.append(f'Attempt {attempt}: HTTP {response.status_code} {response.reason}')
        if attempt < PING_ATTEMPTS:
            sleep(PING_RETRY_DELAY)
    pytest.exit(
        f'Service availability check failed: {api.base_url}{PING_PATH} after {PING_ATTEMPTS} attempts.\n' +
        '\n'.join(errors),
        returncode=pytest.ExitCode.INTERRUPTED,
    )


@pytest.fixture
def token(api: ApiClient) -> str:
    """Issue a fresh authentication token for the current test.

    Args:
        api: Client used to request the token.

    Returns:
        str: Token extracted from a validated response.

    Raises:
        AssertionError: Authentication response status or schema is invalid.
        ValueError: The response is not valid JSON.
        requests.RequestException: Authentication fails at transport level.
    """
    response = api.create_token(payload={'username': BOOKER_USERNAME, 'password': BOOKER_PASSWORD})
    return check_created_token(response)


@pytest.fixture
def create_booking(api: ApiClient) -> Iterator[Callable[..., Booking]]:
    """Create unique bookings and attempt deletion of every owned ID at teardown.

    Args:
        api: Client used to create and delete test-owned bookings.

    Yields:
        Callable[..., Booking]: Factory accepting optional firstname, lastname and depositpaid
        overrides. Every registered booking is deleted at teardown; records already
        deleted by the test are confirmed absent through GET.

    Raises:
        AssertionError: Cleanup fails for one or more registered bookings.
    """
    owned_ids: list[int] = []

    def create(*, depositpaid: bool = True, **overrides: str) -> Booking:
        """Create one booking, registering its ID before validating its payload.

        Args:
            depositpaid: Initial deposit flag. Defaults to True.
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
            'depositpaid': depositpaid,
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
            if response.status_code == 405:
                check_deleted_booking(api, booking_id)
            elif response.status_code != 201:
                errors.append(f'ID {booking_id}: HTTP {response.status_code}')
        except (AssertionError, requests.RequestException) as error:
            errors.append(f'ID {booking_id}: {error}')
    assert not errors, 'Cleanup failed: ' + '; '.join(errors)


@pytest.fixture
def booking(create_booking: Callable[..., Booking], request: pytest.FixtureRequest) -> Booking:
    """Create an isolated booking for the current test.

    Args:
        create_booking: Factory that creates and registers bookings for cleanup.
        request: Optional indirect parameter mapping, such as depositpaid=False.
            Without parametrization the factory defaults are used.

    Returns:
        Booking: Newly created booking with unique guest names.

    Raises:
        AssertionError: The factory receives an unexpected creation response.
        requests.RequestException: The creation request fails.
    """
    return create_booking(**getattr(request, 'param', {}))


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
def deleted_booking(api: ApiClient, basic_auth: tuple[str, str]) -> Iterator[Booking]:
    """Provide a deleted owned ID and clean up any record unexpectedly recreated by an update.

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
