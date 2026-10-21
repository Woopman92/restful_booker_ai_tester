"""Schema and value checks for individual booking representations."""

from datetime import date
from typing import Any
from xml.etree import ElementTree

from requests import Response


def check_json_booking(response: Response, expected_payload: dict[str, Any]) -> None:
    """Validate the JSON booking schema and compare all expected values.

    Args:
        response: Booking retrieval response.
        expected_payload: Original booking data expected after reading.

    Raises:
        AssertionError: Status, media type, schema or values differ.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    assert response.status_code == 200, response.text
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    body = response.json()
    check_booking_schema(body)
    assert body == expected_payload


def check_booking_schema(body: Any) -> None:
    """Validate required fields, JSON types and calendar dates of a booking object.

    Args:
        body: Decoded booking object to validate.

    Raises:
        AssertionError: Required fields, types or date representations are invalid.
        ValueError: A calendar date cannot be parsed.
    """
    assert isinstance(body, dict)
    for field in ('firstname', 'lastname', 'additionalneeds'):
        assert isinstance(body.get(field), str), f'Expected string field {field}'
    assert type(body.get('totalprice')) in (int, float)
    assert type(body.get('depositpaid')) is bool
    assert isinstance(body.get('bookingdates'), dict)
    for field in ('checkin', 'checkout'):
        value = body['bookingdates'].get(field)
        assert isinstance(value, str)
        assert date.fromisoformat(value).isoformat() == value


def _booking_text_fields(payload: dict[str, Any]) -> dict[str, str]:
    """Represent expected booking fields as XML element paths and text values.

    Args:
        payload: Complete booking payload.

    Returns:
        dict[str, str]: Required element paths and their expected text.
    """
    return {
        'firstname': payload['firstname'],
        'lastname': payload['lastname'],
        'totalprice': str(payload['totalprice']),
        'depositpaid': str(payload['depositpaid']).lower(),
        'bookingdates/checkin': payload['bookingdates']['checkin'],
        'bookingdates/checkout': payload['bookingdates']['checkout'],
        'additionalneeds': payload['additionalneeds'],
    }


def check_xml_booking(response: Response, expected_payload: dict[str, Any]) -> None:
    """Validate the XML root, required elements and expected field values.

    Args:
        response: Booking response with an XML body.
        expected_payload: Complete original booking data.

    Raises:
        AssertionError: Status, observed media type, XML structure or values differ.
        xml.etree.ElementTree.ParseError: The body is not well-formed XML.
    """
    assert response.status_code == 200, response.text
    # The response Content-Type is not explicitly specified; record the observed text/html value.
    assert response.headers.get('Content-Type', '').split(';')[0] == 'text/html'
    root = ElementTree.fromstring(response.text)
    check_xml_booking_data(root, expected_payload)


def check_xml_booking_data(root: ElementTree.Element, expected_payload: dict[str, Any]) -> None:
    """Validate a booking XML element and compare required text fields.

    Args:
        root: Parsed booking element.
        expected_payload: Complete booking fields expected in the XML.

    Raises:
        AssertionError: Required elements or their text values differ.
    """
    assert root.tag == 'booking'
    assert len(root.findall('bookingdates')) == 1
    for path, expected_text in _booking_text_fields(expected_payload).items():
        elements = root.findall(path)
        assert len(elements) == 1, f'Expected one element at {path}'
        assert elements[0].text == expected_text
