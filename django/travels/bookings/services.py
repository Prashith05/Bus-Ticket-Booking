import re
from datetime import datetime, timedelta, timezone as dt_timezone

from django.utils import timezone

from .models import Bus, Trip

# Bus start times are stored as plain clock times ("08:00") and mean Indian time,
# while the project itself runs in UTC. India has no daylight saving, so a fixed
# +05:30 offset is correct (and works on Python 3.8 without extra packages).
BUS_TZ = dt_timezone(timedelta(hours=5, minutes=30))


def departure_datetime(trip):
    """The exact moment the bus of this trip leaves (timezone-aware)."""
    return datetime.combine(trip.date, trip.bus.start_time, tzinfo=BUS_TZ)


# Tickets stop selling this many minutes before the bus leaves, so a person who is still
# paying or confirming when the bus pulls away can never end up with a seat that is not honoured.
BOOKING_CUTOFF_MINUTES = 15

# Seats one request may book, and seats one person may hold on the same bus and date (all their
# bookings together, cancelled ones not counted). The second limit stops one person from booking
# again and again to take the whole bus.
MAX_SEATS_PER_BOOKING = 6
MAX_SEATS_PER_USER_PER_TRIP = 6


def booking_closes_at(trip):
    """The moment booking stops for this trip (timezone-aware)."""
    return departure_datetime(trip) - timedelta(minutes=BOOKING_CUTOFF_MINUTES)


def is_booking_closed(trip):
    """True from BOOKING_CUTOFF_MINUTES before departure onwards (this includes after departure)."""
    return timezone.now() >= booking_closes_at(trip)


def has_departed(trip):
    """True once the bus has left: its ticket can no longer be cancelled."""
    return timezone.now() >= departure_datetime(trip)

# Customers can search and book this many days ahead (today + 30 days).
BOOKING_WINDOW_DAYS = 30


def create_trips_for_date(date):
    """Make sure every bus has a trip on `date` (each new trip also gets its seats)."""
    existing = set(Trip.objects.filter(date=date).values_list('bus_id', flat=True))
    for bus in Bus.objects.exclude(id__in=existing):
        Trip.objects.get_or_create(bus=bus, date=date)


def ensure_trips(date):
    """Buses run every day: create the trips for a searched date on demand,
    but only inside the booking window (not in the past, not too far ahead)."""
    today = timezone.localdate()
    if date < today or date > today + timedelta(days=BOOKING_WINDOW_DAYS):
        return
    create_trips_for_date(date)


# ---------------------------------------------------------------- passenger details
GENDER_CODES = ('M', 'F', 'O')
MIN_PASSENGER_AGE, MAX_PASSENGER_AGE = 1, 120
_PHONE_RE = re.compile(r'^[6-9]\d{9}$')          # Indian mobile number: 10 digits starting with 6-9


class PassengerError(ValueError):
    """The passenger details in a booking request are missing or invalid (message is user-facing)."""


def clean_phone(value):
    """'+91 98765 43210' / '098765-43210' / '9876543210' -> '9876543210'. Raises PassengerError."""
    digits = re.sub(r'[\s\-]', '', str(value or ''))
    if digits.startswith('+91'):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    if not _PHONE_RE.match(digits):
        raise PassengerError('Please enter a valid 10-digit mobile number.')
    return digits


def clean_passenger(raw, position):
    """Validate one passenger {"name", "age", "gender"}; `position` (1, 2, ...) is used in messages."""
    who = f'Passenger {position}'
    if not isinstance(raw, dict):
        raise PassengerError(f'{who}: details are missing.')

    name = ' '.join(str(raw.get('name') or '').split())       # trim and collapse spaces
    if len(name) < 2:
        raise PassengerError(f'{who}: please enter the full name.')
    if len(name) > 100:
        raise PassengerError(f'{who}: the name is too long (100 letters at most).')
    if not re.search(r'[^\W\d_]', name) or re.search(r'[<>]', name):
        raise PassengerError(f'{who}: the name must contain letters and no special symbols.')

    age = raw.get('age')
    if isinstance(age, bool) or isinstance(age, float) or age in (None, ''):
        raise PassengerError(f'{who}: please enter the age.')
    try:
        age = int(age)
    except (TypeError, ValueError):
        raise PassengerError(f'{who}: the age must be a whole number.')
    if not MIN_PASSENGER_AGE <= age <= MAX_PASSENGER_AGE:
        raise PassengerError(f'{who}: the age must be between {MIN_PASSENGER_AGE} and {MAX_PASSENGER_AGE}.')

    gender = str(raw.get('gender') or '').strip().upper()
    if gender not in GENDER_CODES:
        raise PassengerError(f'{who}: please choose the gender.')

    return {'name': name, 'age': age, 'gender': gender}
