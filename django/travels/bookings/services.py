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
