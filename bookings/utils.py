import json
import time
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q

class SeatManager:

    
    @staticmethod
    def generate_seat_layout(rows=10, cols=12):

        layout = []
        for row in range(rows):
            row_letter = chr(65 + row)  # A, B, C...
            row_seats = []
            for col in range(1, cols + 1):
                if col == 7:
                    row_seats.append(None)
                else:
                    seat_number = col if col < 7 else col - 1
                    row_seats.append({
                        'seat_id': f"{row_letter}{seat_number}",
                        'row': row_letter,
                        'number': seat_number,
                        'available': True,
                        'type': 'standard',
                        'price': 200.00,
                    })
            layout.append(row_seats)
        return layout
    
    @staticmethod
    def get_seat_layout(showtime_id):

        cache_key = f"seat_layout_{showtime_id}"
        
        layout = cache.get(cache_key)
        
        if not layout:
            layout = SeatManager.generate_seat_layout()
            cache.set(cache_key, layout, timeout=3600)  # Keep for 1 hour
        
        return layout
    
    @staticmethod
    def get_available_seats(showtime_id):

        cache_key = f"available_seats_{showtime_id}"
        available_seats = cache.get(cache_key)
        
        if available_seats is None:
            layout = SeatManager.get_seat_layout(showtime_id)
            available_seats = []
            for row in layout:
                for seat in row:
                    if seat and seat['available']:
                        available_seats.append(seat['seat_id'])
            
            from .models import Booking
            from django.utils import timezone
            
            booked_seats_query = Booking.objects.filter(
                showtime_id=showtime_id,
                status='CONFIRMED'
            ).only('seats').values_list('seats', flat=True)
            
            for seats_list in booked_seats_query:
                for seat_id in seats_list:
                    if seat_id in available_seats:
                        available_seats.remove(seat_id)
            
            pending_seats_query = Booking.objects.filter(
                showtime_id=showtime_id,
                status='PENDING',
                expires_at__gt=timezone.now()  # Not expired yet
            ).only('seats').values_list('seats', flat=True)
            
            for seats_list in pending_seats_query:
                for seat_id in seats_list:
                    if seat_id in available_seats:
                        available_seats.remove(seat_id)
            
            cache.set(cache_key, available_seats, timeout=30)
        
        return available_seats
    
    @staticmethod
    def get_reserved_seats(showtime_id):

        cache_key = f"reserved_seats_{showtime_id}"
        redis_reserved = cache.get(cache_key) or []
        
        from .models import Booking
        from django.utils import timezone
        
        pending_bookings = Booking.objects.filter(
            showtime_id=showtime_id,
            status='PENDING',
            expires_at__gt=timezone.now()  # Not expired yet
        ).only('seats').values_list('seats', flat=True)
        
        db_reserved = []
        for seats_list in pending_bookings:
            db_reserved.extend(seats_list)
        
        all_reserved = list(set(redis_reserved + db_reserved))
        return all_reserved
    
    @staticmethod
    def reserve_seats(showtime_id, seat_ids, user_id):

        if not seat_ids:
            return False
        
        available_seats = SeatManager.get_available_seats(showtime_id)
        reserved_seats = SeatManager.get_reserved_seats(showtime_id)
        
        user_reservation_key = f"seat_reservation_{showtime_id}_{user_id}"
        existing_user_res = cache.get(user_reservation_key)
        my_seats = existing_user_res.get('seat_ids', []) if existing_user_res else []
        
        for seat_id in seat_ids:
            if seat_id not in available_seats or (seat_id in reserved_seats and seat_id not in my_seats):
                return False
        
        new_reserved = list(set(reserved_seats + seat_ids))
        cache_key = f"reserved_seats_{showtime_id}"
        cache.set(cache_key, new_reserved, timeout=settings.SEAT_RESERVATION_TIMEOUT)
        
        cache.set(user_reservation_key, {
            'seat_ids': seat_ids,
            'reserved_at': time.time()
        }, timeout=settings.SEAT_RESERVATION_TIMEOUT)
        
        return True
    
    @staticmethod
    def release_seats(showtime_id, seat_ids=None, user_id=None):

        cache_key = f"reserved_seats_{showtime_id}"
        reserved_seats = cache.get(cache_key) or []
        
        if user_id:
            reservation_key = f"seat_reservation_{showtime_id}_{user_id}"
            cache.delete(reservation_key)
        
        if seat_ids:
            for sid in seat_ids:
                if sid in reserved_seats: 
                    reserved_seats.remove(sid)
        
        cache.set(cache_key, reserved_seats, timeout=settings.SEAT_RESERVATION_TIMEOUT)
        return True
    
    @staticmethod
    def confirm_seats(showtime_id, seat_ids):

        SeatManager.release_seats(showtime_id, seat_ids)
        
        cache_key = f"available_seats_{showtime_id}"
        available_seats = cache.get(cache_key)
        
        if available_seats is not None:
            for sid in seat_ids:
                if sid in available_seats: 
                    available_seats.remove(sid)
            cache.set(cache_key, available_seats, timeout=3600)
        
        return True

    @staticmethod
    def is_seat_still_available_for_user(showtime_id, seat_ids, user_id):

        from .models import Booking
        confirmed_bookings = Booking.objects.filter(
            showtime_id=showtime_id,
            status='CONFIRMED'
        ).exclude(user_id=user_id) # Don't check against the user's own current booking attempt
        
        for booking in confirmed_bookings:
            for seat in seat_ids:
                if seat in booking.seats:
                    return False
            
        return True

class PriceCalculator:

    TAX_RATE = Decimal('0.18')  # 18% GST
    CONVENIENCE_FEE = Decimal('30.00')
    
    @staticmethod
    def calculate_booking_amount(showtime, seat_count, seat_type='standard'):

        base_price = showtime.price * seat_count
        
        if seat_type == 'premium':
            base_price *= Decimal('1.5')
        elif seat_type == 'sofa':
            base_price *= Decimal('2.0')
        
        convenience_fee = PriceCalculator.CONVENIENCE_FEE
        tax_amount = (base_price + convenience_fee) * PriceCalculator.TAX_RATE
        total_amount = base_price + convenience_fee + tax_amount
        
        return {
            'base_price': round(base_price, 2),
            'convenience_fee': convenience_fee,
            'tax_amount': round(tax_amount, 2),
            'total_amount': round(total_amount, 2),
        }
