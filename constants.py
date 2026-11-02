"""Service host, endpoint paths and test credentials."""

import os

# Base address of the service under test.
BASE_URL = os.getenv('BOOKER_BASE_URL', 'https://restful-booker.herokuapp.com').rstrip('/')

# Service availability check at the start of each test session.
PING_PATH = '/ping'
PING_ATTEMPTS = 3
PING_TIMEOUT = 5
PING_RETRY_DELAY = 2

# Authentication endpoint paths.
CREATE_TOKEN_PATH = '/auth'

# Booking endpoint paths.
GET_BOOKINGS_PATH = '/booking'
GET_BOOKING_PATH = '/booking/{booking_id}'
CREATE_BOOKING_PATH = '/booking'
UPDATE_BOOKING_PATH = '/booking/{booking_id}'
PARTIAL_UPDATE_BOOKING_PATH = '/booking/{booking_id}'
DELETE_BOOKING_PATH = '/booking/{booking_id}'

# Public demo credentials published by Restful Booker; intentionally kept visible for authentication and cleanup.
BOOKER_USERNAME = 'admin'
BOOKER_PASSWORD = 'password123'
