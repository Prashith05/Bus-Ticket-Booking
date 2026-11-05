from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Trip, Seat


@receiver(post_save, sender=Trip)
def create_seats_for_trip(sender, instance, created, **kwargs):
    """Every new trip gets its own seats S1..Sn (n = the bus's number of seats)."""
    if created:
        Seat.objects.bulk_create([
            Seat(trip=instance, seat_number=f"S{i}")
            for i in range(1, instance.bus.no_of_seats + 1)
        ])
