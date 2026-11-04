from datetime import timedelta

from django.utils import timezone

from .models import Bus, Trip

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
