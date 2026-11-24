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
            response = api.delete_booking(
                booking_id, auth=(BOOKER_USERNAME, BOOKER_PASSWORD), expected_status_code=(201, 405)
            )
            if response.status_code == 405:
                api.get_booking(booking_id, expected_status_code=404)
        except Exception as error:
            errors.append(f'ID {booking_id}: {type(error).__name__}: {error}')
    if errors:
        raise CleanupError('Cleanup failed: ' + '; '.join(errors))


def check_plain_text_error(response: Response) -> None:
    """Check the content type and standard HTTP phrase of a plain-text error.

    Args:
        response: Service response to validate.

    Raises:
        AssertionError: The content type or response body is unexpected.
        ValueError: The expected status code is not defined in HTTPStatus.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'text/plain'
    assert response.text == HTTPStatus(response.status_code).phrase


def json_body(response: Response) -> Any:
    """Read a response with the expected JSON media type.

    Args:
        response: Service response to decode.

    Returns:
        Any: Decoded JSON value.

    Raises:
        AssertionError: The media type is unexpected.
        ValueError: The body is not valid JSON.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    return response.json()


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
        AssertionError: The content type, schema or ID uniqueness is invalid.
        ValueError: The response body is not valid JSON.
    """
    body = json_body(response)
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
        AssertionError: Media type or schema is invalid.
        ResponseValuesMismatch: The ID sets differ.
        ValueError: The response body is not valid JSON.
    """
    actual_ids = booking_ids(response)
    try:
        assert actual_ids == expected_ids
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error


def check_booking(
    api: ApiClient,
    booking_id: int,
    expected_payload: dict[str, Any],
    *,
    schema_example: dict[str, Any] | None = None
) -> None:
    """Retrieve an owned booking and validate its full schema and expected values.

    Args:
        api: Client used for the independent retrieval.
        booking_id: ID of the test-owned booking.
        expected_payload: Complete expected booking data.
        schema_example: Optional example of an observed response shape and field types.

    Raises:
        AssertionError: Retrieval status, media type, schema or values differ.
        ValueError: JSON or a calendar date cannot be parsed.
        requests.RequestException: Retrieval fails.
    """
    response = api.get_booking(booking_id)
    check_json_booking(response, expected_payload, schema_example=schema_example)


def check_json_booking(
    response: Response, expected_payload: dict[str, Any], *, schema_example: dict[str, Any] | None = None
) -> None:
    """Validate the JSON booking schema and compare all expected values.

    Args:
        response: JSON booking response from a read or write operation.
        expected_payload: Complete expected booking data.
        schema_example: Optional example of an observed response shape and field types.

    Raises:
        AssertionError: Media type, schema or values differ.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    body = json_body(response)
    check_booking_schema(body, schema_example=schema_example)
    check_booking_values(body, expected_payload)


def check_booking_schema(body: Any, *, schema_example: dict[str, Any] | None = None) -> None:
    """Validate required fields, JSON types and calendar dates of a booking object.

    Args:
        body: Decoded booking object to validate.
        schema_example: Optional example defining the exact observed keys and JSON types.

    Raises:
        AssertionError: Required fields, types or date representations are invalid.
        ValueError: A calendar date cannot be parsed.
    """
    if schema_example is not None:
        check_example_schema(body, schema_example)
        return
    check_booking_field_types(body)
    check_calendar_dates(body)


def check_calendar_dates(body: dict[str, Any]) -> None:
    """Validate the calendar values of structurally valid date strings.

    Args:
        body: Booking with string checkin and checkout fields.

    Raises:
        AssertionError: A date is not in canonical format.
        ValueError: A date cannot be parsed.
    """
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
    assert body.keys() == {'firstname', 'lastname', 'totalprice', 'depositpaid', 'bookingdates', 'additionalneeds'}
    for field in ('firstname', 'lastname', 'additionalneeds'):
        assert isinstance(body.get(field), str), f'Expected string field {field}'
    check_number(body.get('totalprice'))
    assert type(body.get('depositpaid')) is bool
    assert isinstance(body.get('bookingdates'), dict)
    assert body['bookingdates'].keys() == {'checkin', 'checkout'}
    for field in ('checkin', 'checkout'):
        value = body['bookingdates'][field]
        assert isinstance(value, str)


def check_booking_values(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Compare contract values using JSON Number semantics after structural checks.

    Args:
        actual: Decoded complete booking data.
        expected: Expected booking values, allowing numerically equal int and float.

    Raises:
        ResponseValuesMismatch: Booking values differ.
    """
    try:
        assert actual == expected
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error


def check_example_schema(actual: Any, example: Any, path: str = 'booking') -> None:
    """Check exact JSON types and nested structure using an example as the schema.

    Args:
        actual: Decoded response data.
        example: Expected shape, including object keys and positional list items.
        path: Field path used in diagnostics.

    Raises:
        AssertionError: A type, key set or array length differs.
    """
    assert type(actual) is type(example), f'Unexpected type at {path}'
    if isinstance(example, dict):
        assert actual.keys() == example.keys(), f'Unexpected fields at {path}'
        for key, value in example.items():
            check_example_schema(actual[key], value, f'{path}.{key}')
    elif isinstance(example, list):
        assert len(actual) == len(example), f'Unexpected array length at {path}'
        for index, value in enumerate(example):
            check_example_schema(actual[index], value, f'{path}[{index}]')


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
        AssertionError: Observed media type, XML structure or values differ.
        xml.etree.ElementTree.ParseError: The body is not well-formed XML.
    """
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
    expected = _booking_text_fields(expected_payload)
    actual = {}
    for path in expected:
        elements = root.findall(path)
        assert len(elements) == 1, f'Expected one element at {path}'
        actual[path] = elements[0].text
    assert actual == expected


def check_form_update_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Check the URL-encoded update representation shown in the documentation.

    Args:
        response: Update response requested as form-urlencoded.
        expected_payload: Expected booking fields.

    Raises:
        AssertionError: The encoded fields differ from the example structure.
        FormResponseMismatch: The service returns its confirmed serializer error.
        ValueError: The body is not valid URL-encoded data.
    """
    fields = form_response_fields(response)
    check_form_booking_fields(fields, expected_payload)


def check_form_booking_fields(fields: dict[str, list[str]], expected_payload: dict[str, Any], prefix: str = '') -> None:
    """Validate field cardinality before comparing form values.

    Args:
        fields: Parsed URL-encoded fields.
        expected_payload: Booking values before form encoding.
        prefix: Optional outer form field containing the booking.

    Raises:
        AssertionError: A required field is missing, repeated or has an unexpected value.
    """
    expected = {}
    for path, value in _booking_text_fields(expected_payload).items():
        first, *nested = path.split('/')
        key = f'{prefix}[{first}]' if prefix else first
        key += ''.join(f'[{part}]' for part in nested)
        expected[key] = value
    actual = {}
    for key in expected:
        assert key in fields and len(fields[key]) == 1, f'Expected one form field at {key}'
        actual[key] = fields[key][0]
    assert actual == expected


def form_response_fields(response: Response) -> dict[str, list[str]]:
    """Parse form fields while identifying the confirmed serializer error separately.

    Args:
        response: Response requested as application/x-www-form-urlencoded.

    Returns:
        dict[str, list[str]]: Parsed fields, including blank values.

    Raises:
        AssertionError: The body structure is unexpected.
        FormResponseMismatch: The service returns its confirmed serializer error.
        ValueError: The response is not valid form data.
    """
    if response.text == 'formurlencoded is not a function':
        raise FormResponseMismatch(response.text)
    assert '=' in response.text, response.text
    return parse_qs(response.text, keep_blank_values=True, strict_parsing=True)
