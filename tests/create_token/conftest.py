"""Credentials isolated to each authentication test."""

import pytest

from checkers.auth import check_created_token
from constants import PASSWORD
from constants import USERNAME
from tests.support import ApiClient


@pytest.fixture
def credentials() -> dict[str, str]:
    """Build valid credentials from constants without changing the shared HTTP session.

    Returns:
        dict[str, str]: Fresh username and password mapping for this test.
    """
    return {'username': USERNAME, 'password': PASSWORD}


@pytest.fixture
def first_token(api: ApiClient, credentials: dict[str, str]) -> str:
    """Create the first token for the current test using configured credentials.

    Args:
        api: Client used to request the token.
        credentials: Valid username and password for the service.

    Returns:
        str: Token extracted from a validated successful authentication response.

    Raises:
        AssertionError: The response status or token schema is unexpected.
        ValueError: The response is not valid JSON.
        requests.RequestException: The authentication request fails.
    """
    response = api.create_token(payload=credentials)
    return check_created_token(response)
