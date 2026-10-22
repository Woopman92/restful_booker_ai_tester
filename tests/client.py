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
from constants import UPDATE_BOOKING_PATH


@dataclass
class ApiClient:
    """Send bounded requests without automatic retries."""

    session: requests.Session
    base_url: str
    timeout: float

    def create_token(
        self,
        payload: dict[str, Any] | None = None,
        body: str | None = None,
        content_type: str = 'application/json'
    ) -> requests.Response:
        """Request an authentication token without persisting credentials in the session.

        Args:
            payload: JSON credentials, omitted when sending a raw body.
            body: Raw body for malformed or empty payload scenarios.
            content_type: Media type of the request body.

        Returns:
            requests.Response: Authentication response from the service.

        Raises:
            requests.RequestException: The request fails, including timeouts.
            ValueError: Both a JSON payload and a raw body are provided.
        """
        if payload is not None and body is not None:
            raise ValueError('Provide either a JSON payload or a raw body')
        return self.session.post(
            f'{self.base_url}{CREATE_TOKEN_PATH}',
            json=payload,
            data=body,
            headers={'Content-Type': content_type},
            timeout=self.timeout,
        )

    def update_booking(
        self,
        booking_id: int | str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        auth: tuple[str, str] | None = None,
        authorization: str | None = None,
        body: str | dict[str, Any] | None = None,
        content_type: str | None = 'application/json',
        accept: str | None = 'application/json'
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

        Returns:
            requests.Response: Booking replacement response.

        Raises:
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
        return self.session.put(
            f'{self.base_url}{path}',
            json=payload,
            data=body,
            headers=headers,
            auth=auth,
            timeout=self.timeout,
        )

    def get_bookings(self, params: dict[str, str] | list[tuple[str, str]] | None = None) -> requests.Response:
        """Retrieve booking IDs using optional query parameters.

        Args:
            params: Query parameters as a mapping or pairs allowing repeated keys.
                Defaults to None to retrieve all booking IDs.

        Returns:
            requests.Response: Booking list response returned by the service.

        Raises:
            requests.RequestException: The request fails, including timeouts.
        """
        return self.session.get(f'{self.base_url}{GET_BOOKINGS_PATH}', params=params, timeout=self.timeout)

    def get_booking(self, booking_id: int | str, accept: str | None = 'application/json') -> requests.Response:
        """Read one booking without changing shared session headers.

        Args:
            booking_id: ID encoded as a single URL path segment.
            accept: Desired response media type. None removes the session Accept header.

        Returns:
            requests.Response: Response to the booking retrieval request.

        Raises:
            requests.RequestException: The request fails, including timeouts.
        """
        path = GET_BOOKING_PATH.format(booking_id=quote(str(booking_id), safe=''))
        return self.session.get(f'{self.base_url}{path}', headers={'Accept': accept}, timeout=self.timeout)

    def create_booking(
        self,
        payload: dict[str, Any] | None = None,
        body: str | dict[str, Any] | None = None,
        content_type: str | None = 'application/json',
        accept: str | None = 'application/json'
    ) -> requests.Response:
        """Create a booking using JSON, a raw body or encoded form fields.

        Args:
            payload: Booking fields sent as JSON.
            body: Raw JSON/XML text or a mapping sent as form data.
            content_type: Request media type; None omits the header.
            accept: Desired response media type; None omits the header.

        Returns:
            requests.Response: Booking creation response returned by the service.

        Raises:
            requests.RequestException: The request fails, including timeouts.
            ValueError: Both payload and body are supplied.
        """
        if payload is not None and body is not None:
            raise ValueError('Provide either a JSON payload or a raw/form body')
        return self.session.post(
            f'{self.base_url}{CREATE_BOOKING_PATH}',
            json=payload,
            data=body,
            headers={'Content-Type': content_type, 'Accept': accept},
            timeout=self.timeout,
        )

    def delete_booking(self, booking_id: int, auth: tuple[str, str]) -> requests.Response:
        """Delete a test-owned booking during cleanup.

        Args:
            booking_id: ID of the booking to delete.
            auth: Username and password for HTTP Basic authentication.

        Returns:
            requests.Response: Booking deletion response returned by the service.

        Raises:
            requests.RequestException: The request fails, including timeouts.
        """
        path = DELETE_BOOKING_PATH.format(booking_id=booking_id)
        return self.session.delete(f'{self.base_url}{path}', auth=auth, timeout=self.timeout)
