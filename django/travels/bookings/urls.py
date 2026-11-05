from django.urls import path
from .views import (
    RegisterView, LoginView, BusListCreateView, UserBookingView, BookingView,
    BusDetailView, TripListView, TripDetailView,
)

urlpatterns = [
    path('buses/',BusListCreateView.as_view(),name = 'buslist'),
    path('buses/<int:pk>/',BusDetailView.as_view(),name = 'bus-detail'),
    path('trips/',TripListView.as_view(),name = 'trip-list'),
    path('trips/<int:pk>/',TripDetailView.as_view(),name = 'trip-detail'),
    path('register/',RegisterView.as_view(),name = 'register'),
    path('login/',LoginView.as_view(),name = 'login'),
    path('user/<int:user_id>/bookings/',UserBookingView.as_view(),name = 'user-bookings'),
    path('booking/',BookingView.as_view(),name = 'bookings'),
]

