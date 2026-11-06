from rest_framework import serializers
from .models import Bus,Seat,Booking,Trip
from django.contrib.auth.models import User
from .services import has_departed


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True)

    class Meta:
        model = User
        fields = ['username','email','password']

    def create(self,validate_date):
        user = User.objects.create_user(
            username= validate_date['username'],
            email=validate_date['email'],
            password=validate_date['password']
        )
        return user

class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id','seat_number','is_booked']

class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = '__all__'


class TripSerializer(serializers.ModelSerializer):
    """A bus on a date, as shown in the search results."""
    bus_id = serializers.IntegerField(source='bus.id', read_only=True)
    bus_name = serializers.CharField(source='bus.bus_name', read_only=True)
    number = serializers.CharField(source='bus.number', read_only=True)
    origin = serializers.CharField(source='bus.origin', read_only=True)
    destination = serializers.CharField(source='bus.destination', read_only=True)
    features = serializers.CharField(source='bus.features', read_only=True)
    start_time = serializers.TimeField(source='bus.start_time', read_only=True)
    reach_time = serializers.TimeField(source='bus.reach_time', read_only=True)
    price = serializers.DecimalField(source='bus.price', max_digits=8, decimal_places=2, read_only=True)
    available_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = Trip
        fields = ['id', 'date', 'bus_id', 'bus_name', 'number', 'origin', 'destination',
                  'features', 'start_time', 'reach_time', 'price', 'available_seats']


class TripDetailSerializer(TripSerializer):
    """One trip with its seats, always in seat-creation order (S1, S2, ...)
    so a booked seat never jumps to the end of the list."""
    seats = serializers.SerializerMethodField()

    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + ['seats']

    def get_seats(self, trip):
        return SeatSerializer(trip.seats.order_by('id'), many=True).data


class BookingSerializer(serializers.ModelSerializer):
    bus = serializers.IntegerField(source='trip.bus_id', read_only=True)
    travel_date = serializers.DateField(source='trip.date', read_only=True)
    bus_name = serializers.CharField(source='trip.bus.bus_name', read_only=True)
    origin = serializers.CharField(source='trip.bus.origin', read_only=True)
    destination = serializers.CharField(source='trip.bus.destination', read_only=True)
    start_time = serializers.TimeField(source='trip.bus.start_time', read_only=True)
    reach_time = serializers.TimeField(source='trip.bus.reach_time', read_only=True)
    seat_number = serializers.CharField(source='seat.seat_number', read_only=True)
    can_cancel = serializers.SerializerMethodField()

    def get_can_cancel(self, booking):
        # Only a confirmed ticket for a bus that has not left yet can be cancelled.
        return booking.status == Booking.STATUS_CONFIRMED and not has_departed(booking.trip)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'bus', 'trip', 'seat', 'booking_time', 'travel_date',
                  'bus_name', 'origin', 'destination',
                  'start_time', 'reach_time', 'seat_number',
                  'status', 'cancelled_at', 'can_cancel']
        read_only_fields = fields
