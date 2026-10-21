"""Reusable response checks with pytest assertion introspection."""

import pytest

pytest.register_assert_rewrite(
    'checkers.common', 'checkers.bookings', 'checkers.auth', 'checkers.get_booking', 'checkers.create_booking'
)
