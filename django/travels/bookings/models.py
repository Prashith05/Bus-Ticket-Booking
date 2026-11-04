from django.db import models
from django.contrib.auth.models import User
# from django.shortcuts import render

# Create your models here.
class Bus(models.Model):
    bus_name = models.CharField(max_length=100)
    number = models.CharField(max_length=20, unique=True)
    origin = models.CharField(max_length=50)
    destination = models.CharField(max_length=50)
    features = models.TextField()
    start_time = models.TimeField()
    reach_time = models.TimeField()
    no_of_seats = models.PositiveBigIntegerField()
    price = models.DecimalField(max_digits=8,decimal_places=2)

    def __str__(self):
       return f"{self.bus_name} {self.number} {self.origin} {self.destination}"


class Trip(models.Model):
    """One run of a bus on one date. Seats and bookings belong to a trip,
    so seat S1 on 10 Nov and seat S1 on 11 Nov are different seats."""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='trips')
    date = models.DateField()

    class Meta:
        unique_together = ('bus', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.bus.bus_name} {self.bus.number} on {self.date}"


class Seat(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('trip', 'seat_number')

    def __str__(self):
        return f"{self.trip} {self.seat_number} {self.is_booked}"


class Booking(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip,on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat,on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        bus = self.trip.bus
        return f"{self.user.username} {bus.bus_name} {self.trip.date} {bus.start_time}-{bus.reach_time} {self.seat.seat_number}"

