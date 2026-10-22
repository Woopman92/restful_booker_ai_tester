"""Common checks for API error responses."""

from http import HTTPStatus

from requests import Response


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
    assert response.status_code == expected_status_code
