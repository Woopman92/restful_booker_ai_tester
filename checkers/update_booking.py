"""UpdateBooking response checks by representation."""

from typing import Any

from requests import Response

from checkers.common import check_booking_form_response
from checkers.common import check_booking_json_response
from checkers.common import check_booking_xml_response


def check_update_booking_json_response(
    response: Response, expected_payload: dict[str, Any], *, schema_example: dict[str, Any] | None = None
) -> None:
    """Validate the booking returned by a JSON update response.

    Args:
        response: UpdateBooking response to validate.
        expected_payload: Expected replacement booking values.
        schema_example: Optional example defining the observed booking schema.

    Raises:
        AssertionError: The media type, schema or booking values differ.
        ValueError: JSON or a calendar date cannot be parsed.
    """
    check_booking_json_response(response, expected_payload, schema_example=schema_example)


def check_update_booking_xml_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Validate the booking returned by an XML update response.

    Args:
        response: UpdateBooking response to validate.
        expected_payload: Expected replacement booking values.

    Raises:
        AssertionError: The media type, XML structure or booking values differ.
        xml.etree.ElementTree.ParseError: The XML is malformed.
    """
    check_booking_xml_response(response, expected_payload)


def check_update_booking_form_response(response: Response, expected_payload: dict[str, Any]) -> None:
    """Validate the URL-encoded booking returned by UpdateBooking.

    Args:
        response: UpdateBooking response to validate.
        expected_payload: Expected replacement booking values.

    Raises:
        AssertionError: The form structure or booking values differ.
        FormResponseMismatch: The service returns its confirmed serializer error.
        ValueError: The form data cannot be parsed.
    """
    check_booking_form_response(response, expected_payload)
