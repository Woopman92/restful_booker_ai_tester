"""Documented Basic and Cookie deletion with independent absence checks."""

from collections.abc import Callable

import pytest

from checkers.bookings import check_booking
from checkers.delete_booking import check_delete_response
from checkers.delete_booking import check_deleted_booking
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = pytest.mark.positive


class TestDeleteBookingContract:
    """Verify deletion of exactly the targeted booking with Basic authentication."""

    def test_delete_booking(
        self, api: ApiClient, booking: Booking, create_booking: Callable[..., Booking], basic_auth: tuple[str, str]
    ) -> None:
        """Delete the target, confirm its absence and preserve a separate owned booking."""
        control_booking = create_booking()
        response = api.delete_booking(booking.booking_id, auth=basic_auth)
        check_delete_response(response)
        check_deleted_booking(api, booking.booking_id)
        check_booking(api, control_booking.booking_id, control_booking.payload)


class TestDeleteBookingAuthorization:
    """Verify deletion using only a newly issued Cookie token."""

    def test_token_authentication(self, api: ApiClient, booking: Booking, token: str) -> None:
        """Delete the owned record using a token without Basic authentication fallback."""
        response = api.delete_booking(booking.booking_id, token=token)
        check_delete_response(response)
        check_deleted_booking(api, booking.booking_id)
