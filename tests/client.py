"""Endpoint-specific API client."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from constants import CREATE_BOOKING_PATH
from constants import CREATE_TOKEN_PATH
from constants import DELETE_BOOKING_PATH
from constants import GET_BOOKING_PATH
from constants import GET_BOOKINGS_PATH
from constants import PARTIAL_UPDATE_BOOKING_PATH
from constants import PING_PATH
from constants import PING_TIMEOUT
from constants import UPDATE_BOOKING_PATH


@dataclass
class ApiClient:
    """Send bounded requests without automatic retries."""

    session: requests.Session
    base_url: str
    timeout: float

    @staticmethod
    def _check_status_code(response: requests.Response, expected_status_code: int | tuple[int, ...]) -> None:
        """Check an HTTP status independently of representation-specific assertions.

        Args:
            response: Service response to validate.
            expected_status_code: Required status or tuple of acceptable statuses.

        Raises:
            AssertionError: The status differs from the expected value.
        """
        allowed = (expected_status_code, ) if isinstance(expected_status_code, int) else expected_status_code
        assert response.status_code in allowed, (
            f'Expected HTTP {expected_status_code}, received HTTP {response.status_code}'
        )

    def ping(self, *, expected_status_code: int = 201) -> requests.Response:
        """Check service availability with a dedicated short timeout.

        Args:
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Health-check response from the service.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The health-check request fails, including timeouts.
        """
        response = self.session.get(f'{self.base_url}{PING_PATH}', timeout=PING_TIMEOUT)
        self._check_status_code(response, expected_status_code)
        return response

    def create_token(
        self,
        payload: dict[str, Any] | None = None,
        body: str | None = None,
        content_type: str = 'application/json',
        *,
        expected_status_code: int = 200
    ) -> requests.Response:
        """Request an authentication token without persisting credentials in the session.

        Args:
            payload: JSON credentials, omitted when sending a raw body.
            body: Raw body for malformed or empty payload scenarios.
            content_type: Media type of the request body.
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Authentication response from the service.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
            ValueError: Both a JSON payload and a raw body are provided.
        """
        if payload is not None and body is not None:
            raise ValueError('Provide either a JSON payload or a raw body')
        response = self.session.post(
            f'{self.base_url}{CREATE_TOKEN_PATH}',
            json=payload,
            data=body,
            headers={'Content-Type': content_type},
            timeout=self.timeout,
        )
        self._check_status_code(response, expected_status_code)
        return response

    def update_booking(
        self,
        booking_id: int | str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        auth: tuple[str, str] | None = None,
        authorization: str | None = None,
        body: str | dict[str, Any] | None = None,
        content_type: str | None = 'application/json',
        accept: str | None = 'application/json',
        *,
        expected_status_code: int = 200
    ) -> requests.Response:
        """Replace an owned booking using one explicit authentication mechanism.

        Args:
            booking_id: ID encoded as one URL path segment.
            payload: Complete JSON replacement payload.
            token: Cookie token sent for this request only.
            auth: Username and password for HTTP Basic authentication.
            authorization: Raw Authorization header for malformed-header scenarios.
            body: Raw text or form fields instead of a JSON payload.
            content_type: Request media type; None omits it for raw bodies.
            accept: Desired response media type; None removes the session header.
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Booking replacement response.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
            ValueError: Body formats or authentication mechanisms conflict.
        """
        if payload is not None and body is not None:
            raise ValueError('Provide either a JSON payload or a raw/form body')
        if sum(value is not None for value in (token, auth, authorization)) > 1:
            raise ValueError('Provide only one authentication mechanism')
        path = UPDATE_BOOKING_PATH.format(booking_id=quote(str(booking_id), safe=''))
        headers = {'Content-Type': content_type, 'Accept': accept, 'Authorization': authorization}
        if token is not None:
            headers['Cookie'] = f'token={token}'
        response = self.session.put(
            f'{self.base_url}{path}',
            json=payload,
            data=body,
            headers=headers,
            auth=auth,
            timeout=self.timeout,
        )
        self._check_status_code(response, expected_status_code)
        return response

    def partial_update_booking(
        self,
        booking_id: int | str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        auth: tuple[str, str] | None = None,
        authorization: str | None = None,
        body: str | dict[str, Any] | None = None,
        content_type: str | None = 'application/json',
        accept: str | None = 'application/json',
        *,
        expected_status_code: int = 200
    ) -> requests.Response:
        """Update supplied booking fields using one explicit authentication mechanism.

        Args:
            booking_id: ID encoded as one URL path segment.
            payload: JSON fields to update; omitted fields should be preserved.
            token: Cookie token sent for this request only.
            auth: Username and password for HTTP Basic authentication.
            authorization: Raw Authorization header for malformed-header scenarios.
            body: Raw text or form fields instead of a JSON payload.
            content_type: Request media type; None omits it for raw bodies.
            accept: Desired response media type; None removes the session header.
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Partial booking update response.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
            ValueError: Body formats or authentication mechanisms conflict.
        """
        if payload is not None and body is not None:
            raise ValueError('Provide either a JSON payload or a raw/form body')
        if sum(value is not None for value in (token, auth, authorization)) > 1:
            raise ValueError('Provide only one authentication mechanism')
        path = PARTIAL_UPDATE_BOOKING_PATH.format(booking_id=quote(str(booking_id), safe=''))
        headers = {'Content-Type': content_type, 'Accept': accept, 'Authorization': authorization}
        if token is not None:
            headers['Cookie'] = f'token={token}'
        response = self.session.patch(
            f'{self.base_url}{path}',
            json=payload,
            data=body,
            headers=headers,
            auth=auth,
            timeout=self.timeout,
        )
        self._check_status_code(response, expected_status_code)
        return response

    def get_bookings(
        self,
        params: dict[str, str] | list[tuple[str, str]] | None = None,
        *,
        expected_status_code: int = 200
    ) -> requests.Response:
        """Retrieve booking IDs using optional query parameters.

        Args:
            params: Query parameters as a mapping or pairs allowing repeated keys.
                Defaults to None to retrieve all booking IDs.
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Booking list response returned by the service.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
        """
        response = self.session.get(f'{self.base_url}{GET_BOOKINGS_PATH}', params=params, timeout=self.timeout)
        self._check_status_code(response, expected_status_code)
        return response

    def get_booking(
        self,
        booking_id: int | str,
        accept: str | None = 'application/json',
        *,
        expected_status_code: int = 200
    ) -> requests.Response:
        """Read one booking without changing shared session headers.

        Args:
            booking_id: ID encoded as a single URL path segment.
            accept: Desired response media type. None removes the session Accept header.
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Response to the booking retrieval request.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
        """
        path = GET_BOOKING_PATH.format(booking_id=quote(str(booking_id), safe=''))
        response = self.session.get(f'{self.base_url}{path}', headers={'Accept': accept}, timeout=self.timeout)
        self._check_status_code(response, expected_status_code)
        return response

    def create_booking(
        self,
        payload: dict[str, Any] | None = None,
        body: str | dict[str, Any] | None = None,
        content_type: str | None = 'application/json',
        accept: str | None = 'application/json',
        *,
        expected_status_code: int = 200
    ) -> requests.Response:
        """Create a booking using JSON, a raw body or encoded form fields.

        Args:
            payload: Booking fields sent as JSON.
            body: Raw JSON/XML text or a mapping sent as form data.
            content_type: Request media type; None omits the header.
            accept: Desired response media type; None omits the header.
            expected_status_code: Required HTTP response status.

        Returns:
            requests.Response: Booking creation response returned by the service.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
            ValueError: Both payload and body are supplied.
        """
        if payload is not None and body is not None:
            raise ValueError('Provide either a JSON payload or a raw/form body')
        response = self.session.post(
            f'{self.base_url}{CREATE_BOOKING_PATH}',
            json=payload,
            data=body,
            headers={'Content-Type': content_type, 'Accept': accept},
            timeout=self.timeout,
        )
        self._check_status_code(response, expected_status_code)
        return response

    def delete_booking(
        self,
        booking_id: int | str,
        auth: tuple[str, str] | None = None,
        token: str | None = None,
        authorization: str | None = None,
        *,
        expected_status_code: int | tuple[int, ...] = 201
    ) -> requests.Response:
        """Delete one booking using an explicit authentication mechanism.

        Args:
            booking_id: ID encoded as a single URL path segment.
            auth: Username and password for HTTP Basic authentication.
            token: Cookie token sent for this request only.
            authorization: Raw Authorization header for malformed-header scenarios.
            expected_status_code: Required HTTP status or acceptable statuses during cleanup.

        Returns:
            requests.Response: Booking deletion response returned by the service.

        Raises:
            AssertionError: The HTTP status differs from the expected status.
            requests.RequestException: The request fails, including timeouts.
            ValueError: Multiple authentication mechanisms are supplied.
        """
        if sum(value is not None for value in (token, auth, authorization)) > 1:
            raise ValueError('Provide only one authentication mechanism')
        path = DELETE_BOOKING_PATH.format(booking_id=quote(str(booking_id), safe=''))
        headers = {'Authorization': authorization}
        if token is not None:
            headers['Cookie'] = f'token={token}'
        response = self.session.delete(f'{self.base_url}{path}', headers=headers, auth=auth, timeout=self.timeout)
        self._check_status_code(response, expected_status_code)
        return response
