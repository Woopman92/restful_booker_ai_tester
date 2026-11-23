"""Schema, persistence and current response checks for booking creation."""

from typing import Any
from xml.etree import ElementTree

from requests import Response

from checkers.common import _check_booking_values
from checkers.common import _check_current_booking_values
from checkers.common import check_booking_schema
from checkers.common import check_xml_booking_data
from checkers.common import form_response_fields


def check_creation_schema(response: Response) -> int:
    """Validate the documented JSON creation envelope and nested booking schema.

    Args:
        response: Booking creation response.

    Returns:
        int: Created booking ID for a subsequent persistence check.

    Raises:
        AssertionError: Media type, envelope or booking schema is invalid.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    booking_id = check_json_creation_envelope(response)
    check_booking_schema(response.json()['booking'])
    return booking_id


def check_json_creation_envelope(response: Response) -> int:
    """Validate the media type and top-level fields of a JSON creation response.

    Args:
        response: JSON creation response.

    Returns:
        int: Created record ID.

    Raises:
        AssertionError: JSON media type or envelope is invalid.
        ValueError: The body is not valid JSON.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    body = response.json()
    assert isinstance(body, dict)
    assert type(body.get('bookingid')) is int, f'Expected an integer bookingid, got {body!r}'
    assert isinstance(body.get('booking'), dict)
    return body['bookingid']


def check_created_values(response: Response, expected_payload: dict[str, Any]) -> None:
    """Compare the nested booking using JSON types and numeric value equality.

    Args:
        response: Response whose creation envelope has already been validated.
        expected_payload: Expected persisted booking fields.

    Raises:
        AssertionError: Required booking fields or JSON types are invalid.
        ResponseValuesMismatch: Booking field values differ.
        ValueError: The response is not valid JSON.
    """
    _check_booking_values(response.json()['booking'], expected_payload)


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


def check_current_created_booking(response: Response, expected_payload: dict[str, Any]) -> None:
    """Record transformed or incomplete success data for invalid/unspecified requests.

    Args:
        response: Creation response to a request with unspecified handling.
        expected_payload: Observed booking fields, which may violate the valid-input schema.

    Raises:
        AssertionError: Envelope, values or field types differ.
        ValueError: The body is not valid JSON.
    """
    check_json_creation_envelope(response)
    _check_current_booking_values(response.json()['booking'], expected_payload)


def check_xml_created_booking(response: Response, expected_payload: dict[str, Any]) -> int:
    """Validate the documented XML creation envelope and nested booking values.

    Args:
        response: XML creation response.
        expected_payload: Expected original booking payload.

    Returns:
        int: ID from the XML envelope.

    Raises:
        AssertionError: Observed media type, envelope or booking values differ.
        ValueError: The ID cannot be parsed as an integer.
        xml.etree.ElementTree.ParseError: The XML is malformed.
    """
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
        AssertionError: The media type or encoded fields differ.
        FormResponseMismatch: The service returns its confirmed serializer error.
        ValueError: The encoded body or ID is invalid.
    """
    fields = form_response_fields(response)
    assert len(fields.get('bookingid', [])) == 1
    int(fields['bookingid'][0])
    for key in ('firstname', 'lastname', 'totalprice', 'additionalneeds'):
        assert fields.get(f'booking[{key}]') == [str(expected_payload[key])]
    assert fields.get('booking[depositpaid]') == [str(expected_payload['depositpaid']).lower()]
    for key in ('checkin', 'checkout'):
        assert fields.get(f'booking[bookingdates][{key}]') == [expected_payload['bookingdates'][key]]
