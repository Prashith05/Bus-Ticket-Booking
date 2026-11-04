from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.services import BOOKING_WINDOW_DAYS, create_trips_for_date


class Command(BaseCommand):
    help = "Create trips (with seats) for every bus for the next N days, starting today."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=BOOKING_WINDOW_DAYS + 1,
            help="How many days to generate, counting today (default: %(default)s)",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        for offset in range(options['days']):
            create_trips_for_date(today + timedelta(days=offset))
        self.stdout.write(self.style.SUCCESS(
            f"Trips are ready for the next {options['days']} day(s)."
        ))
