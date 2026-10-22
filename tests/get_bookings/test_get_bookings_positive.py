"""Documented success contract, optional filters and date boundaries."""

from collections.abc import Callable
from datetime import date
from datetime import timedelta

import pytest

from checkers.bookings import check_booking_ids
from checkers.bookings import check_booking_presence
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = pytest.mark.positive


class TestGetBookingsContract:
    """Validate the list response without assumptions about public database contents."""

    def test_list_contains_created_booking(self, api: ApiClient, booking: Booking) -> None:
        """Return a unique ID array containing the booking created by this test."""
        response = api.get_bookings()
        check_booking_presence(response, booking.booking_id)


class TestGetBookingsNameFilters:
    """Verify individual filters, their intersection, and exact name matching."""

    @pytest.mark.parametrize('fields', [('firstname', ), ('lastname', ), ('firstname', 'lastname')])
    def test_filter_names(self, api: ApiClient, booking: Booking, fields: tuple[str, ...]) -> None:
        """Return exactly the owned booking for its unique name filters."""
        params = {field: booking.payload[field] for field in fields}
        response = api.get_bookings(params=params)
        check_booking_ids(response, {booking.booking_id})

    def test_filters_are_combined(self, api: ApiClient, create_booking: Callable[..., Booking]) -> None:
        """Exclude bookings matching only one of two name filters."""
        target = create_booking()
        create_booking(firstname=target.payload['firstname'])
        create_booking(lastname=target.payload['lastname'])
        params = {field: target.payload[field] for field in ('firstname', 'lastname')}
        response = api.get_bookings(params=params)
        check_booking_ids(response, {target.booking_id})

    @pytest.mark.parametrize('field', ['firstname', 'lastname'])
    def test_no_matching_name(self, api: ApiClient, booking: Booking, field: str) -> None:
        """Return an empty array for a valid name with no matching booking."""
        params = {field: booking.payload[field] + 'Absent'}
        response = api.get_bookings(params=params)
        check_booking_ids(response, set())

    def test_names_are_not_prefix_search(self, api: ApiClient, booking: Booking) -> None:
        """Exclude the owned booking when only a prefix of its name is provided."""
        params = {'firstname': booking.payload['firstname'][:-1], 'lastname': booking.payload['lastname']}
        response = api.get_bookings(params=params)
        check_booking_ids(response, set())


class TestGetBookingsDateFilters:
    """Check the documented inclusive lower bound for both date filters."""

    @pytest.mark.parametrize(
        ('field', 'offset', 'expected_present'),
        [('checkin', -1, True), ('checkout', 0, True), ('checkin', 1, False)],
        ids=['checkin-day-before', 'checkout-equal', 'checkin-day-after'],
    )
    def test_date_boundary(
        self, api: ApiClient, booking: Booking, field: str, offset: int, expected_present: bool
    ) -> None:
        """Check date boundaries where the service follows the documented contract."""
        boundary = date.fromisoformat(booking.payload['bookingdates'][field]) + timedelta(days=offset)
        response = api.get_bookings(params={field: boundary.isoformat()})
        check_booking_presence(response, booking.booking_id, expected_present)

    @pytest.mark.parametrize(
        ('field', 'offset', 'expected_present'),
        [('checkin', 0, True), ('checkout', -1, True), ('checkout', 1, False)],
        ids=['checkin-equal', 'checkout-day-before', 'checkout-day-after'],
    )
    def test_date_boundary_contract_mismatch(
        self,
        api: ApiClient,
        booking: Booking,
        field: str,
        offset: int,
        expected_present: bool,
        request: pytest.FixtureRequest
    ) -> None:
        """Check documented boundaries with confirmed filtering discrepancies."""
        boundary = date.fromisoformat(booking.payload['bookingdates'][field]) + timedelta(days=offset)
        response = api.get_bookings(params={field: boundary.isoformat()})
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason=f'GetBookings documents {field} >= filter date. '
                'Observed: checkin excludes equality; checkout excludes a booking after the filter '
                'and includes a booking before it. Confirmed against the public API.',
            )
        )
        check_booking_presence(response, booking.booking_id, expected_present)

    def test_all_filters_together(self, api: ApiClient, booking: Booking, request: pytest.FixtureRequest) -> None:
        """Apply both name filters and both documented date lower bounds together."""
        params = {
            'firstname': booking.payload['firstname'],
            'lastname': booking.payload['lastname'],
            'checkin': '2030-06-14',
            'checkout': '2030-06-19',
        }
        response = api.get_bookings(params=params)
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason='GetBookings documents checkout >= filter date; all four matching filters return [] '
                'for a booking with checkout 2030-06-20 and checkout filter 2030-06-19.',
            )
        )
        check_booking_ids(response, {booking.booking_id})
