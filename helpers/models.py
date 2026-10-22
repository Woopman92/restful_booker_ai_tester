"""Dataclasses shared by fixtures, tests and helpers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Booking:
    """Store the ID and original payload of a test-owned booking."""

    booking_id: int
    payload: dict[str, Any]
