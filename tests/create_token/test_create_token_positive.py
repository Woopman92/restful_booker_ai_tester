"""Documented token creation contract and token usability."""

import pytest

from checkers.auth import check_created_token
from checkers.bookings import check_booking_ids
from checkers.bookings import check_updated_booking
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = pytest.mark.positive


class TestCreateTokenContract:
    """Validate successful creation with configured credentials."""

    def test_create_token(self, api: ApiClient, credentials: dict[str, str]) -> None:
        """Return HTTP 200 and a string token for valid credentials."""
        response = api.create_token(payload=credentials)
        check_created_token(response)


class TestTokenUsage:
    """Verify that an issued token authorizes an operation on test-owned data."""

    def test_token_authorizes_update(self, api: ApiClient, credentials: dict[str, str], booking: Booking) -> None:
        """Update a booking with the token and confirm the change through an independent read."""
        response = api.create_token(payload=credentials)
        token = check_created_token(response)
        updated_payload = {**booking.payload, 'firstname': booking.payload['firstname'] + 'Updated'}
        response = api.update_booking(booking.booking_id, updated_payload, token)
        check_updated_booking(response, updated_payload)
        params = {'firstname': updated_payload['firstname'], 'lastname': updated_payload['lastname']}
        response = api.get_bookings(params=params)
        check_booking_ids(response, {booking.booking_id})


@pytest.mark.current_behavior
class TestTokenReissuance:
    """Record current token uniqueness and validity after a second issuance."""

    def test_current_behavior_after_token_reissuance(
        self, api: ApiClient, credentials: dict[str, str], token: str, booking: Booking
    ) -> None:
        """Issue a distinct second token and verify that both tokens still authorize updates."""
        # The expected uniqueness and revocation behavior is unspecified in the documentation.
        # This test records current behavior: tokens differ and both remain usable after reissuance.
        response = api.create_token(payload=credentials)
        second_token = check_created_token(response)
        tokens_differ = token != second_token
        assert tokens_differ, 'Repeated issuance returned the same token'

        for label, issued_token in [('Second', second_token), ('FirstAfterReissuance', token)]:
            updated_payload = {**booking.payload, 'firstname': booking.payload['firstname'] + label}
            response = api.update_booking(booking.booking_id, updated_payload, issued_token)
            check_updated_booking(response, updated_payload)
            params = {'firstname': updated_payload['firstname'], 'lastname': updated_payload['lastname']}
            response = api.get_bookings(params=params)
            check_booking_ids(response, {booking.booking_id})
