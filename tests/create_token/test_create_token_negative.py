"""Current authentication failure behavior where the error contract is unspecified."""

import json
from typing import Any

import pytest

from checkers.auth import check_bad_credentials
from checkers.common import check_plain_text_error
from tests.support import ApiClient

pytestmark = pytest.mark.negative


class TestInvalidCredentials:
    """Record authentication responses to invalid credential values."""

    @pytest.mark.parametrize(
        'fields',
        [('username', ), ('password', ), ('username', 'password')],
        ids=['wrong-username', 'wrong-password', 'both-wrong'],
    )
    def test_wrong_credentials(self, api: ApiClient, credentials: dict[str, str], fields: tuple[str, ...]) -> None:
        """Record rejection when one or both credentials differ from the configured values."""
        # The expected error response is unspecified; this test records current service behavior.
        payload = {**credentials, **{field: credentials[field] + 'Invalid' for field in fields}}
        response = api.create_token(payload=payload)
        check_bad_credentials(response)

    @pytest.mark.parametrize('field', ['username', 'password'])
    @pytest.mark.parametrize('value', ['', 'x'], ids=['empty', 'one-character'])
    def test_short_credentials(self, api: ApiClient, credentials: dict[str, str], field: str, value: str) -> None:
        """Record rejection of empty and one-character credentials without inventing length limits."""
        # The expected error response is unspecified; this test records current service behavior.
        payload = {**credentials, field: value}
        response = api.create_token(payload=payload)
        check_bad_credentials(response)

    def test_both_credentials_empty(self, api: ApiClient) -> None:
        """Record rejection when both credential strings are empty."""
        # The expected error response is unspecified; this test records current service behavior.
        response = api.create_token(payload={'username': '', 'password': ''})
        check_bad_credentials(response)


class TestInvalidAuthPayload:
    """Record missing fields, invalid JSON types and request format handling."""

    @pytest.mark.parametrize('field', ['username', 'password'])
    def test_missing_field(self, api: ApiClient, credentials: dict[str, str], field: str) -> None:
        """Record rejection when one required field is absent."""
        # The expected error response is unspecified; this test records current service behavior.
        payload = dict(credentials)
        del payload[field]
        response = api.create_token(payload=payload)
        check_bad_credentials(response)

    @pytest.mark.parametrize('field', ['username', 'password'])
    @pytest.mark.parametrize('value', [None, 123, True, [], {}], ids=['null', 'number', 'boolean', 'array', 'object'])
    def test_invalid_field_type(self, api: ApiClient, credentials: dict[str, str], field: str, value: Any) -> None:
        """Record rejection of non-string JSON credentials."""
        # The expected error response is unspecified; this test records current service behavior.
        payload = {**credentials, field: value}
        response = api.create_token(payload=payload)
        check_bad_credentials(response)

    def test_empty_object(self, api: ApiClient) -> None:
        """Record rejection of a JSON object without credentials."""
        # The expected error response is unspecified; this test records current service behavior.
        response = api.create_token(payload={})
        check_bad_credentials(response)

    def test_empty_body(self, api: ApiClient) -> None:
        """Record the response to a completely empty request body."""
        # The expected error response is unspecified; this test records current service behavior.
        response = api.create_token(body='')
        check_bad_credentials(response)

    def test_malformed_json(self, api: ApiClient) -> None:
        """Record the response to a truncated JSON object."""
        # The expected error response is unspecified; this test records current service behavior.
        response = api.create_token(body='{"username":')
        check_plain_text_error(response, expected_status_code=400)

    def test_unsupported_content_type(self, api: ApiClient, credentials: dict[str, str]) -> None:
        """Record the response to valid credentials sent as plain text."""
        # The expected error response is unspecified; this test records current service behavior.
        response = api.create_token(body=json.dumps(credentials), content_type='text/plain')
        check_bad_credentials(response)
