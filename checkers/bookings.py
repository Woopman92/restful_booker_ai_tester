"""Response schema and booking ID checks."""

from requests import Response


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
        AssertionError: Response validation fails or the ID sets differ.
        ValueError: The response body is not valid JSON.
    """
    actual_ids = booking_ids(response)
    assert actual_ids == expected_ids


def check_booking_presence(response: Response, booking_id: int, expected_present: bool = True) -> None:
    """Check whether the owned booking is present in the returned IDs.

    Args:
        response: Booking list response to validate.
        booking_id: ID of the test-owned booking to locate.
        expected_present: Whether the booking should be present. Defaults to True.

    Raises:
        AssertionError: Response validation fails or booking presence is unexpected.
        ValueError: The response body is not valid JSON.
    """
    actual_ids = booking_ids(response)
    assert (booking_id in actual_ids) == expected_present
