"""Observed authentication failures, repeated deletion and safe malformed ID handling."""

import pytest

from checkers.common import check_booking
from checkers.common import check_plain_text_error
from checkers.delete_booking import check_delete_response
from checkers.delete_booking import check_deleted_booking
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = [pytest.mark.negative, pytest.mark.current_behavior]


class TestDeleteBookingInvalidAuth:
    """Record rejection of unauthenticated requests and preservation of the target."""

    def test_missing_auth(self, api: ApiClient, booking: Booking) -> None:
        """Record rejection when neither authentication mechanism is supplied."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged booking data.
        response = api.delete_booking(booking.booking_id)
        check_plain_text_error(response, 403)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('invalid_token', ['', 'invalid'], ids=['empty-token', 'unknown-token'])
    def test_invalid_token(self, api: ApiClient, booking: Booking, invalid_token: str) -> None:
        """Record rejection of empty and unknown Cookie tokens without Basic fallback."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged booking data.
        response = api.delete_booking(booking.booking_id, token=invalid_token)
        check_plain_text_error(response, 403)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('field', ['username', 'password'])
    def test_invalid_basic_credentials(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], field: str
    ) -> None:
        """Record rejection when either Basic credential is incorrect."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged booking data.
        credentials = dict(zip(('username', 'password'), basic_auth))
        credentials[field] += 'Invalid'
        auth = credentials['username'], credentials['password']
        response = api.delete_booking(booking.booking_id, auth=auth)
        check_plain_text_error(response, 403)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('authorization', ['Bearer invalid', 'Basic !!!'], ids=['wrong-scheme', 'malformed-basic'])
    def test_malformed_authorization(self, api: ApiClient, booking: Booking, authorization: str) -> None:
        """Record rejection of unsupported and malformed Authorization headers."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged booking data.
        response = api.delete_booking(booking.booking_id, authorization=authorization)
        check_plain_text_error(response, 403)
        check_booking(api, booking.booking_id, booking.payload)


class TestDeleteBookingMissingId:
    """Use a previously deleted owned ID to investigate repeat deletion."""

    def test_repeated_delete(self, api: ApiClient, deleted_booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record a second DELETE returning 405 while the original record remains absent."""
        # Expected repeat-deletion handling is unspecified; record current HTTP 405 and continued absence.
        response = api.delete_booking(deleted_booking.booking_id, auth=basic_auth)
        check_plain_text_error(response, 405)
        check_deleted_booking(api, deleted_booking.booking_id)


class TestDeleteBookingInvalidId:
    """Use nonnumeric text or a numeric prefix belonging only to this test's record."""

    def test_non_numeric_id(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record rejection of alphabetic text that cannot resolve to a numeric booking ID."""
        # Expected invalid-ID handling is unspecified; record current HTTP 405 without deleting the owned record.
        # The service parses IDs as integers; text without a numeric prefix cannot identify an existing booking.
        response = api.delete_booking('not-an-id', auth=basic_auth)
        check_plain_text_error(response, 405)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('suffix', ['.5', 'invalid'], ids=['fractional', 'text-suffix'])
    def test_current_numeric_prefix(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], suffix: str
    ) -> None:
        """Record deletion of the owned integer ID when trailing text is ignored."""
        # Expected ID-format handling is unspecified; record current acceptance of the owned numeric prefix.
        booking_id = f'{booking.booking_id}{suffix}'
        response = api.delete_booking(booking_id, auth=basic_auth)
        check_delete_response(response)
        check_deleted_booking(api, booking.booking_id)
