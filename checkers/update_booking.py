"""Update response, persistence and observed invalid-input checks."""

from typing import Any

from requests import Response

from checkers.common import _check_booking_values
from checkers.common import _check_current_booking_values
from checkers.common import check_booking_schema
from tests.client import ApiClient


def check_update_response_schema(response: Response) -> None:
    """Check the JSON media type and full booking schema.

    Args:
        response: Update response whose values will be checked separately.

    Raises:
        AssertionError: Media type or required field types are invalid.
        ValueError: JSON or a calendar date is invalid.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    check_booking_schema(response.json())


def check_update_values(response: Response, expected_payload: dict[str, Any]) -> None:
    """Check replacement values after the response schema has been validated.

    Args:
        response: JSON update response.
        expected_payload: Exact expected replacement fields.

    Raises:
        AssertionError: Required booking fields or JSON types are invalid.
        ResponseValuesMismatch: Response field values differ.
        ValueError: The body is not valid JSON.
    """
    _check_booking_values(response.json(), expected_payload)


def check_update_booking_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Validate the documented update response and all replacement values.

    Args:
        response: Full update response.
        expected_payload: Complete expected booking payload.

    Raises:
        AssertionError: Schema or booking values differ.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    check_update_response_schema(response)
    check_update_values(response, expected_payload)


def check_current_update_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Record an invalid-input response without imposing the valid-input field schema.

    Args:
        response: JSON response to an update or a subsequent retrieval.
        expected_payload: Currently observed fields, including malformed values.

    Raises:
        AssertionError: Media type, object structure or observed values differ.
        ValueError: The response is not valid JSON.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    assert isinstance(response.json(), dict)
    _check_current_booking_values(response.json(), expected_payload)


def check_current_saved_booking(api: ApiClient, booking_id: int, expected_payload: dict[str, Any]) -> None:
    """Read and compare observed persisted values after an invalid request is accepted.

    Args:
        api: Client used for retrieval.
        booking_id: ID of the owned booking.
        expected_payload: Observed persisted fields, possibly outside the documented schema.

    Raises:
        AssertionError: Saved values or the response envelope differ.
        ValueError: The response is not valid JSON.
        requests.RequestException: Retrieval fails at transport level.
    """
    response = api.get_booking(booking_id)
    check_current_update_response(response, expected_payload)
