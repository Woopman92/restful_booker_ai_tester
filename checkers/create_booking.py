"""Schema, persistence and current response checks for booking creation."""

from typing import Any
from xml.etree import ElementTree

from requests import Response

from checkers.common import check_booking_schema
from checkers.common import check_booking_values
from checkers.common import check_form_booking_fields
from checkers.common import check_xml_booking_data
from checkers.common import form_response_fields
from checkers.common import json_body


def check_create_booking_schema(response: Response, *, schema_example: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the JSON creation response, including the nested booking schema.

    Args:
        response: Booking creation response.
        schema_example: Optional example defining the nested booking schema.

    Returns:
        dict[str, Any]: Decoded response containing the validated ID and booking.

    Raises:
        AssertionError: The media type, ID or response schema is invalid.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    body = json_body(response)
    assert isinstance(body, dict)
    assert type(body.get('bookingid')) is int, f'Expected an integer bookingid, got {body!r}'
    assert 'booking' in body
    check_booking_schema(body['booking'], schema_example=schema_example)
    return body


def check_create_booking_json_response(
    response: Response, expected_payload: dict[str, Any], *, schema_example: dict[str, Any] | None = None
) -> int:
    """Validate the documented creation schema and expected booking values.

    Args:
        response: JSON creation response.
        expected_payload: Expected booking values.
        schema_example: Optional example defining the nested booking schema.

    Returns:
        int: Validated created ID.

    Raises:
        AssertionError: Schema or booking values differ.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    body = check_create_booking_schema(response, schema_example=schema_example)
    check_booking_values(body['booking'], expected_payload)
    return body['bookingid']


def check_create_booking_xml_response(response: Response, expected_payload: dict[str, Any]) -> int:
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


def check_create_booking_form_response(response: Response, expected_payload: dict[str, Any]) -> None:
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
    check_form_booking_fields(fields, expected_payload, prefix='booking')
