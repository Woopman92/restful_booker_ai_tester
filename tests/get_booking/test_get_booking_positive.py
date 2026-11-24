"""Documented JSON and XML booking retrieval."""

import pytest

from checkers.common import check_booking_json_response
from checkers.common import check_booking_xml_response
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = pytest.mark.positive


class TestGetBookingContract:
    """Verify the full response schema and saved booking values."""

    def test_get_booking(self, api: ApiClient, booking: Booking) -> None:
        """Read the owned booking and verify its schema and saved values."""
        response = api.get_booking(booking.booking_id)
        check_booking_json_response(response, booking.payload)

    def test_get_xml_booking(self, api: ApiClient, booking: Booking) -> None:
        """Return the owned booking as well-formed XML with all required elements."""
        response = api.get_booking(booking.booking_id, accept='application/xml')
        check_booking_xml_response(response, booking.payload)
