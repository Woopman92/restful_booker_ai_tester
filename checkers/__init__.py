"""Reusable response checks with pytest assertion introspection."""

import pytest

pytest.register_assert_rewrite(
    'checkers.common',
    'checkers.create_token',
    'checkers.get_bookings',
    'checkers.create_booking',
    'checkers.delete_booking',
    'checkers.partial_update_booking',
    'checkers.update_booking'
)
