"""Presence checks specific to GetBookings filtering and listing scenarios."""

from requests import Response

from checkers.common import booking_ids
from checkers.errors import ResponseValuesMismatch


def check_get_bookings_response(
    response: Response,
    *,
    exact_ids: set[int] | None = None,
    present_ids: set[int] | None = None,
    absent_ids: set[int] | None = None,
) -> None:
    """Validate the booking list and compare its IDs with the expected sets.

    Args:
        response: GetBookings response to validate.
        exact_ids: Complete expected set, including an empty set for an empty list.
        present_ids: IDs that must appear when other IDs are allowed.
        absent_ids: IDs that must be excluded.

    Raises:
        ValueError: Expectations are missing or conflicting, or the body is invalid JSON.
        AssertionError: The media type, list schema or ID uniqueness is invalid.
        ResponseValuesMismatch: The validated IDs differ from the expectations.
    """
    if exact_ids is not None and (present_ids is not None or absent_ids is not None):
        raise ValueError('Use exact_ids independently of present_ids and absent_ids')
    required = present_ids or set()
    forbidden = absent_ids or set()
    if exact_ids is None and not (required or forbidden):
        raise ValueError('Specify exact_ids or at least one ID to include or exclude')
    if required & forbidden:
        raise ValueError('An ID cannot be both required and forbidden')

    actual_ids = booking_ids(response)
    try:
        if exact_ids is not None:
            assert actual_ids == exact_ids
        else:
            assert required <= actual_ids, f'Missing booking IDs: {required - actual_ids}'
            assert not (forbidden & actual_ids), f'Unexpected booking IDs: {forbidden & actual_ids}'
    except AssertionError as error:
        raise ResponseValuesMismatch(str(error)) from error
