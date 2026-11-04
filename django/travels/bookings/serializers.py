from rest_framework import serializers
from .models import Bus,Seat,Booking
from django.contrib.auth.models import User


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
    seats = SeatSerializer(many=True,read_only=True)
    class Meta:
        model = Bus
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    bus_name = serializers.CharField(source='bus.bus_name', read_only=True)
    origin = serializers.CharField(source='bus.origin', read_only=True)
    destination = serializers.CharField(source='bus.destination', read_only=True)
    start_time = serializers.TimeField(source='bus.start_time', read_only=True)
    reach_time = serializers.TimeField(source='bus.reach_time', read_only=True)
    seat_number = serializers.CharField(source='seat.seat_number', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'bus', 'seat', 'booking_time',
                  'bus_name', 'origin', 'destination',
                  'start_time', 'reach_time', 'seat_number']
        read_only_fields = fields
