from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging

from .models import Booking, Transaction
from .utils import SeatManager, PriceCalculator
from .razorpay_utils import razorpay_client

logger = logging.getLogger(__name__)

class BookingService:

    
    @staticmethod
    @transaction.atomic
    def create_booking_with_seats(user, showtime, seat_ids):

        try:

            success = SeatManager.reserve_seats(showtime.id, seat_ids, user.id)
            if not success:
                return None, False, "One or more seats are no longer available"
            

            price_details = PriceCalculator.calculate_booking_amount(
                showtime, 
                len(seat_ids)
            )
            

            booking = Booking.objects.create(
                user=user,
                showtime=showtime,
                seats=seat_ids,
                total_seats=len(seat_ids),
                base_price=price_details['base_price'],
                convenience_fee=price_details['convenience_fee'],
                tax_amount=price_details['tax_amount'],
                total_amount=price_details['total_amount'],
                status='PENDING'
            )
            
            logger.info(f"Booking created: {booking.booking_number} for user {user.id}")
            return booking, True, None
            
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")

            SeatManager.release_seats(showtime.id, seat_ids)
            return None, False, str(e)
    
    @staticmethod
    @transaction.atomic
    def get_or_create_razorpay_order(booking):

        try:

            can_create, reason = booking.can_create_payment_order()
            

            existing_order_id = booking.get_or_reuse_razorpay_order()
            if existing_order_id:
                logger.info(f"Reusing existing Razorpay order: {existing_order_id} for booking {booking.booking_number}")
                return {
                    'success': True,
                    'order_id': existing_order_id,
                    'amount': int(booking.total_amount * 100),
                    'currency': 'INR',
                    'is_mock': 'xxxx' in settings.RAZORPAY_KEY_ID,
                    'reused': True
                }, False, None
            

            if not can_create:
                logger.warning(f"Cannot create Razorpay order for booking {booking.booking_number}: {reason}")
                return None, False, reason
            

            order_data = razorpay_client.create_order(
                amount=booking.total_amount,
                receipt=f"booking_{booking.booking_number}",
                notes={
                    'booking_id': booking.id,
                    'booking_number': booking.booking_number,
                    'user_id': booking.user.id,
                    'showtime_id': booking.showtime.id
                }
            )
            
            if not order_data['success']:
                logger.error(f"Razorpay order creation failed: {order_data.get('error')}")
                return None, False, order_data.get('error', 'Payment gateway error')
            

            booking.razorpay_order_id = order_data['order_id']
            booking.save(update_fields=['razorpay_order_id'])
            
            logger.info(f"Created new Razorpay order: {order_data['order_id']} for booking {booking.booking_number}")
            
            order_data['reused'] = False
            return order_data, True, None
            
        except Exception as e:
            logger.error(f"Error in get_or_create_razorpay_order: {str(e)}")
            return None, False, str(e)
    
    @staticmethod
    @transaction.atomic
    def confirm_payment(booking, payment_id, signature_verified=False):
        
        try:

            if booking.status == 'CONFIRMED':
                logger.info(f"Booking {booking.booking_number} already confirmed. Skipping.")
                return True, "Already confirmed"
            

            if booking.status not in ['PENDING']:
                return False, f"Cannot confirm booking with status: {booking.status}"
            

            seats_valid = SeatManager.is_seat_still_available_for_user(
                booking.showtime.id,
                booking.seats,
                booking.user.id
            )
            
            if not seats_valid:
                logger.error(f"Seat validation failed for booking {booking.booking_number} during payment confirmation")
                booking.status = 'FAILED'
                booking.save(update_fields=['status'])
                SeatManager.release_seats(booking.showtime.id, booking.seats)
                return False, "Seats are no longer available. Refund will be initiated."
            

            booking.status = 'CONFIRMED'
            booking.payment_id = payment_id
            booking.confirmed_at = timezone.now()
            booking.payment_method = 'RAZORPAY'
            booking.payment_received_at = timezone.now() 
            

            booking.generate_qr_code()
            booking.save()
            

            SeatManager.confirm_seats(booking.showtime.id, booking.seats)
            

            from .email_utils import send_booking_confirmation_email
            send_booking_confirmation_email(booking.id)
            
            logger.info(f"Payment confirmed for booking {booking.booking_number}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error confirming payment: {str(e)}")
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def cancel_booking(booking, reason="User cancelled"):

        try:
            if booking.status in ['CANCELLED', 'EXPIRED', 'CONFIRMED']:
                return False, f"Cannot cancel booking with status: {booking.status}"
            
            booking.status = 'CANCELLED'
            booking.save(update_fields=['status'])
            

            SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
            
            logger.info(f"Booking {booking.booking_number} cancelled: {reason}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def expire_booking(booking):
 
        try:
            if booking.status != 'PENDING':
                return False, f"Cannot expire booking with status: {booking.status}"
            
            if not booking.is_expired():
                return False, "Booking has not expired yet"
            
            booking.status = 'EXPIRED'
            booking.save(update_fields=['status'])
            

            SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
            
            logger.info(f"Booking {booking.booking_number} expired and seats released (including user reservation)")
            return True, None
            
        except Exception as e:
            logger.error(f"Error expiring booking: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def force_expire_booking(booking, reason="Manual expiration"):

        try:
            if booking.status != 'PENDING':
                logger.warning(f"Cannot force expire booking {booking.booking_number} - status is {booking.status}")
                return False, f"Cannot expire booking with status: {booking.status}"
            

            other_pending = Booking.objects.filter(
                user=booking.user,
                showtime=booking.showtime,
                status='PENDING'
            ).exclude(id=booking.id)
            
            if other_pending.exists():
                logger.warning(f"Found {other_pending.count()} other PENDING bookings for user {booking.user.id} - expiring them too")
                for old_booking in other_pending:
                    old_booking.status = 'EXPIRED'
                    old_booking.save(update_fields=['status'])

                    SeatManager.release_seats(old_booking.showtime.id, old_booking.seats, user_id=old_booking.user.id)
                    logger.info(f"Also expired old booking: {old_booking.booking_number}")
            

            booking.status = 'EXPIRED'
            booking.save(update_fields=['status'])
            logger.info(f"Booking {booking.booking_number} status changed to EXPIRED")
            

            released = SeatManager.release_seats(booking.showtime.id, booking.seats, user_id=booking.user.id)
            logger.info(f"SeatManager.release_seats returned: {released}")
            

            from django.core.cache import cache
            cache_key = f"reserved_seats_{booking.showtime.id}"
            reserved_after = cache.get(cache_key) or []
            still_locked = [seat for seat in booking.seats if seat in reserved_after]
            
            if still_locked:
                logger.error(f"SEATS STILL LOCKED AFTER RELEASE: {still_locked}")

                cache.delete(cache_key)
                logger.info(f"Force deleted reserved_seats cache key")
            else:
                logger.info(f"All seats successfully released for booking {booking.booking_number}")
            
            logger.info(f"Booking {booking.booking_number} force expired: {reason}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error force expiring booking: {str(e)}", exc_info=True)
            return False, str(e)

class PaymentVerificationService:

    
    @staticmethod
    def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):

        try:
            is_valid = razorpay_client.verify_payment_signature(
                razorpay_order_id,
                razorpay_payment_id,
                razorpay_signature
            )
            
            if is_valid:
                logger.info(f"Payment signature verified for order {razorpay_order_id}")
                return True, None
            else:
                logger.warning(f"Invalid payment signature for order {razorpay_order_id}")
                return False, "Invalid payment signature"
                
        except Exception as e:
            logger.error(f"Error verifying payment signature: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def verify_webhook_signature(payload, signature):

        try:

            if 'xxxx' in settings.RAZORPAY_KEY_ID:
                return True, None
            

            from razorpay.utility import Utility
            utility = Utility()
            is_valid = utility.verify_webhook_signature(
                payload,
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            
            return is_valid, None if is_valid else "Invalid webhook signature"
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False, str(e)
