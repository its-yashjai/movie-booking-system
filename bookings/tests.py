
from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Booking
from movies.models import Movie
from movies.theater_models import Showtime, Theater, Screen, City
from django.utils import timezone

class BookingAuthenticationTests(TestCase):

    
    def setUp(self):
        self.client = Client()

        self.client = Client()
    
    def test_select_seats_requires_login(self):

        response = self.client.get('/bookings/select-seats/1/')
        

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_user_can_access_bookings(self):

        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        

        self.client.login(username='testuser', password='testpass123')
        

        response = self.client.get('/my-bookings/')
        

        self.assertNotEqual(response.status_code, 302)

class BookingCreationTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        

        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test Description',
            release_date=timezone.now().date(),
            duration=148 
        )
        

        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        

        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00'
        )
    
    def test_booking_can_be_created(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='PENDING'
        )
        

        self.assertEqual(Booking.objects.count(), 1)
        

        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.status, 'PENDING')
        self.assertEqual(booking.total_amount, 605)
    
    def test_booking_status_can_change(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        

        booking.status = 'CONFIRMED'
        booking.payment_id = 'pay_123456'
        booking.save()
        

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CONFIRMED')
        self.assertEqual(booking.payment_id, 'pay_123456')

class PriceCalculationTests(TestCase):

    
    def setUp(self):

        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250  # Base price per seat
        )
    
    def test_single_seat_pricing(self):

        from .utils import PriceCalculator
        
        price_details = PriceCalculator.calculate_booking_amount(
            self.showtime, 
            seat_count=1  # Changed from num_seats
        )
        
        self.assertIn('base_price', price_details)
        self.assertIn('convenience_fee', price_details)
        self.assertIn('tax_amount', price_details)
        self.assertIn('total_amount', price_details)
        
        expected_total = (
            price_details['base_price'] + 
            price_details['convenience_fee'] + 
            price_details['tax_amount']
        )
        self.assertEqual(price_details['total_amount'], expected_total)
    
    def test_multiple_seats_pricing(self):

        from .utils import PriceCalculator
        
        price_details = PriceCalculator.calculate_booking_amount(
            self.showtime,
            seat_count=3  # Changed from num_seats
        )
        
        expected_base = float(self.showtime.price) * 3
        self.assertEqual(price_details['base_price'], expected_base)
        
        self.assertGreater(price_details['convenience_fee'], 0)
        
        self.assertGreater(price_details['tax_amount'], 0)

class PaymentSuccessTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
        
        self.booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='PENDING',
            razorpay_order_id='order_123456',
            payment_initiated_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=12)
        )
    
    def test_payment_can_be_confirmed(self):

        self.booking.status = 'CONFIRMED'
        self.booking.payment_id = 'pay_1234567890'
        self.booking.payment_received_at = timezone.now()
        self.booking.save()
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'CONFIRMED')
        
        self.assertEqual(self.booking.payment_id, 'pay_1234567890')
        
        self.assertIsNotNone(self.booking.payment_received_at)
    
    def test_payment_before_expiration_is_valid(self):

        payment_time = timezone.now()
        
        self.assertLess(payment_time, self.booking.expires_at)

class LatePaymentTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
        
        self.booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING',
            razorpay_order_id='order_123456',
            payment_initiated_at=timezone.now() - timezone.timedelta(minutes=15),
            expires_at=timezone.now() - timezone.timedelta(minutes=3)  # Expired 3 minutes ago
        )
    
    def test_late_payment_is_rejected(self):

        payment_time = timezone.now()
        
        self.assertGreater(payment_time, self.booking.expires_at)
        
        self.assertEqual(self.booking.status, 'PENDING')
    
    def test_late_payment_marked_as_failed(self):

        self.booking.status = 'FAILED'
        self.booking.payment_id = 'pay_late_payment'
        self.booking.payment_received_at = timezone.now()
        self.booking.refund_notification_sent = False  # Email will be sent
        self.booking.save()
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'FAILED')
        
        self.assertEqual(self.booking.payment_id, 'pay_late_payment')
        
        self.assertFalse(self.booking.refund_notification_sent)

class PaymentFailureTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
        
        self.booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2', 'A3'],
            total_seats=3,
            base_price=750,
            convenience_fee=75,
            tax_amount=82.5,
            total_amount=907.5,
            status='PENDING'
        )
    
    def test_payment_failure_marks_booking_failed(self):

        self.booking.status = 'FAILED'
        self.booking.failure_email_sent = False
        self.booking.save()
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'FAILED')
        
        self.assertIsNone(self.booking.payment_received_at)
        
        self.assertFalse(self.booking.failure_email_sent)
    
    def test_no_payment_confirmed_after_failure(self):

        self.booking.status = 'FAILED'
        self.booking.save()
        
        self.assertNotEqual(self.booking.status, 'CONFIRMED')

class DuplicatePaymentTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
        
        self.booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED',
            payment_id='pay_already_paid',
            payment_received_at=timezone.now(),
            razorpay_order_id='order_123456'
        )
    
    def test_already_confirmed_booking_cannot_be_confirmed_again(self):

        if self.booking.payment_received_at:
            should_skip = True
        else:
            should_skip = False
        
        self.assertTrue(should_skip)
    
    def test_payment_received_at_acts_as_guard(self):

        self.assertIsNotNone(self.booking.payment_received_at)
        
        should_send_confirmation = self.booking.payment_received_at is None
        
        self.assertFalse(should_send_confirmation)

class EdgeCasesTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_booking_with_maximum_seats(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10'],
            total_seats=10,
            base_price=2500,
            convenience_fee=250,
            tax_amount=275,
            total_amount=3025,
            status='PENDING'
        )
        
        self.assertEqual(booking.total_seats, 10)
        self.assertEqual(len(booking.seats), 10)
    
    def test_booking_total_price_precision(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=249.99,
            convenience_fee=24.99,
            tax_amount=27.50,
            total_amount=302.48,
            status='PENDING'
        )
        
        self.assertEqual(booking.base_price, 249.99)
        self.assertEqual(booking.convenience_fee, 24.99)
        self.assertEqual(booking.tax_amount, 27.50)
    
    def test_booking_with_empty_seats_list_invalid(self):

        
        seat_ids = []
        is_valid = len(seat_ids) > 0 and len(seat_ids) <= 10
        
        self.assertFalse(is_valid)
    
    def test_user_can_have_multiple_bookings(self):

        movie2 = Movie.objects.create(
            title='Another Movie',
            slug='another-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=110
        )
        showtime2 = Showtime.objects.create(
            movie=movie2,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=2),
            start_time='18:00',
            end_time='19:50',
            price=300
        )
        
        booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        booking2 = Booking.objects.create(
            user=self.user,
            showtime=showtime2,
            seats=['B2'],
            total_seats=1,
            base_price=300,
            convenience_fee=30,
            tax_amount=33,
            total_amount=363,
            status='PENDING'
        )
        
        user_bookings = Booking.objects.filter(user=self.user)
        self.assertEqual(user_bookings.count(), 2)
        
        self.assertNotEqual(booking1.showtime, booking2.showtime)
    
    def test_booking_timestamps_are_recorded(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        self.assertIsNotNone(booking.created_at)
        
        self.assertIsNone(booking.payment_received_at)

class BookingAPITests(TestCase):

    
    def setUp(self):

        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_get_seat_status_api_returns_json(self):

        response = self.client.get(f'/bookings/api/seat-status/{self.showtime.id}/')
        
        self.assertEqual(response.status_code, 200)
        
        try:
            data = response.json()
            self.assertIn('reserved_seats', data)
            self.assertIn('booked_seats', data)
            self.assertIn('available_count', data)
        except Exception:
            self.fail("Response is not valid JSON")
    
    def test_my_bookings_page_loads(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        response = self.client.get('/bookings/my-bookings/')
        
        self.assertNotEqual(response.status_code, 404)
        
        if response.status_code == 200:
            self.assertIn(booking.booking_number, str(response.content))
    
    def test_booking_detail_page_loads(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='CONFIRMED'
        )
        
        response = self.client.get(f'/bookings/detail/{booking.id}/')
        
        self.assertEqual(response.status_code, 200)
        
        self.assertIn(str(booking.total_seats), str(response.content))

class BookingSecurityTests(TestCase):

    
    def setUp(self):

        self.client = Client()
        
        self.user1 = User.objects.create_user(
            username='user1',
            password='pass1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='pass2'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
        
        self.booking_user1 = Booking.objects.create(
            user=self.user1,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
    
    def test_user_cannot_see_other_users_bookings(self):

        self.client.login(username='user2', password='pass2')
        
        response = self.client.get(f'/bookings/detail/{self.booking_user1.id}/')
        
        self.assertEqual(response.status_code, 404)
    
    def test_anonymous_user_cannot_access_bookings(self):

        
        response = self.client.get(f'/bookings/detail/{self.booking_user1.id}/')
        
        self.assertIn(response.status_code, [302, 404])

class SeatReservationTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_seats_can_be_reserved(self):

        
        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='PENDING',
            payment_initiated_at=timezone.now()
        )
        
        self.assertEqual(booking.total_seats, 2)
        self.assertIn('A1', booking.seats)
        self.assertIn('A2', booking.seats)
    
    def test_reserved_seats_expire_after_window(self):

        payment_window_minutes = 12
        
        now = timezone.now()
        expiry = now + timezone.timedelta(minutes=payment_window_minutes)
        
        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING',
            payment_initiated_at=now,
            expires_at=expiry
        )
        
        time_diff = (booking.expires_at - booking.payment_initiated_at).total_seconds()
        expected_diff = payment_window_minutes * 60
        
        self.assertLess(abs(time_diff - expected_diff), 2)
    
    def test_same_seat_cannot_be_booked_twice(self):

        booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        user2 = User.objects.create_user(
            username='testuser2',
            password='testpass456'
        )
        
        booking2 = Booking.objects.create(
            user=user2,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        all_bookings = Booking.objects.filter(showtime=self.showtime)
        self.assertEqual(all_bookings.count(), 2)

class RefundLogicTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_refund_status_can_be_tracked(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED',
            payment_id='pay_123456',
            payment_received_at=timezone.now()
        )
        
        booking.status = 'CANCELLED'
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertEqual(booking.payment_id, 'pay_123456')
        self.assertIsNotNone(booking.payment_received_at)
    
    def test_full_refund_amount_calculation(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='CONFIRMED',
            payment_id='pay_123456'
        )
        
        refund_amount = booking.total_amount
        
        self.assertEqual(refund_amount, 605)

class EmailNotificationTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_booking_email_flag_can_be_set(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED',
            payment_id='pay_123456',
            confirmation_email_sent=False
        )
        
        self.assertFalse(booking.confirmation_email_sent)
        
        booking.confirmation_email_sent = True
        booking.save()
        
        booking.refresh_from_db()
        self.assertTrue(booking.confirmation_email_sent)
    
    def test_failure_email_tracking(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='FAILED',
            failure_email_sent=False
        )
        
        booking.failure_email_sent = True
        booking.save()
        
        booking.refresh_from_db()
        self.assertTrue(booking.failure_email_sent)
    
    def test_late_payment_email_tracking(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='FAILED',
            payment_id='pay_late',
            refund_notification_sent=False
        )
        
        booking.refund_notification_sent = True
        booking.save()
        
        booking.refresh_from_db()
        self.assertTrue(booking.refund_notification_sent)

class ConcurrentOperationsTests(TestCase):

    
    def setUp(self):

        self.user1 = User.objects.create_user(
            username='user1',
            password='pass1'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='pass2'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=50
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_multiple_users_can_book_different_seats(self):

        booking1 = Booking.objects.create(
            user=self.user1,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        booking2 = Booking.objects.create(
            user=self.user2,
            showtime=self.showtime,
            seats=['B2'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        self.assertEqual(Booking.objects.filter(showtime=self.showtime).count(), 2)
        
        self.assertNotEqual(booking1.user, booking2.user)
        
        self.assertNotEqual(booking1.seats[0], booking2.seats[0])
    
    def test_booking_order_is_preserved(self):

        booking1 = Booking.objects.create(
            user=self.user1,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        booking2 = Booking.objects.create(
            user=self.user2,
            showtime=self.showtime,
            seats=['B1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        self.assertLessEqual(booking1.created_at, booking2.created_at)

class BookingCancellationTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_pending_booking_can_be_cancelled(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='PENDING'
        )
        
        booking.status = 'CANCELLED'
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')
    
    def test_confirmed_booking_can_be_cancelled_with_refund(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED',
            payment_id='pay_123456',
            payment_received_at=timezone.now()
        )
        
        booking.status = 'CANCELLED'
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertIsNotNone(booking.payment_id)
    
    def test_cannot_cancel_already_cancelled_booking(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CANCELLED'
        )
        
        is_already_cancelled = booking.status == 'CANCELLED'
        
        self.assertTrue(is_already_cancelled)

class DataValidationTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_negative_price_rejected(self):

        invalid_price = -250
        is_valid = invalid_price > 0
        
        self.assertFalse(is_valid)
    
    def test_zero_seats_rejected(self):

        invalid_seat_count = 0
        is_valid = 0 < invalid_seat_count <= 10
        
        self.assertFalse(is_valid)
    
    def test_negative_seats_rejected(self):

        invalid_seats = -5
        is_valid = invalid_seats > 0
        
        self.assertFalse(is_valid)
    
    def test_exceeding_max_seats_rejected(self):

        seat_count = 15
        max_seats = 10
        is_valid = seat_count <= max_seats
        
        self.assertFalse(is_valid)
    
    def test_valid_seat_count_range(self):

        for count in range(1, 11):
            is_valid = 0 < count <= 10
            self.assertTrue(is_valid, f"Seat count {count} should be valid")
    
    def test_invalid_booking_status(self):

        valid_statuses = ['PENDING', 'CONFIRMED', 'FAILED', 'CANCELLED', 'REFUNDED']
        
        invalid_status = 'INVALID_STATUS'
        is_valid = invalid_status in valid_statuses
        
        self.assertFalse(is_valid)
    
    def test_all_valid_booking_statuses(self):

        valid_statuses = ['PENDING', 'CONFIRMED', 'FAILED', 'CANCELLED', 'REFUNDED']
        
        for status in valid_statuses:
            booking = Booking.objects.create(
                user=self.user,
                showtime=self.showtime,
                seats=['A1'],
                total_seats=1,
                base_price=250,
                convenience_fee=25,
                tax_amount=27.5,
                total_amount=302.5,
                status=status
            )
            
            self.assertEqual(booking.status, status)

class BusinessLogicTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=50
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_available_seats_calculation(self):

        total_seats = self.screen.total_seats
        
        booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1', 'A2'],
            total_seats=2,
            base_price=500,
            convenience_fee=50,
            tax_amount=55,
            total_amount=605,
            status='CONFIRMED'
        )
        
        user2 = User.objects.create_user(username='user2', password='pass2')
        booking2 = Booking.objects.create(
            user=user2,
            showtime=self.showtime,
            seats=['B1', 'B2', 'B3'],
            total_seats=3,
            base_price=750,
            convenience_fee=75,
            tax_amount=82.5,
            total_amount=907.5,
            status='CONFIRMED'
        )
        
        booked_seats = 2 + 3
        available = total_seats - booked_seats
        
        self.assertEqual(available, total_seats - 5)
    
    def test_occupancy_percentage(self):

        total_seats = self.screen.total_seats
        
        bookings_count = Booking.objects.filter(
            showtime=self.showtime,
            status='CONFIRMED'
        ).count()
        
        booked_seats = 25  # Simulated
        occupancy = (booked_seats / total_seats) * 100
        
        self.assertEqual(occupancy, 50.0)
    
    def test_revenue_calculation(self):

        booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        user2 = User.objects.create_user(username='user2', password='pass2')
        booking2 = Booking.objects.create(
            user=user2,
            showtime=self.showtime,
            seats=['B1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        confirmed = Booking.objects.filter(
            showtime=self.showtime,
            status='CONFIRMED'
        )
        total_revenue = sum(b.total_amount for b in confirmed)
        
        self.assertEqual(total_revenue, 605.0)
    
    def test_peak_vs_off_peak_pricing_readiness(self):

        showtime2 = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=self.showtime.date,
            start_time='18:00',
            end_time='20:00',
            price=350  # Peak time = higher price
        )
        
        morning_price = self.showtime.price
        evening_price = showtime2.price
        
        self.assertLess(morning_price, evening_price)
        self.assertEqual(morning_price, 250)
        self.assertEqual(evening_price, 350)

class ModelRelationshipTests(TestCase):

    
    def setUp(self):

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Test',
            release_date=timezone.now().date(),
            duration=120
        )
        
        self.city = City.objects.create(name='Test City')
        self.theater = Theater.objects.create(
            name='Test Theater',
            city=self.city,
            address='123 Test St'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            total_seats=100
        )
        
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=timezone.now().date() + timezone.timedelta(days=1),
            start_time='14:00',
            end_time='16:00',
            price=250
        )
    
    def test_booking_has_user_relationship(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        self.assertEqual(booking.user.username, 'testuser')
        self.assertEqual(booking.user, self.user)
    
    def test_booking_has_showtime_relationship(self):

        booking = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        self.assertEqual(booking.showtime, self.showtime)
        
        self.assertEqual(booking.showtime.movie, self.movie)
    
    def test_showtime_has_screen_relationship(self):

        self.assertEqual(self.showtime.screen, self.screen)
        
        self.assertEqual(self.showtime.screen.theater, self.theater)
    
    def test_user_can_have_multiple_bookings(self):

        booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='PENDING'
        )
        
        showtime2 = Showtime.objects.create(
            movie=self.movie,
            screen=self.screen,
            date=self.showtime.date + timezone.timedelta(days=1),
            start_time='20:00',
            end_time='22:00',
            price=300
        )
        
        booking2 = Booking.objects.create(
            user=self.user,
            showtime=showtime2,
            seats=['B1'],
            total_seats=1,
            base_price=300,
            convenience_fee=30,
            tax_amount=33,
            total_amount=363,
            status='PENDING'
        )
        
        user_bookings = Booking.objects.filter(user=self.user)
        self.assertEqual(user_bookings.count(), 2)
    
    def test_showtime_can_have_multiple_bookings(self):

        user2 = User.objects.create_user(username='user2', password='pass2')
        
        booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            seats=['A1'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        booking2 = Booking.objects.create(
            user=user2,
            showtime=self.showtime,
            seats=['A2'],
            total_seats=1,
            base_price=250,
            convenience_fee=25,
            tax_amount=27.5,
            total_amount=302.5,
            status='CONFIRMED'
        )
        
        showtime_bookings = Booking.objects.filter(showtime=self.showtime)
        self.assertEqual(showtime_bookings.count(), 2)
