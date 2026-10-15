"""Shared API transport and response contract checks."""

from dataclasses import dataclass
from typing import Any

import requests

from constants import CREATE_BOOKING_PATH
from constants import DELETE_BOOKING_PATH
from constants import GET_BOOKINGS_PATH


@dataclass
class ApiClient:
    """Send bounded requests without automatic retries."""

    session: requests.Session
    base_url: str
    timeout: float

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

    def create_booking(self, payload: dict[str, Any]) -> requests.Response:
        """Create a booking for test data setup.

        Args:
            payload: Booking data sent as a JSON request body.

        Returns:
            requests.Response: Booking creation response returned by the service.

        Raises:
            requests.RequestException: The request fails, including timeouts.
        """
        return self.session.post(f'{self.base_url}{CREATE_BOOKING_PATH}', json=payload, timeout=self.timeout)

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


@dataclass(frozen=True)
class Booking:
    """Store the ID and original payload of a test-owned booking."""

    booking_id: int
    payload: dict[str, Any]
