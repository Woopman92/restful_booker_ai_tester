"""Partial updates, preservation of omitted fields, boundaries and supported formats."""

from typing import Any

import pytest

from checkers.common import check_status_code
from checkers.get_booking import check_xml_booking
from checkers.partial_update_booking import PartialUpdateMismatch
from checkers.partial_update_booking import check_partial_update_response
from checkers.partial_update_booking import check_patched_booking
from checkers.update_booking import check_form_update_response
from helpers.models import Booking
from helpers.payloads import form_payload
from helpers.payloads import merge_booking_patch
from helpers.payloads import xml_payload
from tests.client import ApiClient

pytestmark = pytest.mark.positive


class TestPartialUpdateBookingContract:
    """Verify individual fields, combinations and a complete supplied payload."""

    @pytest.mark.parametrize(
        'field', ['firstname', 'lastname', 'totalprice', 'depositpaid', 'bookingdates', 'additionalneeds']
    )
    def test_single_field(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Update only one top-level field and preserve every omitted value."""
        payload = {field: replacement_payload[field]}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    def test_field_combination(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Change both names together while leaving unrelated fields intact."""
        payload = {field: replacement_payload[field] for field in ('firstname', 'lastname')}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    def test_all_fields(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Apply a complete payload through PATCH and preserve the booking ID."""
        response = api.partial_update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_partial_update_response(response, replacement_payload)
        check_patched_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.xfail(
        strict=True,
        raises=PartialUpdateMismatch,
        reason='PartialUpdateBooking documents both nested dates as optional; updating one date '
        'currently replaces the omitted date with 0NaN-aN-aN instead of preserving it.',
    )
    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    def test_single_nested_date(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Update one optional nested date without losing the other date."""
        payload = {'bookingdates': {field: replacement_payload['bookingdates'][field]}}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)


class TestPartialUpdateBookingAuthorization:
    """Exercise token authentication independently of Basic authentication."""

    def test_token_authentication(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], token: str
    ) -> None:
        """Authorize a partial name change with a newly created Cookie token."""
        payload = {'firstname': replacement_payload['firstname']}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, token=token)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)


class TestPartialUpdateBookingFields:
    """Verify supplied scalar boundaries, special strings and valid dates."""

    @pytest.mark.parametrize(
        'booking', [{'depositpaid': True}, {'depositpaid': False}],
        indirect=True,
        ids=['paid-to-unpaid', 'unpaid-to-paid']
    )
    def test_deposit_transitions(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Persist either Boolean transition when depositpaid is the only supplied field."""
        payload = {'depositpaid': not booking.payload['depositpaid']}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize('price', [-1, 0, 1], ids=['negative', 'zero', 'positive'])
    def test_integer_price(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], price: int) -> None:
        """Preserve integer values around zero without assuming an undocumented minimum."""
        payload = {'totalprice': price}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.xfail(
        strict=True,
        raises=PartialUpdateMismatch,
        reason='PartialUpdateBooking documents totalprice as Number; PATCH totalprice=123.5 '
        'currently returns and persists 123, losing the fractional part.',
    )
    def test_fractional_price(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Preserve the fractional part allowed by the documented Number type."""
        payload = {'totalprice': 123.5}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    @pytest.mark.parametrize('value', ['', 'x', " Élodie O'Neil-李 & <tea> "], ids=['empty', 'one-character', 'special'])
    def test_string_values(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], field: str, value: str
    ) -> None:
        """Preserve short strings, whitespace, Unicode and markup characters in one field."""
        payload = {field: value}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    @pytest.mark.parametrize('value', ['a' * 1024, 'Ж' * 1024], ids=['ascii-1024', 'unicode-1024'])
    @pytest.mark.current_behavior
    def test_current_long_string(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], field: str, value: str
    ) -> None:
        """Record current preservation of a 1024-character string in a single field."""
        # Expected maximum lengths are unspecified; record current behavior without truncation.
        payload = {field: value}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize(('checkin', 'checkout'), [('2028-02-29', '2028-03-01'), ('2030-12-31', '2031-01-01')],
                             ids=['leap-day', 'year-transition'])
    def test_calendar_dates(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], checkin: str, checkout: str
    ) -> None:
        """Update only the date object with valid leap-day and year-boundary intervals."""
        payload = {'bookingdates': {'checkin': checkin, 'checkout': checkout}}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)


class TestPartialUpdateBookingFormats:
    """Verify minimal XML and form inputs and documented output formats."""

    def test_xml_input(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Update only a name supplied as XML and preserve all omitted fields."""
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        expected = merge_booking_patch(booking.payload, payload)
        body = xml_payload(payload)
        response = api.partial_update_booking(booking.booking_id, body=body, content_type='text/xml', auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    def test_form_input(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Update only a name supplied as form data without injecting omitted fields."""
        payload = {'lastname': booking.payload['lastname'] + 'Changed'}
        expected = merge_booking_patch(booking.payload, payload)
        body = form_payload(payload)
        response = api.partial_update_booking(
            booking.booking_id, body=body, content_type='application/x-www-form-urlencoded', auth=basic_auth
        )
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize(
        'booking',
        [
            pytest.param({'depositpaid': True},
                         marks=pytest.mark.xfail(
                             strict=True,
                             raises=PartialUpdateMismatch,
                             reason='PartialUpdateBooking documents Boolean depositpaid and xml input; '
                             'xml depositpaid=false currently becomes true.',
                         )),
            pytest.param({'depositpaid': False}),
        ],
        indirect=True,
        ids=['paid-to-unpaid', 'unpaid-to-paid'],
    )
    def test_xml_deposit(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Preserve either Boolean transition when sent alone as xml input."""
        payload = {'depositpaid': not booking.payload['depositpaid']}
        expected = merge_booking_patch(booking.payload, payload)
        body = xml_payload(payload)
        response = api.partial_update_booking(booking.booking_id, body=body, content_type='text/xml', auth=basic_auth)
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize(
        'booking',
        [
            pytest.param({'depositpaid': True},
                         marks=pytest.mark.xfail(
                             strict=True,
                             raises=PartialUpdateMismatch,
                             reason='PartialUpdateBooking documents Boolean depositpaid and form input; '
                             'form depositpaid=false currently becomes true.',
                         )),
            pytest.param({'depositpaid': False}),
        ],
        indirect=True,
        ids=['paid-to-unpaid', 'unpaid-to-paid'],
    )
    def test_form_deposit(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Preserve either Boolean transition when sent alone as form input."""
        payload = {'depositpaid': not booking.payload['depositpaid']}
        expected = merge_booking_patch(booking.payload, payload)
        body = form_payload(payload)
        response = api.partial_update_booking(
            booking.booking_id, body=body, content_type='application/x-www-form-urlencoded', auth=basic_auth
        )
        check_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    def test_xml_output(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Return the complete XML booking after changing a single JSON field."""
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth, accept='application/xml')
        check_xml_booking(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    def test_form_output(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], request: pytest.FixtureRequest
    ) -> None:
        """Return the documented form representation after persisting a single changed field."""
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(
            booking.booking_id, payload, auth=basic_auth, accept='application/x-www-form-urlencoded'
        )
        check_status_code(response, 200)
        check_patched_booking(api, booking.booking_id, expected)
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason='PartialUpdateBooking shows a URL-encoded response; the service instead returns '
                'HTTP 200 text/html "formurlencoded is not a function", although the patch is persisted.',
            )
        )
        check_form_update_response(response, expected)
