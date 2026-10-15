"""Service host and endpoint paths used by the API client."""

import os

BASE_URL = os.getenv('BOOKER_BASE_URL', 'https://restful-booker.herokuapp.com').rstrip('/')
GET_BOOKINGS_PATH = '/booking'
CREATE_BOOKING_PATH = '/booking'
DELETE_BOOKING_PATH = '/booking/{booking_id}'
