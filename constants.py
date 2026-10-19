"""Service host, endpoint paths and test credentials."""

import os

# Base address of the service under test.
BASE_URL = os.getenv('BOOKER_BASE_URL', 'https://restful-booker.herokuapp.com').rstrip('/')

# Authentication endpoint paths.
CREATE_TOKEN_PATH = '/auth'

# Booking endpoint paths.
GET_BOOKINGS_PATH = '/booking'
CREATE_BOOKING_PATH = '/booking'
UPDATE_BOOKING_PATH = '/booking/{booking_id}'
DELETE_BOOKING_PATH = '/booking/{booking_id}'

# Credentials for authentication and test data cleanup.
USERNAME = 'admin'
PASSWORD = 'password123'
