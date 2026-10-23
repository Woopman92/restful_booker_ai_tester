"""Partial-update response, schema and persistence checks."""

from typing import Any

from requests import Response

from checkers.common import check_status_code
from checkers.get_booking import check_booking_schema
from tests.client import ApiClient


class PartialUpdateMismatch(AssertionError):
    """Identify contract value mismatches separately from transport or schema errors."""


def check_partial_update_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Check all fields, including values that should remain unchanged after PATCH.

    Args:
        response: JSON response to the partial update or its independent retrieval.
        expected_payload: Full expected booking state.

    Raises:
        PartialUpdateMismatch: A booking value or its type differs.
        AssertionError: Status, media type or schema is invalid.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    check_current_partial_update_response(response, expected_payload)
    check_booking_schema(response.json())


def check_current_partial_update_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Compare observed invalid-input results without requiring valid booking field types.

    Args:
        response: JSON response from PATCH or GET.
        expected_payload: Full observed state, possibly containing invalid values.

    Raises:
        PartialUpdateMismatch: Fields or their types differ from the expected state.
        AssertionError: Status, media type or object structure is invalid.
        ValueError: The response is not JSON.
    """
    check_status_code(response, 200)
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    actual = response.json()
    assert isinstance(actual, dict)
    try:
        assert actual == expected_payload
        for name, value in expected_payload.items():
            assert type(actual[name]) is type(value), f'Unexpected type for {name}'
    except AssertionError as error:
        raise PartialUpdateMismatch(str(error)) from error


def check_patched_booking(api: ApiClient, booking_id: int, expected_payload: dict[str, Any]) -> None:
    """Read the owned record and check its full valid schema and expected state.

    Args:
        api: Client used for the independent retrieval.
        booking_id: ID of the test-owned booking.
        expected_payload: Full expected booking state after PATCH.

    Raises:
        AssertionError: Status, schema or persisted values differ.
        ValueError: JSON or a calendar date cannot be parsed.
        requests.RequestException: Retrieval fails.
    """
    response = api.get_booking(booking_id)
    check_partial_update_response(response, expected_payload)


def check_current_patched_booking(api: ApiClient, booking_id: int, expected_payload: dict[str, Any]) -> None:
    """Read persisted invalid-input results without imposing the valid-input schema.

    Args:
        api: Client used for the independent retrieval.
        booking_id: ID of the test-owned booking.
        expected_payload: Full observed state after the request.

    Raises:
        AssertionError: Response metadata or persisted values differ.
        ValueError: The response is not JSON.
        requests.RequestException: Retrieval fails.
    """
    response = api.get_booking(booking_id)
    check_current_partial_update_response(response, expected_payload)


def check_serialization_error(response: Response, expected_message: str) -> None:
    """Record a successful HTTP status carrying an unstructured serialization error.

    Args:
        response: PATCH or GET response for a record with null bookingdates.
        expected_message: Observed serialization error text.

    Raises:
        AssertionError: Status, media type or error message differs.
    """
    check_status_code(response, 200)
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
