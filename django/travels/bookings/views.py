from django.db import transaction
from django.shortcuts import render

# authicate, permission, token, status, response, generics, api views
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS, BasePermission
from rest_framework.authtoken.models import Token
from rest_framework import status, generics
from rest_framework.views import APIView
from .serializers import (
    UserRegisterSerializer, BusSerializer, BookingSerializer, SeatSerializer,
    TripSerializer, TripDetailSerializer,
)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import Bus,Seat,Booking,Trip
from .services import ensure_trips
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date as date_type


 
# Create your views here.
class IsAdminOrReadOnly(BasePermission):
    """Anyone can read buses; only admin users can create, update or delete."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class RegisterView(APIView):
    def post(self,request):
        serializer = UserRegisterSerializer(data = request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token':token.key}, status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username = username,password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token':token.key,
                'user_id':user.id
            },status=status.HTTP_200_OK)
        else:
            return Response({'error':'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    

class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    permission_classes = [IsAdminOrReadOnly]

class BusDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    permission_classes = [IsAdminOrReadOnly]


def _trips_with_availability():
    return (
        Trip.objects.select_related('bus')
        .annotate(available_seats=Count('seats', filter=Q(seats__is_booked=False)))
    )


class TripListView(generics.ListAPIView):
    """GET /api/trips/?date=YYYY-MM-DD&origin=..&destination=..
    Buses running on that date (today if no date is given) with free-seat counts."""
    serializer_class = TripSerializer

    def get_queryset(self):
        raw_date = self.request.query_params.get('date')
        if raw_date:
            try:
                travel_date = date_type.fromisoformat(raw_date)
            except ValueError:
                raise ValidationError({'date': 'Use the format YYYY-MM-DD.'})
        else:
            travel_date = timezone.localdate()

        ensure_trips(travel_date)

        trips = _trips_with_availability().filter(date=travel_date)
        origin = self.request.query_params.get('origin')
        destination = self.request.query_params.get('destination')
        if origin:
            trips = trips.filter(bus__origin__icontains=origin)
        if destination:
            trips = trips.filter(bus__destination__icontains=destination)
        return trips.order_by('bus__start_time', 'id')


class TripDetailView(generics.RetrieveAPIView):
    """GET /api/trips/<id>/ - one trip with its seats (always in S1, S2, ... order)."""
    serializer_class = TripDetailSerializer

    def get_queryset(self):
        return _trips_with_availability()

class BookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        seat_id = request.data.get('seat')
        try:
            # Lock the seat row so two users cannot book the same seat at once.
            with transaction.atomic():
                seat = Seat.objects.select_for_update().get(id=seat_id)
                if seat.is_booked:
                    return Response({'error': 'Seat already booked'}, status=status.HTTP_400_BAD_REQUEST)

                trip = seat.trip
                if trip.date < timezone.localdate():
                    return Response({'error': 'This trip has already taken place'}, status=status.HTTP_400_BAD_REQUEST)

                seat.is_booked = True
                seat.save()

                booking = Booking.objects.create(
                    user=request.user,
                    trip=trip,
                    seat=seat
                )
            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (Seat.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Invalid Seat ID'}, status=status.HTTP_404_NOT_FOUND)


class UserBookingView(APIView):
    permission_classes =[IsAuthenticated]

    def get(self,request,user_id):
        if request.user.id != user_id:
            return Response({'error':'Forbidden'},status=status.HTTP_403_FORBIDDEN)
        
        bookings = Booking.objects.filter(user_id=user_id).select_related('trip__bus', 'seat')
        serializer =BookingSerializer(bookings,many=True)
        return Response(serializer.data)
