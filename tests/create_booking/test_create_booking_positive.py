"""Documented creation contract, valid values and supported representations."""

from typing import Any

import pytest

from checkers.create_booking import check_create_booking_response
from checkers.create_booking import check_created_booking
from checkers.create_booking import check_created_values
from checkers.create_booking import check_creation_schema
from checkers.create_booking import check_form_created_booking
from checkers.create_booking import check_xml_created_booking
from tests.create_booking.support import CreationTracker
from tests.create_booking.support import form_payload
from tests.create_booking.support import xml_payload
from tests.support import ApiClient

pytestmark = pytest.mark.positive


class TestCreateBookingContract:
    """Check the creation envelope, persistence and independence of owned records."""

    def test_create_booking(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Create a complete booking and confirm persistence with a read by its ID."""
        response = api.create_booking(booking_payload)
        booking_id = check_create_booking_response(response, booking_payload)
        check_created_booking(api, booking_id, booking_payload)

    def test_independent_creations(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Assign distinct IDs to two independent creations without assuming sequential IDs."""
        response = api.create_booking(booking_payload)
        first_id = check_create_booking_response(response, booking_payload)
        second_payload = {**booking_payload, 'lastname': booking_payload['lastname'] + 'Second'}
        response = api.create_booking(second_payload)
        second_id = check_create_booking_response(response, second_payload)
        assert first_id != second_id
        check_created_booking(api, first_id, booking_payload)
        check_created_booking(api, second_id, second_payload)


class TestDuplicateBookingCreation:
    """Record current handling of repeated creation with identical booking data."""

    def test_identical_payload_creates_distinct_bookings(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Create two distinct records from identical payloads and verify both persisted bookings."""
        # Deduplication and POST idempotency are unspecified in the documentation.
        # This test records current behavior: identical payloads create separate bookings with distinct IDs.
        response = api.create_booking(booking_payload)
        first_id = check_create_booking_response(response, booking_payload)
        response = api.create_booking(booking_payload)
        second_id = check_create_booking_response(response, booking_payload)
        assert first_id != second_id
        check_created_booking(api, first_id, booking_payload)
        check_created_booking(api, second_id, booking_payload)


class TestBookingValues:
    """Check documented JSON types, unconstrained boundaries and calendar transitions."""

    @pytest.mark.parametrize('value', [True, False], ids=['paid', 'unpaid'])
    def test_boolean(self, api: ApiClient, booking_payload: dict[str, Any], value: bool) -> None:
        """Preserve either valid boolean deposit value."""
        booking_payload['depositpaid'] = value
        response = api.create_booking(booking_payload)
        check_create_booking_response(response, booking_payload)

    @pytest.mark.parametrize('value', [-1, 0, 1], ids=['negative', 'zero', 'positive'])
    def test_integer_price(self, api: ApiClient, booking_payload: dict[str, Any], value: int) -> None:
        """Preserve numbers around zero without inventing a nonnegative price constraint."""
        booking_payload['totalprice'] = value
        response = api.create_booking(booking_payload)
        check_create_booking_response(response, booking_payload)

    def test_fractional_price(
        self, api: ApiClient, booking_payload: dict[str, Any], request: pytest.FixtureRequest
    ) -> None:
        """Preserve a fractional Number rather than silently truncate it."""
        booking_payload['totalprice'] = 123.5
        response = api.create_booking(booking_payload)
        check_creation_schema(response)
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason='CreateBooking documents totalprice as Number without an integer restriction; '
                'sending 123.5 currently returns 123, losing the fractional part.',
            )
        )
        check_created_values(response, booking_payload)

    def test_special_strings(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Preserve Unicode, spaces, punctuation and markup characters in JSON strings."""
        booking_payload['firstname'] += " Élodie O'Neil-李"
        booking_payload['additionalneeds'] = 'Завтрак & tea <without sugar>'
        response = api.create_booking(booking_payload)
        check_create_booking_response(response, booking_payload)

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    @pytest.mark.parametrize('value', ['', 'x'], ids=['empty', 'one-character'])
    def test_short_strings(self, api: ApiClient, booking_payload: dict[str, Any], field: str, value: str) -> None:
        """Preserve short strings because the contract specifies no minimum length."""
        booking_payload[field] = value
        response = api.create_booking(booking_payload)
        check_create_booking_response(response, booking_payload)

    @pytest.mark.parametrize(
        ('checkin', 'checkout'),
        [('2028-02-29', '2028-03-01'), ('2030-12-31', '2031-01-01')],
        ids=['leap-day', 'year-transition'],
    )
    def test_calendar_dates(self, api: ApiClient, booking_payload: dict[str, Any], checkin: str, checkout: str) -> None:
        """Preserve valid leap-day and year-boundary intervals."""
        booking_payload['bookingdates'] = {'checkin': checkin, 'checkout': checkout}
        response = api.create_booking(booking_payload)
        check_create_booking_response(response, booking_payload)


class TestLongBookingStrings:
    """Record creation and persistence of long ASCII and Unicode strings."""

    @pytest.mark.parametrize('field', ['firstname', 'lastname', 'additionalneeds'])
    def test_long_ascii_string(self, api: ApiClient, booking_payload: dict[str, Any], field: str) -> None:
        """Record full preservation of a 1024-character ASCII string in each string field."""
        # Maximum lengths are unspecified; 1024 characters is an exploratory size, not a documented boundary.
        # This test records current acceptance and persistence without truncation.
        booking_payload[field] = 'a' * 1024
        response = api.create_booking(booking_payload)
        booking_id = check_create_booking_response(response, booking_payload)
        check_created_booking(api, booking_id, booking_payload)

    def test_long_unicode_string(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Record full preservation of 1024 Unicode characters occupying 2048 UTF-8 bytes."""
        # Maximum lengths are unspecified; this test records current behavior for multibyte text.
        booking_payload['additionalneeds'] = 'Ж' * 1024
        response = api.create_booking(booking_payload)
        booking_id = check_create_booking_response(response, booking_payload)
        check_created_booking(api, booking_id, booking_payload)


class TestBookingFormats:
    """Check documented XML and URL-encoded request and response representations."""

    def test_xml_input(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Accept a complete booking sent as text/xml."""
        body = xml_payload(booking_payload)
        response = api.create_booking(body=body, content_type='text/xml')
        booking_id = check_create_booking_response(response, booking_payload)
        check_created_booking(api, booking_id, booking_payload)

    def test_xml_output(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Return the documented created-booking XML envelope and persist its fields."""
        response = api.create_booking(booking_payload, accept='application/xml')
        booking_id = check_xml_created_booking(response, booking_payload)
        check_created_booking(api, booking_id, booking_payload)

    def test_form_input(self, api: ApiClient, booking_payload: dict[str, Any]) -> None:
        """Accept form fields and nested dates encoded using bracket notation."""
        body = form_payload(booking_payload)
        response = api.create_booking(body=body, content_type='application/x-www-form-urlencoded')
        booking_id = check_create_booking_response(response, booking_payload)
        check_created_booking(api, booking_id, booking_payload)

    def test_form_output(
        self,
        api: ApiClient,
        booking_payload: dict[str, Any],
        creation_tracker: CreationTracker,
        request: pytest.FixtureRequest
    ) -> None:
        """Return bookingid and nested fields in the documented URL-encoded format."""
        creation_tracker.expected_recovered_count = 1
        response = api.create_booking(booking_payload, accept='application/x-www-form-urlencoded')
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason='CreateBooking shows a URL-encoded response example; the service instead returns HTTP 200 '
                'text/html "formurlencoded is not a function". The record is created without an ID in the response '
                'and is recovered by unique names and deleted at teardown.',
            )
        )
        check_form_created_booking(response, booking_payload)
