"""Observed handling of missing fields, invalid values and unsupported representations."""

import json
from typing import Any

import pytest

from checkers.common import check_plain_text_error
from checkers.create_booking import check_current_created_booking
from tests.client import ApiClient
from tests.create_booking.support import CreationTracker

pytestmark = pytest.mark.negative


class TestMissingBookingFields:
    """Record required-field omissions without assuming undocumented error codes."""

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'totalprice', 'depositpaid', 'bookingdates'])
    def test_missing_field(self, api: ApiClient, booking_payload: dict[str, Any], field: str) -> None:
        """Record the current server error when a validated mandatory field is absent."""
        # Error handling is unspecified; record the current HTTP 500 response.
        del booking_payload[field]
        response = api.create_booking(booking_payload)
        check_plain_text_error(response, expected_status_code=500)

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    def test_missing_nested_date(self, api: ApiClient, booking_payload: dict[str, Any], field: str) -> None:
        """Record the current response when one mandatory booking date is absent."""
        # Error handling is unspecified; record the current HTTP 500 response.
        del booking_payload['bookingdates'][field]
        response = api.create_booking(booking_payload)
        check_plain_text_error(response, expected_status_code=500)

    def test_missing_additionalneeds(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Record acceptance of an omitted additionalneeds field despite its required annotation."""
        # Invalid-input behavior is unspecified; the current service creates a record without this field.
        del booking_payload['additionalneeds']
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, booking_payload)


class TestInvalidBookingTypes:
    """Record type validation and coercion using separate tests for distinct outcomes."""

    @pytest.mark.parametrize('field', ['firstname', 'lastname'])
    @pytest.mark.parametrize('value', [None, 123, True, [], {}], ids=['null', 'number', 'boolean', 'array', 'object'])
    def test_invalid_name_type(self, api: ApiClient, booking_payload: dict[str, Any], field: str, value: Any) -> None:
        """Record rejection of non-string first or last names."""
        # Error handling is unspecified; record the current HTTP 500 response.
        booking_payload[field] = value
        response = api.create_booking(booking_payload)
        check_plain_text_error(response, expected_status_code=500)

    @pytest.mark.parametrize('value', [None, 123, True, [], {}], ids=['null', 'number', 'boolean', 'array', 'object'])
    def test_unvalidated_additionalneeds(self, api: ApiClient, booking_payload: dict[str, Any], value: Any) -> None:
        """Record acceptance of additionalneeds values outside the documented string type."""
        # Invalid-input behavior is unspecified; record the currently accepted value without coercion.
        booking_payload['additionalneeds'] = value
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, booking_payload)

    @pytest.mark.parametrize('value', ['bad', True, [], {}], ids=['string', 'boolean', 'array', 'object'])
    def test_price_coerced_to_null(self, api: ApiClient, booking_payload: dict[str, Any], value: Any) -> None:
        """Record invalid price values represented as JSON null after creation."""
        # Invalid-input behavior is unspecified; the current service returns a null price.
        booking_payload['totalprice'] = value
        expected = {**booking_payload, 'totalprice': None}
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, expected)

    @pytest.mark.parametrize('field', ['totalprice', 'depositpaid'])
    def test_null_mandatory_field(self, api: ApiClient, booking_payload: dict[str, Any], field: str) -> None:
        """Record rejection of null in validated mandatory scalar fields."""
        # Error handling is unspecified; record the observed HTTP 500 for null price or deposit.
        booking_payload[field] = None
        response = api.create_booking(booking_payload)
        check_plain_text_error(response, expected_status_code=500)

    def test_numeric_string_price(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Record conversion of a numeric string to an integer price."""
        # Invalid-input behavior is unspecified; record the current string-to-number conversion.
        booking_payload['totalprice'] = '123'
        expected = {**booking_payload, 'totalprice': 123}
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, expected)

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [('false', True), (0, False), ([], True), ({}, True)],
        ids=['string', 'number', 'array', 'object'],
    )
    def test_deposit_coercion(
        self, api: ApiClient, booking_payload: dict[str, Any], value: Any, expected: bool
    ) -> None:
        """Record coercion of non-boolean deposit values."""
        # Invalid-input behavior is unspecified; record the currently observed boolean conversion.
        booking_payload['depositpaid'] = value
        expected_payload = {**booking_payload, 'depositpaid': expected}
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, expected_payload)

    @pytest.mark.parametrize('value', [None, [], 'invalid'], ids=['null', 'array', 'string'])
    def test_invalid_dates_object(self, api: ApiClient, booking_payload: dict[str, Any], value: Any) -> None:
        """Record rejection of invalid bookingdates container types."""
        # Error handling is unspecified; record the current HTTP 500 response.
        booking_payload['bookingdates'] = value
        response = api.create_booking(booking_payload)
        check_plain_text_error(response, expected_status_code=500)


class TestInvalidBookingDates:
    """Record date normalization and acceptance of undefined interval boundaries."""

    @pytest.mark.parametrize('field', ['checkin', 'checkout'])
    @pytest.mark.parametrize(
        ('value', 'expected'),
        [('2030-02-30', '2030-03-02'), ('2030-02-29', '2030-03-01'), ('2030/06/15', '2030-06-15'),
         ('not-a-date', '0NaN-aN-aN'), ('2030-13-01', '0NaN-aN-aN'), ('2030-06-00', '0NaN-aN-aN')],
        ids=['impossible-day', 'non-leap-year', 'wrong-separator', 'not-a-date', 'invalid-month', 'zero-day'],
    )
    def test_invalid_date_values(
        self, api: ApiClient, booking_payload: dict[str, Any], field: str, value: str, expected: str
    ) -> None:
        """Record normalization of invalid dates and the placeholder used for unparseable dates."""
        # Invalid-input behavior is unspecified; record the current date normalization or placeholder.
        booking_payload['bookingdates'][field] = value
        expected_payload = {**booking_payload, 'bookingdates': {**booking_payload['bookingdates'], field: expected}}
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, expected_payload)

    @pytest.mark.parametrize(
        ('checkin', 'checkout'),
        [('2030-06-15', '2030-06-15'), ('2030-06-15', '2030-06-14')],
        ids=['equal-dates', 'reversed-interval'],
    )
    def test_undefined_interval(
        self, api: ApiClient, booking_payload: dict[str, Any], checkin: str, checkout: str
    ) -> None:
        """Record acceptance of equal dates and intervals with checkout before checkin."""
        # The allowed interval relation is unspecified; record current acceptance without changes.
        booking_payload['bookingdates'] = {'checkin': checkin, 'checkout': checkout}
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, booking_payload)


class TestInvalidBookingPayload:
    """Record parser failures, unknown fields and unsupported media types."""

    def test_empty_body(self, api: ApiClient) -> None:
        """Record the current response to a completely empty JSON body."""
        # Error handling is unspecified; record the current HTTP 500 response.
        response = api.create_booking(body='')
        check_plain_text_error(response, expected_status_code=500)

    @pytest.mark.parametrize(
        ('body', 'content_type'),
        [('{"firstname":', 'application/json'), ('<booking>', 'text/xml')],
        ids=['malformed-json', 'malformed-xml'],
    )
    def test_malformed_body(self, api: ApiClient, body: str, content_type: str) -> None:
        """Record the parser error for malformed JSON or XML."""
        # Error handling is unspecified; record the current HTTP 400 response.
        response = api.create_booking(body=body, content_type=content_type)
        check_plain_text_error(response, expected_status_code=400)

    @pytest.mark.parametrize('content_type', ['text/plain', None], ids=['unsupported', 'absent'])
    def test_unparsed_content_type(
        self, api: ApiClient, booking_payload: dict[str, Any], content_type: str | None
    ) -> None:
        """Record handling of a JSON body without a supported JSON media type."""
        # Error handling is unspecified; record the current HTTP 500 response.
        body = json.dumps(booking_payload)
        response = api.create_booking(body=body, content_type=content_type)
        check_plain_text_error(response, expected_status_code=500)

    @pytest.mark.parametrize('accept', ['application/pdf', None], ids=['unsupported', 'absent'])
    def test_unusable_accept(
        self, api: ApiClient, booking_payload: dict[str, Any], creation_tracker: CreationTracker, accept: str | None
    ) -> None:
        """Record an error response that still creates a record, recovered during cleanup."""
        # Error handling is unspecified; the current service returns 418 after persisting the booking.
        creation_tracker.expected_recovered_count = 1
        response = api.create_booking(booking_payload, accept=accept)
        check_plain_text_error(response, expected_status_code=418)

    def test_unknown_field(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Record that an unknown request field is omitted from the created booking."""
        # Unknown-field handling is unspecified; record the current omission of that field.
        booking_payload['unknown'] = 'extra'
        expected = {key: value for key, value in booking_payload.items() if key != 'unknown'}
        response = api.create_booking(booking_payload)
        check_current_created_booking(response, expected)
