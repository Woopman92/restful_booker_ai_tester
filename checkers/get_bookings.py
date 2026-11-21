"""Presence checks specific to GetBookings filtering and listing scenarios."""

from requests import Response

from checkers.common import booking_ids
from checkers.errors import ResponseValuesMismatch


def check_booking_presence(response: Response, booking_id: int, expected_present: bool = True) -> None:
    """Check whether the owned booking is present in the returned IDs.

    Args:
        response: Booking list response to validate.
        booking_id: ID of the test-owned booking to locate.
        expected_present: Whether the booking should be present. Defaults to True.

    Raises:
        AssertionError: Response status, media type or schema is invalid.
        ResponseValuesMismatch: Booking presence is unexpected.
        ValueError: The response body is not valid JSON.
    """
    actual_ids = booking_ids(response)
    try:
        assert (booking_id in actual_ids) == expected_present
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error
