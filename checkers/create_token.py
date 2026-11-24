"""Authentication response checks without exposing credentials or issued tokens."""

from requests import Response

from checkers.common import json_body


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
    body = json_body(response)
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
    body = json_body(response)
    valid_schema = isinstance(body, dict) and body.keys() == {'reason'} and isinstance(body['reason'], str)
    assert valid_schema, 'Expected only a string reason'
    valid_reason = body['reason'] == 'Bad credentials'
    assert valid_reason, 'Unexpected reason for authentication failure'
