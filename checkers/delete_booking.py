"""Deletion response and resulting booking state checks."""

from requests import Response

from checkers.common import check_plain_text_error
from checkers.common import check_status_code
from tests.client import ApiClient


def check_delete_response(response: Response) -> None:
    """Check the documented deletion status and the observed plain-text representation.

    Args:
        response: Successful DELETE response.

    Raises:
        AssertionError: Status, media type or response body differs.
    """
    check_status_code(response, 201)
    # The response body and media type are unspecified; record their current representation.
    assert response.headers.get('Content-Type', '').split(';')[0] == 'text/plain'
    assert response.text == 'Created'


def check_deleted_booking(api: ApiClient, booking_id: int) -> None:
    """Read the owned ID and verify that the record is absent.

    Args:
        api: Client used for the independent read.
        booking_id: ID of the test-owned deleted booking.

    Raises:
        AssertionError: Retrieval does not return the observed plain-text 404.
        requests.RequestException: Retrieval fails.
    """
    response = api.get_booking(booking_id)
    check_plain_text_error(response, 404)
