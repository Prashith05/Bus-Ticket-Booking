from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from .models import Bus, Trip, Seat, Booking
from .services import BOOKING_WINDOW_DAYS, MAX_SEATS_PER_BOOKING, MAX_SEATS_PER_USER_PER_TRIP


PHONE = '9876543210'


def passenger(seat_id, **over):
    """One passenger entry of a booking request (valid unless overridden)."""
    return {'seat': seat_id, 'name': 'Ravi Kumar', 'age': 34, 'gender': 'M', **over}


def booking_body(seat_ids, **over):
    """A valid booking request body for these seat ids."""
    return {'contact_phone': PHONE, 'passengers': [passenger(i) for i in seat_ids], **over}


class BaseApiTest(APITestCase):
    def at(self, hour, minute=0):
        """A fixed UTC moment on the trip's day (the bus departs 08:00 IST = 02:30 UTC)."""
        return datetime(self.today.year, self.today.month, self.today.day, hour, minute, tzinfo=dt_timezone.utc)

    def setUp(self):
        self.today = timezone.localdate()
        # Freeze the clock at 06:30 IST on the trip's day. Booking and cancelling now depend on
        # the time of day, so without this the tests would pass or fail depending on when they run.
        patcher = patch('django.utils.timezone.now', return_value=self.at(1, 0))
        self.mock_now = patcher.start()
        self.addCleanup(patcher.stop)
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
        return self.client.post('/api/booking/', booking_body([seat.id]), format='json')


class BookingApiTests(BaseApiTest):
    def test_booking_success_returns_readable_fields(self):
        self.auth(self.user)
        res = self.book(self.seat)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data), 1)  # the booking API always answers with a list
        self.assertEqual(res.data[0]['bus_name'], 'Express')
        self.assertEqual(res.data[0]['seat_number'], self.seat.seat_number)
        self.assertEqual(str(res.data[0]['travel_date']), str(self.today))
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
        res = self.client.post('/api/booking/', booking_body([99999]), format='json')
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


class CancelBookingTests(BaseApiTest):
    def make_booking(self, user=None, seat=None):
        self.auth(user or self.user)
        res = self.book(seat or self.seat)
        self.assertEqual(res.status_code, 201)
        return res.data[0]['id']

    def cancel(self, booking_id):
        return self.client.post(f'/api/booking/{booking_id}/cancel/', {}, format='json')

    def test_cancel_frees_the_seat_and_keeps_history(self):
        booking_id = self.make_booking()
        res = self.cancel(booking_id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'cancelled')
        self.assertIsNotNone(res.data['cancelled_at'])
        self.assertFalse(res.data['can_cancel'])
        self.seat.refresh_from_db()
        self.assertFalse(self.seat.is_booked)
        self.assertEqual(Booking.objects.count(), 1)  # kept, not deleted

    def test_available_seats_goes_back_up(self):
        booking_id = self.make_booking()
        self.assertEqual(self.client.get(f'/api/trips/?date={self.today}').data[0]['available_seats'], 3)
        self.cancel(booking_id)
        self.assertEqual(self.client.get(f'/api/trips/?date={self.today}').data[0]['available_seats'], 4)

    def test_cancelled_seat_can_be_booked_again_by_someone_else(self):
        first = self.make_booking(self.user)
        self.cancel(first)
        self.auth(self.other)
        res = self.book(self.seat)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(Booking.objects.filter(status='confirmed').count(), 1)

    def test_cancelling_twice_does_not_free_a_seat_someone_else_rebooked(self):
        first = self.make_booking(self.user)
        self.cancel(first)
        self.auth(self.other)
        self.book(self.seat)  # bob now holds the seat
        self.auth(self.user)
        res = self.cancel(first)  # alice tries again
        self.assertEqual(res.status_code, 400)
        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked)

    def test_cannot_cancel_someone_elses_booking(self):
        booking_id = self.make_booking(self.user)
        self.auth(self.other)
        self.assertEqual(self.cancel(booking_id).status_code, 403)
        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked)
        self.assertEqual(Booking.objects.get(id=booking_id).status, 'confirmed')

    def test_cancel_requires_login_and_valid_id(self):
        booking_id = self.make_booking()
        self.client.credentials()  # log out
        self.assertEqual(self.cancel(booking_id).status_code, 401)
        self.auth(self.user)
        self.assertEqual(self.cancel(99999).status_code, 404)

    def test_can_cancel_before_departure_but_not_after(self):
        booking_id = self.make_booking()
        # 06:30 IST: the bus has not left yet
        listed = self.client.get(f'/api/user/{self.user.id}/bookings/').data[0]
        self.assertTrue(listed['can_cancel'])

        # 08:30 IST: the bus has left, so cancelling is refused and the seat stays booked
        self.mock_now.return_value = self.at(3, 0)
        listed = self.client.get(f'/api/user/{self.user.id}/bookings/').data[0]
        self.assertFalse(listed['can_cancel'])
        self.assertEqual(self.cancel(booking_id).status_code, 400)
        self.seat.refresh_from_db()
        self.assertTrue(self.seat.is_booked)

        # back to 06:30 IST: it works
        self.mock_now.return_value = self.at(1, 0)
        self.assertEqual(self.cancel(booking_id).status_code, 200)

    def test_bookings_list_shows_cancelled_ones_newest_first(self):
        first = self.make_booking(self.user, self.seat)
        second_seat = self.trip.seats.order_by('id')[1]
        self.make_booking(self.user, second_seat)
        self.cancel(first)
        res = self.client.get(f'/api/user/{self.user.id}/bookings/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b['status'] for b in res.data], ['confirmed', 'cancelled'])


class DepartedBusTests(BaseApiTest):
    """The bus leaves at 08:00 IST (02:30 UTC); booking stops 15 minutes earlier, at 07:45 IST."""

    def test_cannot_book_after_the_bus_has_left_today(self):
        self.mock_now.return_value = self.at(3, 0)  # 08:30 IST
        self.auth(self.user)
        res = self.book(self.seat)
        self.assertEqual(res.status_code, 400)
        self.assertIn('departed', res.data['error'])
        self.seat.refresh_from_db()
        self.assertFalse(self.seat.is_booked)
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_stops_15_minutes_before_departure(self):
        self.auth(self.user)
        self.mock_now.return_value = self.at(2, 14)  # 07:44 IST, one minute before the cutoff
        self.assertEqual(self.book(self.seat).status_code, 201)

        self.mock_now.return_value = self.at(2, 15)  # 07:45 IST, booking closes
        other_seat = self.trip.seats.order_by('id')[1]
        res = self.book(other_seat)
        self.assertEqual(res.status_code, 400)
        self.assertIn('closed', res.data['error'])
        self.assertIn('15 minutes', res.data['error'])
        other_seat.refresh_from_db()
        self.assertFalse(other_seat.is_booked)

    def test_flags_before_the_cutoff_in_the_last_15_minutes_and_after_departure(self):
        def flags():
            listed = self.client.get(f'/api/trips/?date={self.today}').data[0]
            detail = self.client.get(f'/api/trips/{self.trip.id}/').data
            return (listed['booking_closed'], listed['departed'], detail['booking_closed'], detail['departed'])

        self.assertEqual(flags(), (False, False, False, False))      # 06:30 IST
        self.mock_now.return_value = self.at(2, 20)                  # 07:50 IST
        self.assertEqual(flags(), (True, False, True, False))        # closed, but not left yet
        self.mock_now.return_value = self.at(3, 0)                   # 08:30 IST
        self.assertEqual(flags(), (True, True, True, True))

    def test_seat_list_is_only_sent_while_the_trip_is_open(self):
        detail = self.client.get(f'/api/trips/{self.trip.id}/').data
        self.assertEqual(len(detail['seats']), 4)
        self.assertEqual(detail['booking_cutoff_minutes'], 15)

        for moment in (self.at(2, 20), self.at(3, 0)):               # last 15 minutes, and after departure
            self.mock_now.return_value = moment
            detail = self.client.get(f'/api/trips/{self.trip.id}/').data
            self.assertEqual(detail['seats'], [])

    def test_a_bus_on_a_later_date_is_never_closed_or_departed(self):
        self.mock_now.return_value = self.at(20, 0)  # late in the evening, today
        tomorrow = self.today + timedelta(days=1)
        listed = self.client.get(f'/api/trips/?date={tomorrow}').data[0]
        self.assertFalse(listed['departed'])
        self.assertFalse(listed['booking_closed'])
        self.auth(self.user)
        tomorrow_seat = Trip.objects.get(date=tomorrow, bus=self.bus).seats.order_by('id').first()
        self.assertEqual(self.book(tomorrow_seat).status_code, 201)


class MultiSeatBookingTests(BaseApiTest):
    def setUp(self):
        super().setUp()
        # A bigger bus (10 seats, leaves at 09:00 IST) so the 6-seat limits can be tested.
        big = Bus.objects.create(
            bus_name='Big Bus', number='KA09', origin='Chennai', destination='Bangalore',
            features='AC', start_time='09:00', reach_time='15:00', no_of_seats=10, price='200.00',
        )
        self.big_trip = Trip.objects.create(bus=big, date=self.today)
        self.big_seats = list(self.big_trip.seats.order_by('id'))

    def book_many(self, seats):
        return self.client.post('/api/booking/', booking_body([s.id for s in seats]), format='json')

    def confirmed(self, user):
        return Booking.objects.filter(user=user, status='confirmed').count()

    def test_limits_are_six(self):
        self.assertEqual(MAX_SEATS_PER_BOOKING, 6)
        self.assertEqual(MAX_SEATS_PER_USER_PER_TRIP, 6)

    def test_books_several_seats_in_one_request(self):
        self.auth(self.user)
        res = self.book_many(self.big_seats[:3])
        self.assertEqual(res.status_code, 201)
        self.assertEqual([b['seat_number'] for b in res.data], ['S1', 'S2', 'S3'])
        self.assertTrue(all(b['bus_name'] == 'Big Bus' and b['status'] == 'confirmed' for b in res.data))
        self.assertEqual(Booking.objects.count(), 3)
        self.assertEqual(Seat.objects.filter(trip=self.big_trip, is_booked=True).count(), 3)

    def test_all_or_nothing_when_one_seat_is_taken(self):
        self.auth(self.other)
        self.assertEqual(self.book_many([self.big_seats[1]]).status_code, 201)  # bob takes S2
        self.auth(self.user)
        res = self.book_many(self.big_seats[:3])  # alice asks for S1, S2, S3
        self.assertEqual(res.status_code, 400)
        self.assertIn('S2', res.data['error'])
        self.assertEqual(res.data['unavailable_seats'], [self.big_seats[1].id])
        self.assertEqual(self.confirmed(self.user), 0)  # S1 and S3 were NOT booked
        self.assertFalse(Seat.objects.get(id=self.big_seats[0].id).is_booked)
        self.assertFalse(Seat.objects.get(id=self.big_seats[2].id).is_booked)

    def test_more_than_six_seats_in_one_booking_is_refused(self):
        self.auth(self.user)
        res = self.book_many(self.big_seats[:MAX_SEATS_PER_BOOKING + 1])
        self.assertEqual(res.status_code, 400)
        self.assertIn('6', res.data['error'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_exactly_six_seats_is_allowed(self):
        self.auth(self.user)
        self.assertEqual(self.book_many(self.big_seats[:6]).status_code, 201)
        self.assertEqual(self.confirmed(self.user), 6)

    def test_per_person_limit_counts_all_bookings_on_the_trip(self):
        self.auth(self.user)
        self.assertEqual(self.book_many(self.big_seats[:4]).status_code, 201)
        res = self.book_many(self.big_seats[4:7])  # 4 + 3 = 7 > 6
        self.assertEqual(res.status_code, 400)
        self.assertIn('already have 4', res.data['error'])
        self.assertEqual(self.confirmed(self.user), 4)
        self.assertEqual(self.book_many(self.big_seats[4:6]).status_code, 201)  # 4 + 2 = 6 is fine
        self.assertEqual(self.book_many(self.big_seats[6:7]).status_code, 400)  # a 7th is not
        # someone else can still book the remaining seats
        self.auth(self.other)
        self.assertEqual(self.book_many(self.big_seats[6:9]).status_code, 201)

    def test_per_person_limit_is_per_trip(self):
        tomorrow = Trip.objects.create(bus=self.big_trip.bus, date=self.today + timedelta(days=1))
        self.auth(self.user)
        self.assertEqual(self.book_many(self.big_seats[:6]).status_code, 201)
        self.assertEqual(self.book_many(list(tomorrow.seats.order_by('id')[:6])).status_code, 201)

    def test_cancelled_seats_do_not_count_toward_the_limit(self):
        self.auth(self.user)
        made = self.book_many(self.big_seats[:6]).data
        self.assertEqual(self.book_many(self.big_seats[6:7]).status_code, 400)
        self.assertEqual(self.client.post(f"/api/booking/{made[0]['id']}/cancel/", {}, format='json').status_code, 200)
        self.assertEqual(self.book_many(self.big_seats[6:7]).status_code, 201)
        self.assertEqual(self.confirmed(self.user), 6)

    def test_cancel_one_of_several_seats_and_it_can_be_booked_again(self):
        self.auth(self.user)
        made = self.book_many(self.big_seats[:2]).data  # S1 and S2
        self.client.post(f"/api/booking/{made[0]['id']}/cancel/", {}, format='json')  # cancel S1 only
        self.assertFalse(Seat.objects.get(id=self.big_seats[0].id).is_booked)
        self.assertTrue(Seat.objects.get(id=self.big_seats[1].id).is_booked)
        self.assertEqual(Booking.objects.get(id=made[1]['id']).status, 'confirmed')
        self.auth(self.other)
        self.assertEqual(self.book_many([self.big_seats[0]]).status_code, 201)

    def test_seats_from_different_trips_are_refused(self):
        self.auth(self.user)
        res = self.book_many([self.big_seats[0], self.seat])  # a seat of the big bus and one of the small bus
        self.assertEqual(res.status_code, 400)
        self.assertIn('same bus and date', res.data['error'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_duplicate_and_empty_requests_are_refused(self):
        self.auth(self.user)
        dup = self.client.post('/api/booking/', booking_body([self.big_seats[0].id, self.big_seats[0].id]), format='json')
        self.assertEqual(dup.status_code, 400)
        for body in ({'contact_phone': PHONE, 'passengers': []}, {}):
            self.assertEqual(self.client.post('/api/booking/', body, format='json').status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)

    def test_unknown_or_invalid_seat_ids_book_nothing(self):
        self.auth(self.user)
        for seats in ([self.big_seats[0].id, 99999], ['abc'], [None], [True]):
            body = {'contact_phone': PHONE, 'passengers': [passenger(sid) for sid in seats]}
            res = self.client.post('/api/booking/', body, format='json')
            self.assertEqual(res.status_code, 404, seats)
        res = self.client.post('/api/booking/', {'contact_phone': PHONE, 'passengers': 'S1'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertFalse(Seat.objects.get(id=self.big_seats[0].id).is_booked)

    def test_old_request_without_passenger_details_is_refused(self):
        self.auth(self.user)
        for body in ({'seat': self.big_seats[0].id}, {'seats': [self.big_seats[0].id]}):
            res = self.client.post('/api/booking/', body, format='json')
            self.assertEqual(res.status_code, 400)
            self.assertIn('Passenger details are required', res.data['error'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_several_seats_on_a_closed_trip_are_refused(self):
        self.mock_now.return_value = self.at(3, 15)  # 08:45 IST: Big Bus leaves 09:00, booking closed at 08:45
        self.auth(self.user)
        res = self.book_many(self.big_seats[:2])
        self.assertEqual(res.status_code, 400)
        self.assertIn('closed', res.data['error'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_requires_login(self):
        res = self.book_many(self.big_seats[:2])
        self.assertEqual(res.status_code, 401)



class PassengerDetailTests(BaseApiTest):
    def setUp(self):
        super().setUp()
        self.big = Trip.objects.create(
            bus=Bus.objects.create(bus_name='Big Bus', number='KA09', origin='Chennai', destination='Bangalore',
                                   features='AC', start_time='09:00', reach_time='15:00', no_of_seats=10,
                                   price='200.00'),
            date=self.today)
        self.s = list(self.big.seats.order_by('id'))
        self.auth(self.user)

    def post(self, passengers, phone=PHONE):
        return self.client.post('/api/booking/', {'contact_phone': phone, 'passengers': passengers}, format='json')

    def assert_refused(self, res, text):
        self.assertEqual(res.status_code, 400, res.data)
        self.assertIn(text, res.data['error'])
        self.assertEqual(Booking.objects.count(), 0)
        self.assertFalse(Seat.objects.filter(is_booked=True).exists())

    def test_each_seat_stores_its_own_passenger(self):
        res = self.post([
            passenger(self.s[0].id, name='Ravi Kumar', age=34, gender='M'),
            passenger(self.s[1].id, name='Asha  Devi ', age=31, gender='f'),
            passenger(self.s[2].id, name='Kid', age=7, gender='O'),
        ])
        self.assertEqual(res.status_code, 201, res.data)
        got = {b['seat_number']: b for b in res.data}
        self.assertEqual(got[self.s[1].seat_number]['passenger_name'], 'Asha Devi')   # spaces tidied
        self.assertEqual(got[self.s[1].seat_number]['passenger_gender'], 'F')         # upper-cased
        self.assertEqual(got[self.s[2].seat_number]['passenger_age'], 7)
        self.assertTrue(all(b['contact_phone'] == PHONE for b in res.data))
        row = Booking.objects.get(seat=self.s[0])
        self.assertEqual((row.passenger_name, row.passenger_age, row.passenger_gender, row.contact_phone),
                         ('Ravi Kumar', 34, 'M', PHONE))

    def test_details_show_up_in_my_bookings(self):
        self.post([passenger(self.s[0].id, name='Meena')])
        res = self.client.get(f'/api/user/{self.user.id}/bookings/')
        self.assertEqual(res.data[0]['passenger_name'], 'Meena')
        self.assertEqual(res.data[0]['contact_phone'], PHONE)

    def test_missing_or_bad_name(self):
        for bad in ('', '   ', 'A', None, '1234', '<b>x</b>', 'x' * 101):
            self.assert_refused(self.post([passenger(self.s[0].id, name=bad)]), 'Passenger 1')

    def test_missing_or_bad_age(self):
        for bad in (None, '', 0, -3, 121, 'abc', 12.5, True):
            self.assert_refused(self.post([passenger(self.s[0].id, age=bad)]), 'age')
        res = self.post([passenger(self.s[0].id, age='34')])      # a number sent as text is fine
        self.assertEqual(res.status_code, 201)

    def test_missing_or_bad_gender(self):
        for bad in (None, '', 'X', 'male'):
            self.assert_refused(self.post([passenger(self.s[0].id, gender=bad)]), 'gender')

    def test_error_names_the_passenger_with_the_problem(self):
        res = self.post([passenger(self.s[0].id), passenger(self.s[1].id, age=0)])
        self.assert_refused(res, 'Passenger 2')

    def test_phone_is_required_and_validated(self):
        for bad in (None, '', '12345', '5876543210', 'abcdefghij', '98765432101234'):
            self.assert_refused(self.post([passenger(self.s[0].id)], phone=bad), 'mobile number')

    def test_phone_formats_are_normalised(self):
        for i, ok in enumerate(('+91 98765 43210', '098765-43210', '919876543210', '9876543210')):
            res = self.post([passenger(self.s[i].id)], phone=ok)
            self.assertEqual(res.status_code, 201, ok)
            self.assertEqual(res.data[0]['contact_phone'], '9876543210')

    def test_bad_details_for_one_seat_book_none_of_them(self):
        self.assert_refused(self.post([passenger(self.s[0].id), passenger(self.s[1].id, name='')]), 'Passenger 2')

    def test_non_object_passenger_entries(self):
        for bad in ([None], ['S1'], [5]):
            self.assert_refused(self.post(bad), 'Passenger 1')

    def test_cancelling_keeps_the_passenger_details(self):
        booking_id = self.post([passenger(self.s[0].id, name='Meena')]).data[0]['id']
        res = self.client.post(f'/api/booking/{booking_id}/cancel/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['passenger_name'], 'Meena')

    def test_rebooking_a_cancelled_seat_stores_the_new_passenger(self):
        first = self.post([passenger(self.s[0].id, name='Meena')]).data[0]['id']
        self.client.post(f'/api/booking/{first}/cancel/')
        self.auth(self.other)
        res = self.post([passenger(self.s[0].id, name='Suresh', age=50)])
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Booking.objects.get(pk=first).passenger_name, 'Meena')       # history unchanged
        self.assertEqual(Booking.objects.get(seat=self.s[0], status='confirmed').passenger_name, 'Suresh')

    def test_old_bookings_without_details_still_load(self):
        old = Booking.objects.create(user=self.user, trip=self.big, seat=self.s[0])   # as made before this feature
        self.s[0].is_booked = True; self.s[0].save()
        res = self.client.get(f'/api/user/{self.user.id}/bookings/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data[0]['passenger_name'], res.data[0]['passenger_age'],
                          res.data[0]['passenger_gender'], res.data[0]['contact_phone']), ('', None, '', ''))
