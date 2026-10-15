"""Additional input validation expectations where the error contract is unspecified."""

import pytest

from checkers.bookings import booking_ids
from checkers.common import check_plain_text_error
from tests.support import ApiClient
from tests.support import Booking

pytestmark = pytest.mark.negative


class TestGetBookingsInvalidDates:
    """Check invalid date handling and record behavior where the contract is unspecified."""

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    @pytest.mark.parametrize(
        'value',
        ['not-a-date', '2030-13-01', '2030-06-00'],
        ids=['not-a-date', 'invalid-month', 'zero-day'],
    )
    def test_reject_invalid_date(self, api: ApiClient, booking: Booking, field: str, value: str) -> None:
        """Record HTTP 500 for date values that the service cannot parse."""
        # The expected result is unknown: the documentation does not define handling of these values.
        # This test records the current service behavior: HTTP 500 with a plain-text error.
        params = {'firstname': booking.payload['firstname'], field: value}
        response = api.get_bookings(params=params)
        check_plain_text_error(response, expected_status_code=500)

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    @pytest.mark.parametrize(
        'value',
        ['2030-02-30', '2030-02-29', '2030/06/15'],
        ids=['impossible-day', 'non-leap-year', 'wrong-separator'],
    )
    def test_current_behavior_for_accepted_invalid_date(
        self, api: ApiClient, booking: Booking, field: str, value: str
    ) -> None:
        """Record the current successful response for invalid dates accepted by the service."""
        # The expected result is unknown: the documentation does not define handling of these values.
        # This test records the current service behavior: HTTP 200 with an array of booking IDs.
        params = {'firstname': booking.payload['firstname'], field: value}
        response = api.get_bookings(params=params)
        booking_ids(response)


class TestGetBookingsQueryInputBehavior:
    """Record current responses for query inputs with unspecified error handling."""

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    def test_current_behavior_for_boolean_string(self, api: ApiClient, booking: Booking, field: str) -> None:
        """Record HTTP 500 when a date filter contains the string true."""
        # The expected result is unknown: the documentation does not define handling of this input.
        # This test records the current service behavior: HTTP 500 with a plain-text error.
        params = {'firstname': booking.payload['firstname'], field: 'true'}
        response = api.get_bookings(params=params)
        check_plain_text_error(response, expected_status_code=500)

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    def test_current_behavior_for_repeated_date_parameter(self, api: ApiClient, booking: Booking, field: str) -> None:
        """Record HTTP 500 when a date filter appears twice in the query string."""
        # The expected result is unknown: the documentation does not define handling of repeated parameters.
        # This test records the current service behavior: HTTP 500 with a plain-text error.
        params = [('firstname', booking.payload['firstname']), (field, '2030-06-15'), (field, '2030-06-16')]
        response = api.get_bookings(params=params)
        check_plain_text_error(response, expected_status_code=500)
