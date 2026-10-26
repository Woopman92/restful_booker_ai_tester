"""Full replacement, authentication, valid boundaries and response formats."""

from typing import Any

import pytest

from checkers.bookings import check_booking
from checkers.common import check_status_code
from checkers.get_booking import check_xml_booking
from checkers.update_booking import UpdateValuesMismatch
from checkers.update_booking import check_form_update_response
from checkers.update_booking import check_update_booking_response
from checkers.update_booking import check_update_response_schema
from checkers.update_booking import check_update_values
from helpers.models import Booking
from helpers.payloads import form_payload
from helpers.payloads import xml_payload
from tests.client import ApiClient

pytestmark = pytest.mark.positive


class TestUpdateBookingContract:
    """Verify complete replacement and repeated identical PUT operations."""

    def test_full_update(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Replace every field with Basic authentication and preserve the original booking ID."""
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    def test_repeated_update(self, api: ApiClient, updated_booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Repeat the fixture's valid PUT and verify the same persisted replacement state."""
        response = api.update_booking(updated_booking.booking_id, updated_booking.payload, auth=basic_auth)
        check_update_booking_response(response, updated_booking.payload)
        check_booking(api, updated_booking.booking_id, updated_booking.payload)


class TestUpdateBookingAuthorization:
    """Verify token authentication separately from the Basic-authenticated contract test."""

    def test_token_authentication(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], token: str
    ) -> None:
        """Authorize a complete replacement using only a newly issued Cookie token."""
        response = api.update_booking(booking.booking_id, replacement_payload, token=token)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)


class TestUpdateBookingValues:
    """Check valid field types and boundaries without invented business constraints."""

    @pytest.mark.parametrize(
        'booking',
        [{'depositpaid': True}, {'depositpaid': False}],
        indirect=True,
        ids=['paid-to-unpaid', 'unpaid-to-paid'],
    )
    def test_deposit_transitions(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Invert the initial deposit flag with one PUT and verify the persisted value."""
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.parametrize('price', [-1, 0, 1], ids=['negative', 'zero', 'positive'])
    def test_integer_price(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        price: int
    ) -> None:
        """Persist numeric values around zero without assuming a nonnegative price requirement."""
        replacement_payload['totalprice'] = price
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    def test_fractional_price(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        request: pytest.FixtureRequest
    ) -> None:
        """Preserve the fractional part allowed by the documented Number type."""
        replacement_payload['totalprice'] = 123.5
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_response_schema(response)
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason='UpdateBooking documents totalprice as Number without an integer restriction; '
                'PUT totalprice=123.5 currently returns 123, and subsequent GET also returns 123.',
            )
        )
        check_update_values(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    @pytest.mark.parametrize('value', ['', 'x'], ids=['empty', 'one-character'])
    def test_short_strings(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str,
        value: str
    ) -> None:
        """Persist empty and one-character strings without an undocumented minimum length."""
        replacement_payload[field] = value
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    def test_special_strings(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Preserve Unicode, spaces, apostrophes, hyphens and markup characters."""
        replacement_payload['firstname'] += " Élodie O'Neil-李"
        replacement_payload['additionalneeds'] = 'Завтрак & tea <without sugar>'
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    @pytest.mark.parametrize('value', ['a' * 1024, 'Ж' * 1024], ids=['ascii-1024', 'unicode-1024'])
    def test_current_long_string(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        value: str,
        field: str
    ) -> None:
        """Record preservation of an exploratory 1024-character value in each string field."""
        # Maximum lengths are unspecified; record current acceptance without truncation.
        replacement_payload[field] = value
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.parametrize(
        ('checkin', 'checkout'),
        [('2028-02-29', '2028-03-01'), ('2030-12-31', '2031-01-01')],
        ids=['leap-day', 'year-transition'],
    )
    def test_calendar_dates(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        checkin: str,
        checkout: str
    ) -> None:
        """Preserve valid leap-day and year-boundary intervals."""
        replacement_payload['bookingdates'] = {'checkin': checkin, 'checkout': checkout}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_update_booking_response(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)


class TestUpdateBookingFormats:
    """Check the documented XML and form request and response formats."""

    @pytest.mark.parametrize(
        'booking',
        [
            pytest.param({'depositpaid': True},
                         marks=pytest.mark.xfail(
                             strict=True,
                             raises=UpdateValuesMismatch,
                             reason=(
                                 'UpdateBooking documents Boolean depositpaid and XML input; '
                                 'XML depositpaid=false currently becomes true.'
                             ),
                         )),
            pytest.param({'depositpaid': False}),
        ],
        indirect=True,
        ids=['paid-to-unpaid', 'unpaid-to-paid'],
    )
    def test_xml_input(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Preserve either deposit flag supplied in a valid XML replacement."""
        body = xml_payload(replacement_payload)
        response = api.update_booking(booking.booking_id, body=body, content_type='text/xml', auth=basic_auth)
        check_update_response_schema(response)
        check_update_values(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    def test_xml_output(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Return an XML booking after a JSON replacement and persist all replacement fields."""
        response = api.update_booking(
            booking.booking_id, replacement_payload, auth=basic_auth, accept='application/xml'
        )
        check_xml_booking(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.parametrize(
        'booking',
        [
            pytest.param({'depositpaid': True},
                         marks=pytest.mark.xfail(
                             strict=True,
                             raises=UpdateValuesMismatch,
                             reason=(
                                 'UpdateBooking documents Boolean depositpaid and form input; '
                                 'form depositpaid=false currently becomes true.'
                             ),
                         )),
            pytest.param({'depositpaid': False}),
        ],
        indirect=True,
        ids=['paid-to-unpaid', 'unpaid-to-paid'],
    )
    def test_form_input(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Preserve either deposit flag supplied in a form replacement."""
        body = form_payload(replacement_payload)
        response = api.update_booking(
            booking.booking_id,
            body=body,
            content_type='application/x-www-form-urlencoded',
            auth=basic_auth,
        )
        check_update_response_schema(response)
        check_update_values(response, replacement_payload)
        check_booking(api, booking.booking_id, replacement_payload)

    def test_form_output(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        request: pytest.FixtureRequest
    ) -> None:
        """Return the documented URL-encoded response after persisting the replacement."""
        response = api.update_booking(
            booking.booking_id,
            replacement_payload,
            auth=basic_auth,
            accept='application/x-www-form-urlencoded',
        )
        check_status_code(response, 200)
        check_booking(api, booking.booking_id, replacement_payload)
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason='UpdateBooking documents a URL-encoded response example; the current body is '
                '"formurlencoded is not a function" with HTTP 200 text/html, although the update is persisted.',
            )
        )
        check_form_update_response(response, replacement_payload)
