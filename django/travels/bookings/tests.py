from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from .models import Bus, Trip, Seat, Booking
from .services import BOOKING_WINDOW_DAYS


class BaseApiTest(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user = User.objects.create_user('alice', 'a@example.com', 'pass12345')
        self.other = User.objects.create_user('bob', 'b@example.com', 'pass12345')
        self.admin = User.objects.create_user('admin', 'admin@example.com', 'pass12345', is_staff=True)
        self.bus = Bus.objects.create(
            bus_name='Express', number='KA01', origin='Chennai', destination='Bangalore',
            features='AC', start_time='08:00', reach_time='12:00',
            no_of_seats=4, price='100.00',
        )
        # The post_save signal creates the seats of a trip automatically.
        self.trip = Trip.objects.create(bus=self.bus, date=self.today)
        self.seat = self.trip.seats.order_by('id').first()

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def book(self, seat):
        return self.client.post('/api/booking/', {'seat': seat.id}, format='json')


class BookingApiTests(BaseApiTest):
    def test_booking_success_returns_readable_fields(self):
        self.auth(self.user)
        res = self.book(self.seat)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['bus_name'], 'Express')
        self.assertEqual(res.data['seat_number'], self.seat.seat_number)
        self.assertEqual(str(res.data['travel_date']), str(self.today))
        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked)

    def test_double_booking_is_rejected(self):
        self.auth(self.user)
        self.book(self.seat)
        self.auth(self.other)
        res = self.book(self.seat)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Booking.objects.count(), 1)

    def test_invalid_seat_returns_404(self):
        self.auth(self.user)
        res = self.client.post('/api/booking/', {'seat': 99999}, format='json')
        self.assertEqual(res.status_code, 404)

    def test_booking_requires_login(self):
        res = self.book(self.seat)
        self.assertEqual(res.status_code, 401)

    def test_cannot_book_a_trip_that_already_happened(self):
        old_trip = Trip.objects.create(bus=self.bus, date=self.today - timedelta(days=1))
        self.auth(self.user)
        res = self.book(old_trip.seats.first())
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)

    def test_same_seat_number_on_another_date_is_independent(self):
        tomorrow = Trip.objects.create(bus=self.bus, date=self.today + timedelta(days=1))
        tomorrow_s1 = tomorrow.seats.get(seat_number=self.seat.seat_number)
        self.auth(self.user)
        self.assertEqual(self.book(self.seat).status_code, 201)
        # the same seat number tomorrow is still free, and another user can take it
        self.auth(self.other)
        self.assertEqual(self.book(tomorrow_s1).status_code, 201)

    def test_user_cannot_view_other_users_bookings(self):
        self.auth(self.user)
        res = self.client.get(f'/api/user/{self.other.id}/bookings/')
        self.assertEqual(res.status_code, 403)

    def test_user_can_view_own_bookings_with_travel_date(self):
        self.auth(self.user)
        self.book(self.seat)
        res = self.client.get(f'/api/user/{self.user.id}/bookings/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(str(res.data[0]['travel_date']), str(self.today))


class TripApiTests(BaseApiTest):
    def test_new_trip_gets_one_seat_per_bus_seat(self):
        self.assertEqual(self.trip.seats.count(), 4)
        self.assertEqual(Seat.objects.count(), 4)

    def test_trip_list_for_a_date(self):
        res = self.client.get(f'/api/trips/?date={self.today}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], self.trip.id)
        self.assertEqual(res.data[0]['bus_name'], 'Express')
        self.assertEqual(res.data[0]['available_seats'], 4)

    def test_date_defaults_to_today(self):
        res = self.client.get('/api/trips/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_buses_run_every_day_trips_are_created_when_searched(self):
        tomorrow = self.today + timedelta(days=1)
        self.assertFalse(Trip.objects.filter(date=tomorrow).exists())
        res = self.client.get(f'/api/trips/?date={tomorrow}')
        self.assertEqual(len(res.data), 1)
        trip = Trip.objects.get(date=tomorrow)
        self.assertEqual(trip.seats.count(), 4)
        # searching again must not duplicate it
        self.client.get(f'/api/trips/?date={tomorrow}')
        self.assertEqual(Trip.objects.filter(date=tomorrow).count(), 1)

    def test_past_dates_and_dates_beyond_the_window_have_no_buses(self):
        yesterday = self.today - timedelta(days=1)
        too_far = self.today + timedelta(days=BOOKING_WINDOW_DAYS + 1)
        for d in (yesterday, too_far):
            res = self.client.get(f'/api/trips/?date={d}')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data, [])
        self.assertFalse(Trip.objects.filter(date=too_far).exists())

    def test_invalid_date_returns_400(self):
        res = self.client.get('/api/trips/?date=not-a-date')
        self.assertEqual(res.status_code, 400)

    def test_origin_and_destination_filters(self):
        Bus.objects.create(
            bus_name='Night', number='KA02', origin='Mumbai', destination='Pune',
            features='Sleeper', start_time='21:00', reach_time='01:00',
            no_of_seats=2, price='200.00',
        )
        res = self.client.get(f'/api/trips/?date={self.today}&origin=chen')
        self.assertEqual([t['bus_name'] for t in res.data], ['Express'])
        res = self.client.get(f'/api/trips/?date={self.today}&destination=pune')
        self.assertEqual([t['bus_name'] for t in res.data], ['Night'])
        res = self.client.get(f'/api/trips/?date={self.today}')
        self.assertEqual(len(res.data), 2)

    def test_available_seats_goes_down_after_booking(self):
        self.auth(self.user)
        self.book(self.seat)
        res = self.client.get(f'/api/trips/?date={self.today}')
        self.assertEqual(res.data[0]['available_seats'], 3)

    def test_trip_detail_seats_keep_their_order_after_booking(self):
        self.auth(self.user)
        self.book(self.seat)  # book the first seat; it must not move to the end
        res = self.client.get(f'/api/trips/{self.trip.id}/')
        self.assertEqual(res.status_code, 200)
        ids = [s['id'] for s in res.data['seats']]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(res.data['seats'][0]['seat_number'], 'S1')
        self.assertTrue(res.data['seats'][0]['is_booked'])

    def test_generate_trips_command(self):
        call_command('generate_trips', days=3, verbosity=0)
        self.assertEqual(Trip.objects.filter(bus=self.bus).count(), 3)
        call_command('generate_trips', days=3, verbosity=0)  # running twice is safe
        self.assertEqual(Trip.objects.filter(bus=self.bus).count(), 3)


class BusPermissionTests(BaseApiTest):
    def test_anyone_can_list_and_view_buses(self):
        self.assertEqual(self.client.get('/api/buses/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/buses/{self.bus.id}/').status_code, 200)

    def test_only_admin_can_modify_buses(self):
        payload = {
            'bus_name': 'New', 'number': 'KA03', 'origin': 'A', 'destination': 'C',
            'features': 'AC', 'start_time': '09:00', 'reach_time': '13:00',
            'no_of_seats': 2, 'price': '80.00',
        }
        # anonymous
        self.assertEqual(self.client.post('/api/buses/', payload, format='json').status_code, 401)
        # normal user
        self.auth(self.user)
        self.assertEqual(self.client.post('/api/buses/', payload, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/buses/{self.bus.id}/').status_code, 403)
        # admin
        self.auth(self.admin)
        self.assertEqual(self.client.post('/api/buses/', payload, format='json').status_code, 201)
