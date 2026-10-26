"""Reusable response checks with pytest assertion introspection."""

import pytest

pytest.register_assert_rewrite(
    'checkers.common',
    'checkers.bookings',
    'checkers.auth',
    'checkers.get_booking',
    'checkers.create_booking',
    'checkers.delete_booking',
    'checkers.partial_update_booking',
    'checkers.update_booking'
)
