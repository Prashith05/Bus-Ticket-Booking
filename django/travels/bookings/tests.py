from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from .models import Bus, Seat, Booking


class BookingApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', 'a@example.com', 'pass12345')
        self.other = User.objects.create_user('bob', 'b@example.com', 'pass12345')
        self.admin = User.objects.create_user('admin', 'admin@example.com', 'pass12345', is_staff=True)
        # The post_save signal creates the seats automatically.
        self.bus = Bus.objects.create(
            bus_name='Express', number='KA01', origin='A', destination='B',
            features='AC', start_time='08:00', reach_time='12:00',
            no_of_seats=4, price='100.00',
        )
        self.seat = self.bus.seats.first()

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_booking_success_returns_readable_fields(self):
        self.auth(self.user)
        res = self.client.post('/api/booking/', {'seat': self.seat.id}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['bus_name'], 'Express')
        self.assertEqual(res.data['seat_number'], self.seat.seat_number)
        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked)

    def test_double_booking_is_rejected(self):
        self.auth(self.user)
        self.client.post('/api/booking/', {'seat': self.seat.id}, format='json')
        self.auth(self.other)
        res = self.client.post('/api/booking/', {'seat': self.seat.id}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Booking.objects.count(), 1)

    def test_invalid_seat_returns_404(self):
        self.auth(self.user)
        res = self.client.post('/api/booking/', {'seat': 99999}, format='json')
        self.assertEqual(res.status_code, 404)

    def test_booking_requires_login(self):
        res = self.client.post('/api/booking/', {'seat': self.seat.id}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_user_cannot_view_other_users_bookings(self):
        self.auth(self.user)
        res = self.client.get(f'/api/user/{self.other.id}/bookings/')
        self.assertEqual(res.status_code, 403)

    def test_user_can_view_own_bookings(self):
        self.auth(self.user)
        self.client.post('/api/booking/', {'seat': self.seat.id}, format='json')
        res = self.client.get(f'/api/user/{self.user.id}/bookings/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_anyone_can_list_buses_and_see_seats(self):
        res = self.client.get('/api/buses/')
        self.assertEqual(res.status_code, 200)
        res = self.client.get(f'/api/buses/{self.bus.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['seats']), 4)

    def test_only_admin_can_modify_buses(self):
        payload = {
            'bus_name': 'New', 'number': 'KA02', 'origin': 'A', 'destination': 'C',
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
