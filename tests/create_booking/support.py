"""Response tracking for isolated booking creation tests."""

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

from requests import Response

from checkers.common import booking_ids
from constants import BOOKER_PASSWORD
from constants import BOOKER_USERNAME
from constants import CREATE_BOOKING_PATH
from tests.client import ApiClient


@dataclass
class CreationTracker:
    """Register owned IDs before assertions and recover IDs hidden by error responses."""

    api: ApiClient
    payload: dict[str, Any]
    original_names: dict[str, str]
    owned_ids: set[int] = field(default_factory=set)
    recovered_ids: set[int] = field(default_factory=set)
    needs_lookup: bool = False
    expected_recovered_count: int = 0

    def capture(self, response: Response, **kwargs: Any) -> Response:
        """Register IDs from this test's POST responses before response assertions run.

        Args:
            response: Response dispatched by the session hook.
            **kwargs: Additional requests hook arguments.

        Returns:
            Response: Unmodified response, including when its body is not parseable.
        """
        if response.request.method != 'POST' or urlsplit(response.request.url).path != CREATE_BOOKING_PATH:
            return response
        booking_id = None
        try:
            body = response.json()
            if isinstance(body, dict):
                booking_id = body.get('bookingid')
        except ValueError:
            try:
                root = ElementTree.fromstring(response.text)
                text = root.findtext('bookingid')
                if text is not None:
                    booking_id = int(text)
            except (ElementTree.ParseError, ValueError):
                pass
        if type(booking_id) is int:
            self.owned_ids.add(booking_id)
        else:
            self.needs_lookup = True
        return response

    def cleanup(self) -> None:
        """Discover unreported creations and attempt deletion of every registered record.

        Raises:
            AssertionError: ID discovery or deletion fails; known IDs are still cleaned up.
        """
        errors = []
        if self.needs_lookup:
            key = 'firstname' if self.payload.get('firstname') == self.original_names['firstname'] else 'lastname'
            try:
                response = self.api.get_bookings(params={key: self.original_names[key]})
                found = booking_ids(response)
                self.recovered_ids = found - self.owned_ids
                self.owned_ids.update(found)
            except Exception as error:
                errors.append(f'Owned ID discovery failed: {error}')
        for booking_id in sorted(self.owned_ids):
            try:
                response = self.api.delete_booking(booking_id, auth=(BOOKER_USERNAME, BOOKER_PASSWORD))
                if response.status_code != 201:
                    errors.append(f'ID {booking_id}: HTTP {response.status_code}')
            except Exception as error:
                errors.append(f'ID {booking_id}: {error}')
        assert not errors, 'Cleanup failed: ' + '; '.join(errors)
        assert len(self.recovered_ids) == self.expected_recovered_count, (
            f'Unexpected records hidden by a creation response: {sorted(self.recovered_ids)}'
        )
