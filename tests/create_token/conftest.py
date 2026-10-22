"""Credentials isolated to each authentication test."""

import pytest

from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME


@pytest.fixture
def credentials() -> dict[str, str]:
    """Build valid credentials from constants without changing the shared HTTP session.

    Returns:
        dict[str, str]: Fresh username and password mapping for this test.
    """
    return {'username': BOOKER_USERNAME, 'password': BOOKER_PASSWORD}
