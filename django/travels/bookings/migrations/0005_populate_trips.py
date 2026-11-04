from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def create_trips_and_move_data(apps, schema_editor):
    """Step 2 of 3: keep all existing data.

    For every existing bus:
      * create a trip for today and move the bus's existing seats and bookings onto it
      * create a trip for tomorrow with a fresh set of seats (same seat numbers, all free)
    """
    Bus = apps.get_model('bookings', 'Bus')
    Trip = apps.get_model('bookings', 'Trip')
    Seat = apps.get_model('bookings', 'Seat')
    Booking = apps.get_model('bookings', 'Booking')

    today = timezone.localdate()

    for bus in Bus.objects.all():
        today_trip = Trip.objects.create(bus=bus, date=today)
        existing_numbers = list(
            Seat.objects.filter(bus=bus).order_by('id').values_list('seat_number', flat=True)
        )
        Seat.objects.filter(bus=bus).update(trip=today_trip)
        Booking.objects.filter(bus=bus).update(trip=today_trip)

        tomorrow_trip = Trip.objects.create(bus=bus, date=today + timedelta(days=1))
        Seat.objects.bulk_create([
            Seat(bus=bus, trip=tomorrow_trip, seat_number=number)
            for number in existing_numbers
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_trip'),
    ]

    operations = [
        migrations.RunPython(create_trips_and_move_data, migrations.RunPython.noop),
    ]
