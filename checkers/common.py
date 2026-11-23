"""Checks shared across endpoint test groups, including booking schemas and persisted state."""

from collections.abc import Iterable
from datetime import date
from http import HTTPStatus
from math import isfinite
from typing import Any
from urllib.parse import parse_qs
from xml.etree import ElementTree

from requests import Response

from checkers.errors import CleanupError
from checkers.errors import FormResponseMismatch
from checkers.errors import ResponseValuesMismatch
from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME
from tests.client import ApiClient


def cleanup_bookings(api: ApiClient, owned_ids: Iterable[int]) -> None:
    """Delete registered bookings and confirm absence when DELETE returns 405.

    Args:
        api: Client used for cleanup with the configured valid credentials.
        owned_ids: Registered IDs to delete, preserving order and ignoring duplicates.

    Raises:
        CleanupError: A deletion, absence check, or request fails. Every remaining
            registered ID is attempted before the collected failures are reported.
    """
    errors = []
    for booking_id in dict.fromkeys(owned_ids):
        try:
            response = api.delete_booking(booking_id, auth=(BOOKER_USERNAME, BOOKER_PASSWORD))
            if response.status_code == 405:
                response = api.get_booking(booking_id)
                check_status_code(response, 404)
            else:
                check_status_code(response, 201)
        except Exception as error:
            errors.append(f'ID {booking_id}: {type(error).__name__}: {error}')
    if errors:
        raise CleanupError('Cleanup failed: ' + '; '.join(errors))


def check_plain_text_error(response: Response, expected_status_code: int) -> None:
    """Check the status, content type and standard HTTP phrase of a plain-text error.

    Args:
        response: Service response to validate.
        expected_status_code: Standard HTTP status whose phrase is expected in the body.

    Raises:
        AssertionError: The status, content type or response body is unexpected.
        ValueError: The expected status code is not defined in HTTPStatus.
    """
    assert response.status_code == expected_status_code, response.text
    assert response.headers.get('Content-Type', '').split(';')[0] == 'text/plain'
    assert response.text == HTTPStatus(expected_status_code).phrase


def check_status_code(response: Response, expected_status_code: int) -> None:
    """Check an HTTP status independently of representation-specific assertions.

    Args:
        response: Service response to validate.
        expected_status_code: Required HTTP response status.

    Raises:
        AssertionError: The status differs from the expected value.
    """
    assert response.status_code == expected_status_code, (
        f'Expected HTTP {expected_status_code}, received HTTP {response.status_code}'
    )


def check_number(value: Any) -> None:
    """Check a JSON Number without treating Boolean as numeric.

    Args:
        value: Decoded JSON field to validate.

    Raises:
        AssertionError: The value is not int or float, or is a nonfinite float.
    """
    assert type(value) in (int, float), f'Expected a JSON Number, got {value!r}'
    assert type(value) is int or isfinite(value), f'Expected a finite JSON Number, got {value!r}'


def booking_ids(response: Response) -> set[int]:
    """Check the documented JSON array schema and uniqueness, then return IDs.

    Args:
        response: Booking list response to validate.

    Returns:
        set[int]: Unique booking IDs extracted from the validated response.

    Raises:
        AssertionError: The status, content type, schema or ID uniqueness is invalid.
        ValueError: The response body is not valid JSON.
    """
    assert response.status_code == 200, f'{response.status_code}: {response.text[:500]}'
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    body = response.json()
    assert isinstance(body, list), f'Expected an array, got {body!r}'
    ids = []
    for item in body:
        assert isinstance(item, dict), f'Expected an object, got {item!r}'
        assert 'bookingid' in item, f'Missing bookingid: {item!r}'
        assert type(item['bookingid']) is int, f'Expected an integer ID, got {item!r}'
        ids.append(item['bookingid'])
    assert len(ids) == len(set(ids)), 'Response contains duplicate booking IDs'
    return set(ids)


def check_booking_ids(response: Response, expected_ids: set[int]) -> None:
    """Check that the response contains exactly the expected booking IDs.

    Args:
        response: Booking list response to validate.
        expected_ids: Complete set of IDs expected in the response.

    Raises:
        AssertionError: Response status, media type or schema is invalid.
        ResponseValuesMismatch: The ID sets differ.
        ValueError: The response body is not valid JSON.
    """
    actual_ids = booking_ids(response)
    try:
        assert actual_ids == expected_ids
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error


def check_booking(api: ApiClient, booking_id: int, expected_payload: dict[str, Any]) -> None:
    """Retrieve an owned booking and validate its full schema and expected values.

    Args:
        api: Client used for the independent retrieval.
        booking_id: ID of the test-owned booking.
        expected_payload: Complete expected booking data.

    Raises:
        AssertionError: Retrieval status, media type, schema or values differ.
        ValueError: JSON or a calendar date cannot be parsed.
        requests.RequestException: Retrieval fails.
    """
    response = api.get_booking(booking_id)
    check_json_booking(response, expected_payload)


def check_json_booking(response: Response, expected_payload: dict[str, Any]) -> None:
    """Validate the JSON booking schema and compare all expected values.

    Args:
        response: JSON booking response from a read or write operation.
        expected_payload: Complete expected booking data.

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
    check_booking_field_types(body)
    for field in ('checkin', 'checkout'):
        value = body['bookingdates'][field]
        assert date.fromisoformat(value).isoformat() == value


def check_booking_field_types(body: Any) -> None:
    """Validate required booking fields and types independently of calendar values.

    Args:
        body: Decoded booking object to validate.

    Raises:
        AssertionError: A required field is missing or has an invalid JSON type.
    """
    assert isinstance(body, dict)
    for field in ('firstname', 'lastname', 'additionalneeds'):
        assert isinstance(body.get(field), str), f'Expected string field {field}'
    check_number(body.get('totalprice'))
    assert type(body.get('depositpaid')) is bool
    assert isinstance(body.get('bookingdates'), dict)
    for field in ('checkin', 'checkout'):
        value = body['bookingdates'].get(field)
        assert isinstance(value, str)


def _check_booking_values(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Compare contract values using JSON Number semantics after structural checks.

    Args:
        actual: Decoded complete booking data.
        expected: Expected booking values, allowing numerically equal int and float.

    Raises:
        AssertionError: Required fields or JSON types are invalid.
        ResponseValuesMismatch: Booking values differ.
    """
    check_booking_field_types(actual)
    try:
        assert actual == expected
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error


def _check_current_booking_values(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Compare booking data and top-level value types after response validation.

    Args:
        actual: Decoded booking data from a validated response envelope.
        expected: Expected booking values, including current-behavior cases.

    Raises:
        ResponseValuesMismatch: Booking values or their types differ.
    """
    try:
        assert actual == expected
        for name, value in expected.items():
            assert type(actual[name]) is type(value), f'Unexpected type for {name}'
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error


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


def check_form_update_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Check the URL-encoded update representation shown in the documentation.

    Args:
        response: Update response requested as form-urlencoded.
        expected_payload: Expected booking fields.

    Raises:
        AssertionError: The status or encoded fields differ from the example structure.
        FormResponseMismatch: The service returns its confirmed serializer error.
        ValueError: The body is not valid URL-encoded data.
    """
    fields = form_response_fields(response)
    for name in ('firstname', 'lastname', 'totalprice', 'additionalneeds'):
        assert fields.get(name) == [str(expected_payload[name])]
    assert fields.get('depositpaid') == [str(expected_payload['depositpaid']).lower()]
    for name in ('checkin', 'checkout'):
        assert fields.get(f'bookingdates[{name}]') == [expected_payload['bookingdates'][name]]


def form_response_fields(response: Response) -> dict[str, list[str]]:
    """Parse form fields while identifying the confirmed serializer error separately.

    Args:
        response: Response requested as application/x-www-form-urlencoded.

    Returns:
        dict[str, list[str]]: Parsed fields, including blank values.

    Raises:
        AssertionError: The HTTP status or body structure is unexpected.
        FormResponseMismatch: The service returns its confirmed serializer error.
        ValueError: The response is not valid form data.
    """
    check_status_code(response, 200)
    if response.text == 'formurlencoded is not a function':
        raise FormResponseMismatch(response.text)
    assert '=' in response.text, response.text
    return parse_qs(response.text, keep_blank_values=True, strict_parsing=True)
