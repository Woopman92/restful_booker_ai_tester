"""Observed retrieval failures where the documentation specifies no error responses."""

import pytest

from checkers.common import check_plain_text_error
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = [pytest.mark.negative, pytest.mark.current_behavior]


class TestMissingBooking:
    """Record the response for a previously deleted test-owned booking."""

    def test_deleted_booking(self, api: ApiClient, deleted_booking: Booking) -> None:
        """Return the observed plain-text 404 without leaking another booking."""
        # The expected error result is unspecified; record current behavior: HTTP 404 with Not Found.
        response = api.get_booking(deleted_booking.booking_id)
        check_plain_text_error(response, expected_status_code=404)


class TestInvalidBookingId:
    """Record boundary and malformed path ID handling."""

    @pytest.mark.parametrize(
        'booking_id', ['not-an-id', '0', '-1', '0.5'], ids=['non-numeric', 'zero', 'negative', 'fractional']
    )
    def test_invalid_id(self, api: ApiClient, booking: Booking, booking_id: str) -> None:
        """Record the response to an ID outside the tested valid ID class."""
        # ID constraints and error responses are unspecified; record current behavior: HTTP 404.
        response = api.get_booking(booking_id)
        check_plain_text_error(response, expected_status_code=404)


class TestUnsupportedAccept:
    """Record media negotiation errors without changing the shared session."""

    def test_unsupported_accept(self, api: ApiClient, booking: Booking) -> None:
        """Record the current response to an unsupported Accept media type."""
        # The expected error result is unspecified; record current behavior: HTTP 418 with a plain-text error.
        response = api.get_booking(booking.booking_id, accept='application/pdf')
        check_plain_text_error(response, expected_status_code=418)
