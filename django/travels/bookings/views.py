from django.db import transaction
from django.shortcuts import render

# authicate, permission, token, status, response, generics, api views
from django.contrib.auth import authenticate, get_user_model
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
from .services import (
    ensure_trips, has_departed, is_booking_closed, BOOKING_CUTOFF_MINUTES,
    MAX_SEATS_PER_BOOKING, MAX_SEATS_PER_USER_PER_TRIP,
    PassengerError, clean_passenger, clean_phone,
)
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

def _bad_request(message, **extra):
    return Response({'error': message, **extra}, status=status.HTTP_400_BAD_REQUEST)


class InvalidSeatId(ValueError):
    """A seat id in the request is not a number."""


def _parse_booking_request(data):
    """Read {"contact_phone": "...", "passengers": [{"seat": id, "name", "age", "gender"}, ...]}.
    Returns (seat_ids, passengers_by_seat_id, phone). Raises InvalidSeatId or PassengerError."""
    raw = data.get('passengers') if hasattr(data, 'get') else None
    if raw is None:
        raise PassengerError('Passenger details are required: send a name, age and gender for every seat.')
    if not isinstance(raw, (list, tuple)):
        raise PassengerError('passengers must be a list.')

    seat_ids, details = [], {}
    for position, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise PassengerError(f'Passenger {position}: details are missing.')
        seat = item.get('seat')
        if isinstance(seat, bool) or seat in (None, ''):
            raise InvalidSeatId('not a seat id')
        try:
            seat_id = int(seat)
        except (TypeError, ValueError):
            raise InvalidSeatId('not a seat id')
        seat_ids.append(seat_id)
        details[seat_id] = item          # validated later, once we know the request is otherwise sane

    return seat_ids, details, data.get('contact_phone')


class BookingView(APIView):
    """POST /api/booking/ - book one or several seats of ONE trip, with the passenger for each seat:
        {"contact_phone": "9876543210",
         "passengers": [{"seat": 12, "name": "Ravi Kumar", "age": 34, "gender": "M"}, ...]}
    All or nothing: if any seat cannot be booked, none are."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            seat_ids, raw_details, raw_phone = _parse_booking_request(request.data)
        except InvalidSeatId:
            return Response({'error': 'Invalid Seat ID'}, status=status.HTTP_404_NOT_FOUND)
        except PassengerError as exc:
            return _bad_request(str(exc))

        if not seat_ids:
            return _bad_request('Please choose at least one seat.')
        if len(set(seat_ids)) != len(seat_ids):
            return _bad_request('The same seat was chosen more than once.')
        if len(seat_ids) > MAX_SEATS_PER_BOOKING:
            return _bad_request(f'You can book at most {MAX_SEATS_PER_BOOKING} seats at a time.')

        # Check the passenger details before touching the database.
        try:
            passengers = {sid: clean_passenger(raw_details[sid], i)
                          for i, sid in enumerate(seat_ids, start=1)}
            phone = clean_phone(raw_phone)
        except PassengerError as exc:
            return _bad_request(str(exc))

        with transaction.atomic():
            # Lock this person's row first, so two requests from the same person run one after the
            # other and cannot both slip under the per-person seat limit.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)

            # Lock the seats in a fixed order (by id): people choosing overlapping seats at the same
            # moment queue up instead of deadlocking, and a seat is never booked twice.
            seats = list(
                Seat.objects.select_for_update(of=('self',))
                .select_related('trip__bus')
                .filter(id__in=seat_ids)
                .order_by('id')
            )
            if len(seats) != len(seat_ids):
                return Response({'error': 'Invalid Seat ID'}, status=status.HTTP_404_NOT_FOUND)

            trips = {seat.trip_id for seat in seats}
            if len(trips) != 1:
                return _bad_request('All seats in one booking must be on the same bus and date.')
            trip = seats[0].trip

            # Covers past dates, a bus that left earlier today, and the last few minutes
            # before departure (booking stops BOOKING_CUTOFF_MINUTES before the bus leaves).
            if has_departed(trip):
                return _bad_request('This bus has already departed, so it can no longer be booked')
            if is_booking_closed(trip):
                return _bad_request(
                    f'Booking for this bus has closed. Tickets can be booked until '
                    f'{BOOKING_CUTOFF_MINUTES} minutes before departure.')

            taken = [seat for seat in seats if seat.is_booked]
            if taken:
                names = ', '.join(seat.seat_number for seat in taken)
                message = (f'Seat {names} is already booked.' if len(taken) == 1
                           else f'Seats {names} are no longer available. Nothing was booked.')
                return _bad_request(message, unavailable_seats=[seat.id for seat in taken])

            held = Booking.objects.filter(
                user=request.user, trip=trip, status=Booking.STATUS_CONFIRMED).count()
            if held + len(seats) > MAX_SEATS_PER_USER_PER_TRIP:
                return _bad_request(
                    f'You can book at most {MAX_SEATS_PER_USER_PER_TRIP} seats on one bus and date. '
                    f'You already have {held} on this trip.')

            bookings = []
            for seat in seats:
                seat.is_booked = True
                seat.save(update_fields=['is_booked'])
                who = passengers[seat.id]
                bookings.append(Booking.objects.create(
                    user=request.user, trip=trip, seat=seat, contact_phone=phone,
                    passenger_name=who['name'], passenger_age=who['age'], passenger_gender=who['gender']))

        return Response(BookingSerializer(bookings, many=True).data, status=status.HTTP_201_CREATED)


class UserBookingView(APIView):
    permission_classes =[IsAuthenticated]

    def get(self,request,user_id):
        if request.user.id != user_id:
            return Response({'error':'Forbidden'},status=status.HTTP_403_FORBIDDEN)
        
        bookings = Booking.objects.filter(user_id=user_id).select_related('trip__bus', 'seat').order_by('-booking_time', '-id')
        serializer =BookingSerializer(bookings,many=True)
        return Response(serializer.data)


class CancelBookingView(APIView):
    """POST /api/booking/<id>/cancel/ - cancel your own ticket and free the seat."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            try:
                # Lock the booking row, then its seat, so a double click or a simultaneous
                # new booking of the same seat cannot leave the seat in the wrong state.
                booking = (
                    Booking.objects.select_for_update(of=('self',))
                    .select_related('trip__bus')
                    .get(pk=pk)
                )
            except Booking.DoesNotExist:
                return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

            if booking.user_id != request.user.id:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            if booking.status == Booking.STATUS_CANCELLED:
                return Response({'error': 'This booking is already cancelled'}, status=status.HTTP_400_BAD_REQUEST)
            if has_departed(booking.trip):
                return Response({'error': 'This bus has already departed, so the ticket cannot be cancelled'},
                                status=status.HTTP_400_BAD_REQUEST)

            seat = Seat.objects.select_for_update().get(pk=booking.seat_id)
            seat.is_booked = False
            seat.save()

            booking.status = Booking.STATUS_CANCELLED
            booking.cancelled_at = timezone.now()
            booking.save()

        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)
