"""Schema, persistence and current response checks for booking creation."""

from typing import Any
from urllib.parse import parse_qs
from xml.etree import ElementTree

from requests import Response

from checkers.get_booking import check_booking_schema
from checkers.get_booking import check_json_booking
from checkers.get_booking import check_xml_booking_data
from tests.support import ApiClient


def check_creation_schema(response: Response) -> int:
    """Validate the documented JSON creation envelope and nested booking schema.

    Args:
        response: Booking creation response.

    Returns:
        int: Created booking ID for a subsequent persistence check.

    Raises:
        AssertionError: Status, media type, envelope or booking schema is invalid.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    booking_id = check_current_creation_envelope(response)
    check_booking_schema(response.json()['booking'])
    return booking_id


def check_current_creation_envelope(response: Response) -> int:
    """Check the observed success envelope without imposing a schema on invalid input.

    Args:
        response: JSON creation response.

    Returns:
        int: Created record ID.

    Raises:
        AssertionError: Status, JSON media type or envelope is invalid.
        ValueError: The body is not valid JSON.
    """
    assert response.status_code == 200, response.text
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    body = response.json()
    assert isinstance(body, dict)
    assert type(body.get('bookingid')) is int
    assert isinstance(body.get('booking'), dict)
    return body['bookingid']


def check_created_values(response: Response, expected_payload: dict[str, Any]) -> None:
    """Compare the nested created booking with expected values and exact field types.

    Args:
        response: Response whose creation envelope has already been validated.
        expected_payload: Expected persisted booking fields.

    Raises:
        AssertionError: Booking fields or their JSON types differ.
        ValueError: The response is not valid JSON.
    """
    actual = response.json()['booking']
    assert actual == expected_payload
    for key, value in expected_payload.items():
        assert type(actual[key]) is type(value), f'Unexpected type for {key}'


def check_create_booking_response(response: Response, expected_payload: dict[str, Any]) -> int:
    """Validate the documented creation schema and expected booking values.

    Args:
        response: JSON creation response.
        expected_payload: Expected complete booking payload.

    Returns:
        int: Validated created ID.

    Raises:
        AssertionError: Schema or booking values differ.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    booking_id = check_creation_schema(response)
    check_created_values(response, expected_payload)
    return booking_id


def check_created_booking(api: ApiClient, booking_id: int, expected_payload: dict[str, Any]) -> None:
    """Read a created booking and validate its persisted schema and values.

    Args:
        api: Client used to retrieve the test-owned booking.
        booking_id: ID returned by the creation response checker.
        expected_payload: Complete booking data expected to be persisted.

    Raises:
        AssertionError: The retrieval status, schema or saved values differ.
        ValueError: JSON or a calendar date cannot be parsed.
        requests.RequestException: The retrieval request fails.
    """
    response = api.get_booking(booking_id)
    check_json_booking(response, expected_payload)


def check_current_created_booking(response: Response, expected_payload: dict[str, Any]) -> None:
    """Record transformed or incomplete success data for invalid/unspecified requests.

    Args:
        response: Creation response to a request with unspecified handling.
        expected_payload: Observed booking fields, which may violate the valid-input schema.

    Raises:
        AssertionError: Current status, envelope, values or field types differ.
        ValueError: The body is not valid JSON.
    """
    check_current_creation_envelope(response)
    check_created_values(response, expected_payload)


def check_xml_created_booking(response: Response, expected_payload: dict[str, Any]) -> int:
    """Validate the documented XML creation envelope and nested booking values.

    Args:
        response: XML creation response.
        expected_payload: Expected original booking payload.

    Returns:
        int: ID from the XML envelope.

    Raises:
        AssertionError: Status, observed media type, envelope or booking values differ.
        ValueError: The ID cannot be parsed as an integer.
        xml.etree.ElementTree.ParseError: The XML is malformed.
    """
    assert response.status_code == 200, response.text
    # The response media type is not explicitly documented; record its current value.
    assert response.headers.get('Content-Type', '').split(';')[0] == 'text/html'
    root = ElementTree.fromstring(response.text)
    assert root.tag == 'created-booking'
    assert len(root.findall('bookingid')) == 1
    booking_id = int(root.findtext('bookingid', ''))
    bookings = root.findall('booking')
    assert len(bookings) == 1
    check_xml_booking_data(bookings[0], expected_payload)
    return booking_id


def check_form_created_booking(response: Response, expected_payload: dict[str, Any]) -> None:
    """Check the URL-encoded creation response shown in the documentation example.

    Args:
        response: Creation response requested as form-urlencoded.
        expected_payload: Expected booking fields.

    Raises:
        AssertionError: The status, media type or encoded fields differ.
        ValueError: The encoded body or ID is invalid.
    """
    assert response.status_code == 200, response.text
    assert '=' in response.text, response.text
    fields = parse_qs(response.text, keep_blank_values=True, strict_parsing=True)
    assert len(fields.get('bookingid', [])) == 1
    int(fields['bookingid'][0])
    for key in ('firstname', 'lastname', 'totalprice', 'additionalneeds'):
        assert fields.get(f'booking[{key}]') == [str(expected_payload[key])]
    assert fields.get('booking[depositpaid]') == [str(expected_payload['depositpaid']).lower()]
    for key in ('checkin', 'checkout'):
        assert fields.get(f'booking[bookingdates][{key}]') == [expected_payload['bookingdates'][key]]
