from django.db import transaction
from django.shortcuts import render

# authicate, permission, token, status, response, generics, api views
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS, BasePermission
from rest_framework.authtoken.models import Token
from rest_framework import status, generics
from rest_framework.views import APIView
from .serializers import UserRegisterSerializer,BusSerializer,BookingSerializer,SeatSerializer
from rest_framework.response import Response
from .models import Bus,Seat,Booking
from django.db.models import Prefetch


 
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
    # queryset = Bus.objects.all() # caused the problem by ordering the seats at the last after booking the seat(alignment changing problem)
    queryset = Bus.objects.prefetch_related(
        Prefetch('seats', queryset=Seat.objects.order_by('id'))
    )
    serializer_class = BusSerializer
    permission_classes = [IsAdminOrReadOnly]

class BusDetailView(generics.RetrieveUpdateDestroyAPIView):
    # queryset = Bus.objects.all()
    queryset = Bus.objects.prefetch_related(
        Prefetch('seats', queryset=Seat.objects.order_by('id'))
    )
    serializer_class = BusSerializer
    permission_classes = [IsAdminOrReadOnly]

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

                seat.is_booked = True
                seat.save()

                booking = Booking.objects.create(
                    user=request.user,
                    bus=seat.bus,
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
        
        bookings = Booking.objects.filter(user_id=user_id)
        serializer =BookingSerializer(bookings,many=True)
        return Response(serializer.data)
