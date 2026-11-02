"""Observed invalid PATCH inputs, authentication failures and persistence side effects."""

import json
from copy import deepcopy
from typing import Any

import pytest

from checkers.bookings import check_booking_ids
from checkers.common import check_plain_text_error
from checkers.partial_update_booking import check_current_partial_update_response
from checkers.partial_update_booking import check_current_patched_booking
from checkers.partial_update_booking import check_patched_booking
from checkers.partial_update_booking import check_serialization_error
from checkers.partial_update_booking import check_unreadable_booking
from helpers.models import Booking
from helpers.payloads import merge_booking_patch
from tests.client import ApiClient

pytestmark = [pytest.mark.negative, pytest.mark.current_behavior]


class TestPartialUpdateBookingInvalidAuth:
    """Check authentication failures without relying on tokens in the shared session."""

    def test_missing_auth(self, api: ApiClient, booking: Booking) -> None:
        """Record rejection of a partial update without authentication."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged data.
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        response = api.partial_update_booking(booking.booking_id, payload)
        check_plain_text_error(response, 403)
        check_patched_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('token', ['', 'invalid'], ids=['empty-token', 'unknown-token'])
    def test_invalid_token(self, api: ApiClient, booking: Booking, token: str) -> None:
        """Record rejection of empty and unknown Cookie tokens."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged data.
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        response = api.partial_update_booking(booking.booking_id, payload, token=token)
        check_plain_text_error(response, 403)
        check_patched_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('field', ['username', 'password'])
    def test_invalid_basic_credentials(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], field: str
    ) -> None:
        """Record rejection when either Basic credential is wrong."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged data.
        credentials = dict(zip(('username', 'password'), basic_auth))
        credentials[field] += 'Invalid'
        auth = credentials['username'], credentials['password']
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        response = api.partial_update_booking(booking.booking_id, payload, auth=auth)
        check_plain_text_error(response, 403)
        check_patched_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('authorization', ['Bearer invalid', 'Basic !!!'], ids=['wrong-scheme', 'malformed-basic'])
    def test_malformed_authorization(self, api: ApiClient, booking: Booking, authorization: str) -> None:
        """Record rejection of unsupported and malformed Authorization headers."""
        # Expected error handling is unspecified; record current HTTP 403 with unchanged data.
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        response = api.partial_update_booking(booking.booking_id, payload, authorization=authorization)
        check_plain_text_error(response, 403)
        check_patched_booking(api, booking.booking_id, booking.payload)


class TestPartialUpdateBookingInvalidTypes:
    """Record accepted invalid scalar types and their persisted representations."""

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    @pytest.mark.parametrize('value', [None, 123, True, [], {}], ids=['null', 'number', 'boolean', 'array', 'object'])
    def test_non_string_field(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], field: str, value: Any
    ) -> None:
        """Record storage of non-string names and additional needs without coercion."""
        # Expected invalid-input handling is unspecified; record current acceptance and persistence.
        payload = {field: value}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize('value', [None, 'bad', True, [], {}], ids=['null', 'string', 'boolean', 'array', 'object'])
    def test_price_coerced_to_null(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], value: Any
    ) -> None:
        """Record the null price produced by invalid supplied price types."""
        # Expected invalid-input handling is unspecified; record the current null price in PATCH and GET.
        payload = {'totalprice': value}
        expected = merge_booking_patch(booking.payload, {'totalprice': None})
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)

    def test_numeric_string_price(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record conversion of a numeric string to an integer."""
        # Expected invalid-input handling is unspecified; record the current numeric conversion.
        payload = {'totalprice': '124'}
        expected = merge_booking_patch(booking.payload, {'totalprice': 124})
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize(('value', 'expected_value'), [(None, False), (0, False), (1, True), ('false', True),
                                                           ([], True), ({}, True)],
                             ids=['null', 'zero', 'one', 'string', 'array', 'object'])
    def test_deposit_coercion(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], value: Any, expected_value: bool
    ) -> None:
        """Record Boolean conversion of non-Boolean deposit values."""
        # Expected invalid-input handling is unspecified; record the currently observed conversions.
        payload = {'depositpaid': value}
        expected = merge_booking_patch(booking.payload, {'depositpaid': expected_value})
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize('value', [{}, [], 'invalid'], ids=['empty-object', 'array', 'string'])
    def test_invalid_dates_object(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], value: Any
    ) -> None:
        """Record invalid-date placeholders after replacing bookingdates without valid dates."""
        # Expected invalid-input handling is unspecified; record current persistence of both placeholders.
        payload = {'bookingdates': value}
        expected = merge_booking_patch(
            booking.payload, {'bookingdates': {'checkin': '0NaN-aN-aN', 'checkout': '0NaN-aN-aN'}}
        )
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)

    def test_null_dates_object(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record a persisted null date object that breaks both PATCH and GET serialization."""
        # Expected invalid-input handling is unspecified; record current HTTP 200 with an error message.
        payload = {'bookingdates': None}
        message = "Cannot read properties of null (reading 'checkin')"
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_serialization_error(response, message)
        check_unreadable_booking(api, booking.booking_id, message)


class TestPartialUpdateBookingInvalidDates:
    """Explore invalid calendar inputs while supplying the other date explicitly."""

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    @pytest.mark.parametrize(('value', 'normalized'),
                             [
                                 ('2030-02-30', '2030-03-02'),
                                 ('2030-02-29', '2030-03-01'),
                                 ('2030/06/15', '2030-06-15'),
                                 ('not-a-date', '0NaN-aN-aN'),
                                 ('2030-13-01', '0NaN-aN-aN'),
                                 ('2030-00-15', '0NaN-aN-aN'),
                                 ('2030-06-00', '0NaN-aN-aN'),
                                 (None, '1970-01-01'),
                             ],
                             ids=[
                                 'impossible-day',
                                 'non-leap-year',
                                 'wrong-separator',
                                 'not-a-date',
                                 'invalid-month',
                                 'zero-month',
                                 'zero-day',
                                 'null'
                             ])
    def test_invalid_date_values(
        self,
        api: ApiClient,
        booking: Booking,
        basic_auth: tuple[str, str],
        field: str,
        value: str | None,
        normalized: str
    ) -> None:
        """Record normalization and invalid-date placeholders for one supplied date."""
        # Expected invalid-input handling is unspecified; record current serialized and persisted dates.
        dates = {**booking.payload['bookingdates'], field: value}
        payload = {'bookingdates': dates}
        expected = merge_booking_patch(booking.payload, {'bookingdates': {**dates, field: normalized}})
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize(('checkin', 'checkout'), [('2031-07-01', '2031-07-01'), ('2031-07-01', '2031-06-30')],
                             ids=['equal-dates', 'reversed-interval'])
    def test_undefined_interval(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], checkin: str, checkout: str
    ) -> None:
        """Record acceptance of equal dates and a checkout preceding checkin."""
        # Expected interval constraints are unspecified; record current acceptance and persistence.
        payload = {'bookingdates': {'checkin': checkin, 'checkout': checkout}}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_current_patched_booking(api, booking.booking_id, expected)


class TestPartialUpdateBookingInvalidPayload:
    """Record empty, unknown or malformed bodies and content negotiation side effects."""

    @pytest.mark.parametrize('payload', [{}, {'unknown': 'extra'}], ids=['empty-object', 'unknown-only'])
    def test_no_known_fields(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], payload: dict[str, Any]
    ) -> None:
        """Record a successful no-op when no recognized fields are supplied."""
        # Expected handling is unspecified; record current HTTP 200 with the original data preserved.
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, booking.payload)
        check_patched_booking(api, booking.booking_id, booking.payload)

    def test_unknown_field_with_valid_change(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str]
    ) -> None:
        """Record omission of an unknown field while a recognized field changes."""
        # Expected unknown-field handling is unspecified; record the current omission of the extra field.
        payload = {'firstname': booking.payload['firstname'] + 'Changed', 'unknown': 'extra'}
        expected = merge_booking_patch(booking.payload, {'firstname': payload['firstname']})
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth)
        check_current_partial_update_response(response, expected)
        check_patched_booking(api, booking.booking_id, expected)

    @pytest.mark.parametrize('body', ['', '[]'], ids=['empty-body', 'root-array'])
    def test_unstructured_noop(self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], body: str) -> None:
        """Record an unchanged booking after an empty body or root JSON array."""
        # Expected invalid-input handling is unspecified; record current HTTP 200 with unchanged data.
        response = api.partial_update_booking(booking.booking_id, body=body, auth=basic_auth)
        check_current_partial_update_response(response, booking.payload)
        check_patched_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize(('body', 'content_type'),
                             [('null', 'application/json'), ('{"firstname":', 'application/json'),
                              ('<booking>', 'text/xml')],
                             ids=['root-null', 'malformed-json', 'malformed-xml'])
    def test_malformed_body(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], body: str, content_type: str
    ) -> None:
        """Record parser rejection before the original booking changes."""
        # Expected error handling is unspecified; record current HTTP 400 with unchanged data.
        response = api.partial_update_booking(booking.booking_id, body=body, content_type=content_type, auth=basic_auth)
        check_plain_text_error(response, 400)
        check_patched_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('content_type', ['text/plain', None], ids=['unsupported', 'absent'])
    def test_unparsed_content_type(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], content_type: str | None
    ) -> None:
        """Record a successful no-op for unparsed JSON text."""
        # Expected header handling is unspecified; record current HTTP 200 with the original data preserved.
        body = json.dumps({'firstname': booking.payload['firstname'] + 'Changed'})
        response = api.partial_update_booking(booking.booking_id, body=body, content_type=content_type, auth=basic_auth)
        check_current_partial_update_response(response, booking.payload)
        check_patched_booking(api, booking.booking_id, booking.payload)

    @pytest.mark.parametrize('accept', ['application/pdf', None], ids=['unsupported', 'absent'])
    def test_unusable_accept(
        self, api: ApiClient, booking: Booking, basic_auth: tuple[str, str], accept: str | None
    ) -> None:
        """Record a server error returned after the partial update has already been saved."""
        # Expected header handling is unspecified; record current HTTP 500 despite the persisted change.
        payload = {'firstname': booking.payload['firstname'] + 'Changed'}
        expected = merge_booking_patch(booking.payload, payload)
        response = api.partial_update_booking(booking.booking_id, payload, auth=basic_auth, accept=accept)
        check_plain_text_error(response, 500)
        check_patched_booking(api, booking.booking_id, expected)


class TestPartialUpdateBookingMissingId:
    """Target a previously deleted test-owned ID rather than a random public booking."""

    def test_deleted_id(self, api: ApiClient, deleted_booking: Booking, basic_auth: tuple[str, str]) -> None:
        """Record a missing-ID response and verify no matching booking was created."""
        # Expected missing-ID handling is unspecified; record HTTP 405 without resurrecting the owned record.
        payload = deepcopy(deleted_booking.payload)
        payload['firstname'] += 'Changed'
        response = api.partial_update_booking(deleted_booking.booking_id, payload, auth=basic_auth)
        check_plain_text_error(response, 405)
        response = api.get_bookings(params={'lastname': payload['lastname']})
        check_booking_ids(response, set())
