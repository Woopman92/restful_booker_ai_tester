"""Authentication response checks without exposing credentials or issued tokens."""

from requests import Response


def check_created_token(response: Response) -> str:
    """Validate the documented success response and return its token.

    Args:
        response: Token creation response.

    Returns:
        str: Validated token for subsequent authenticated requests.

    Raises:
        AssertionError: The media type or token schema is unexpected.
        ValueError: The body is not valid JSON.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    body = response.json()
    assert isinstance(body, dict), 'Expected an authentication object'
    valid_token = isinstance(body.get('token'), str)
    assert valid_token, 'Expected a string token'
    return body['token']


def check_bad_credentials(response: Response) -> None:
    """Check the observed JSON authentication failure without printing its body.

    Args:
        response: Authentication failure response.

    Raises:
        AssertionError: The media type or failure schema differs.
        ValueError: The body is not valid JSON.
    """
    assert response.headers.get('Content-Type', '').split(';')[0] == 'application/json'
    body = response.json()
    valid_failure = isinstance(body, dict) and body == {'reason': 'Bad credentials'}
    assert valid_failure, 'Expected only the Bad credentials reason and no token'
