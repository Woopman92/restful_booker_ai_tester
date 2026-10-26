"""Current invalid-input behavior and persisted state after failed or accepted PUT requests."""

import json
from copy import deepcopy
from typing import Any

import pytest

from checkers.bookings import check_booking
from checkers.bookings import check_booking_ids
from checkers.common import check_plain_text_error
from checkers.update_booking import check_current_saved_booking
from checkers.update_booking import check_current_update_response
from helpers.models import Booking
from tests.client import ApiClient

pytestmark = pytest.mark.negative


class TestUpdateBookingInvalidAuth:
    """Record authentication failures and verify the original booking remains intact."""

    def test_missing_auth(self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any]) -> None:
        """Record rejection of an update without either authentication mechanism."""
        # Error handling is unspecified; record HTTP 403 with no persisted update.
        response = api.update_booking(booking.booking_id, replacement_payload)
        check_plain_text_error(response, expected_status_code=403)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('invalid_token', ['', 'invalid'], ids=['empty-token', 'unknown-token'])
    def test_invalid_token(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], invalid_token: str
    ) -> None:
        """Record rejection of an empty or unknown Cookie token without Basic fallback."""
        # Error handling is unspecified; record HTTP 403 with no persisted update.
        response = api.update_booking(booking.booking_id, replacement_payload, token=invalid_token)
        check_plain_text_error(response, expected_status_code=403)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('field', ['username', 'password'])
    def test_invalid_basic_credentials(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Record rejection when either Basic credential is incorrect."""
        # Error handling is unspecified; record HTTP 403 with no persisted update.
        credentials = dict(zip(('username', 'password'), basic_auth))
        credentials[field] += 'Invalid'
        auth = credentials['username'], credentials['password']
        response = api.update_booking(booking.booking_id, replacement_payload, auth=auth)
        check_plain_text_error(response, expected_status_code=403)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('authorization', ['Bearer invalid', 'Basic !!!'], ids=['wrong-scheme', 'malformed-basic'])
    def test_malformed_authorization(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], authorization: str
    ) -> None:
        """Record rejection of unsupported or malformed Authorization headers."""
        # Error handling is unspecified; record HTTP 403 with no persisted update.
        response = api.update_booking(booking.booking_id, replacement_payload, authorization=authorization)
        check_plain_text_error(response, expected_status_code=403)
        check_booking(api, booking.booking_id, booking.payload)


class TestUpdateBookingMissingFields:
    """Record mandatory field omissions and the observed treatment of additionalneeds."""

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'totalprice', 'depositpaid', 'bookingdates'])
    def test_missing_field(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Record rejection of incomplete full replacements."""
        # Error handling is unspecified; record HTTP 400 with the original record preserved.
        del replacement_payload[field]
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    def test_missing_nested_date(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Record rejection when one mandatory nested date is absent."""
        # Error handling is unspecified; record HTTP 400 with no persisted update.
        del replacement_payload['bookingdates'][field]
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    def test_missing_additionalneeds(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Record retention of the original additionalneeds when the field is omitted."""
        # Invalid-input handling is unspecified; other fields change but the original additionalneeds remains.
        del replacement_payload['additionalneeds']
        expected = {**replacement_payload, 'additionalneeds': booking.payload['additionalneeds']}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, expected)
        check_current_saved_booking(api, booking.booking_id, expected)


class TestUpdateBookingInvalidTypes:
    """Keep rejected nulls separate from accepted coercions and server errors."""

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'totalprice', 'depositpaid', 'bookingdates'])
    def test_null_field(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Record rejection of null in validated mandatory fields."""
        # Error handling is unspecified; record HTTP 400 with the original booking unchanged.
        replacement_payload[field] = None
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    def test_null_nested_date(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str
    ) -> None:
        """Record rejection of a null nested date."""
        # Error handling is unspecified; record HTTP 400 with no persisted update.
        replacement_payload['bookingdates'][field] = None
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('field', ['firstname', 'lastname'])
    @pytest.mark.parametrize('value', [123, True, [], {}], ids=['number', 'boolean', 'array', 'object'])
    def test_invalid_name_type(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str,
        value: Any
    ) -> None:
        """Record current server errors for non-null non-string names."""
        # Error handling is unspecified; record HTTP 500 without a partial update.
        replacement_payload[field] = value
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=500)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('value', [None, 123, True, [], {}], ids=['null', 'number', 'boolean', 'array', 'object'])
    def test_unvalidated_additionalneeds(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        value: Any
    ) -> None:
        """Record acceptance of additionalneeds outside the documented String type."""
        # Invalid-input handling is unspecified; record acceptance and persistence of the supplied value.
        replacement_payload['additionalneeds'] = value
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, replacement_payload)
        check_current_saved_booking(api, booking.booking_id, replacement_payload)

    @pytest.mark.parametrize('value', ['bad', True, [], {}], ids=['string', 'boolean', 'array', 'object'])
    def test_price_coerced_to_null(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        value: Any
    ) -> None:
        """Record JSON null produced from invalid non-null prices."""
        # Invalid-input handling is unspecified; record the current null price in the response and GET.
        replacement_payload['totalprice'] = value
        expected = {**replacement_payload, 'totalprice': None}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, expected)
        check_current_saved_booking(api, booking.booking_id, expected)

    def test_numeric_string_price(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Record conversion of a numeric string to an integer."""
        # Invalid-input handling is unspecified; record the observed conversion.
        replacement_payload['totalprice'] = '123'
        expected = {**replacement_payload, 'totalprice': 123}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, expected)
        check_current_saved_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [('false', True), (0, False), ([], True), ({}, True)],
        ids=['string', 'number', 'array', 'object'],
    )
    def test_deposit_coercion(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        value: Any,
        expected: bool
    ) -> None:
        """Record conversion of non-boolean deposit values."""
        # Invalid-input handling is unspecified; record the currently observed boolean conversions.
        replacement_payload['depositpaid'] = value
        expected_payload = {**replacement_payload, 'depositpaid': expected}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, expected_payload)
        check_current_saved_booking(api, booking.booking_id, expected_payload)

    @pytest.mark.parametrize('value', [[], 'invalid'], ids=['array', 'string'])
    def test_invalid_dates_object(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        value: Any
    ) -> None:
        """Record rejection of non-object bookingdates values."""
        # Error handling is unspecified; record HTTP 400 with no persisted update.
        replacement_payload['bookingdates'] = value
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)


class TestUpdateBookingInvalidDates:
    """Record normalization and undefined interval handling after full replacement."""

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    @pytest.mark.parametrize(
        ('value', 'expected'),
        [('2030-02-30', '2030-03-02'), ('2030-02-29', '2030-03-01'), ('2030/06/15', '2030-06-15'),
         ('not-a-date', '0NaN-aN-aN'), ('2030-13-01', '0NaN-aN-aN'), ('2030-06-00', '0NaN-aN-aN')],
        ids=['impossible-day', 'non-leap-year', 'wrong-separator', 'not-a-date', 'invalid-month', 'zero-day'],
    )
    def test_invalid_date_values(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        field: str,
        value: str,
        expected: str
    ) -> None:
        """Record normalization of invalid dates or the current unparseable-date placeholder."""
        # Invalid-input handling is unspecified; record current response and persisted date representations.
        replacement_payload['bookingdates'][field] = value
        expected_payload = {
            **replacement_payload,
            'bookingdates': {**replacement_payload['bookingdates'], field: expected},
        }
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, expected_payload)
        check_current_saved_booking(api, booking.booking_id, expected_payload)

    @pytest.mark.parametrize(
        ('checkin', 'checkout'),
        [('2031-07-01', '2031-07-01'), ('2031-07-01', '2031-06-30')],
        ids=['equal-dates', 'reversed-interval'],
    )
    def test_undefined_interval(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        checkin: str,
        checkout: str
    ) -> None:
        """Record acceptance of equal dates and a checkout preceding checkin."""
        # The interval relation is unspecified; record current acceptance of these replacements.
        replacement_payload['bookingdates'] = {'checkin': checkin, 'checkout': checkout}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, replacement_payload)
        check_current_saved_booking(api, booking.booking_id, replacement_payload)


class TestUpdateBookingInvalidPayload:
    """Record body parser errors, unknown fields and content negotiation side effects."""

    def test_empty_body(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record rejection of an empty replacement body."""
        # Error handling is unspecified; record HTTP 400 without a persisted update.
        response = api.update_booking(booking.booking_id, body='', auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize(
        ('body', 'content_type'),
        [('{"firstname":', 'application/json'), ('<booking>', 'text/xml')],
        ids=['malformed-json', 'malformed-xml'],
    )
    def test_malformed_body(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], body: str, content_type: str
    ) -> None:
        """Record parser errors before the original booking is changed."""
        # Error handling is unspecified; record HTTP 400 without a persisted update.
        response = api.update_booking(booking.booking_id, body=body, content_type=content_type, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('content_type', ['text/plain', None], ids=['unsupported', 'absent'])
    def test_unparsed_content_type(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        content_type: str | None
    ) -> None:
        """Record rejection of JSON text sent without a supported Content-Type."""
        # Error handling is unspecified; record HTTP 400 without a persisted update.
        body = json.dumps(replacement_payload)
        response = api.update_booking(booking.booking_id, body=body, content_type=content_type, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=400)
        check_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('accept', ['application/pdf', None], ids=['unsupported', 'absent'])
    def test_unusable_accept(
        self,
        api: ApiClient,
        booking: Booking,
        replacement_payload: dict[str, Any],
        basic_auth: tuple[str, str],
        accept: str | None
    ) -> None:
        """Record a 418 response that occurs after the replacement is already saved."""
        # Error handling is unspecified; record HTTP 418 while all replacement fields are persisted.
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth, accept=accept)
        check_plain_text_error(response, expected_status_code=418)
        check_booking(api, booking.booking_id, replacement_payload)

    def test_unknown_field(
        self, api: ApiClient, booking: Booking, replacement_payload: dict[str, Any], basic_auth: tuple[str, str]
    ) -> None:
        """Record omission of an unrecognized field from the update response and saved record."""
        # Unknown-field handling is unspecified; record the current omission of this field.
        replacement_payload['unknown'] = 'extra'
        expected = {key: value for key, value in replacement_payload.items() if key != 'unknown'}
        response = api.update_booking(booking.booking_id, replacement_payload, auth=basic_auth)
        check_current_update_response(response, expected)
        check_current_saved_booking(api, booking.booking_id, expected)


class TestUpdateBookingMissingId:
    """Modify only a previously deleted owned ID, never a random public record."""

    def test_deleted_id(self, api: ApiClient, deleted_booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record rejection of a deleted ID and verify that no replacement was created."""
        # Missing-ID handling is unspecified; record HTTP 405 and no resurrected or newly created booking.
        payload = deepcopy(deleted_booking.payload)
        payload['firstname'] += 'Updated'
        response = api.update_booking(deleted_booking.booking_id, payload, auth=basic_auth)
        check_plain_text_error(response, expected_status_code=405)
        response = api.get_bookings(params={'lastname': payload['lastname']})
        check_booking_ids(response, set())
