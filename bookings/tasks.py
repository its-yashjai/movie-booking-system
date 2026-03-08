
try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from django.utils import timezone
from datetime import timedelta

@shared_task
def release_expired_bookings():

    from .models import Booking
    from .services import BookingService
    import logging
    
    logger = logging.getLogger(__name__)

    expired_bookings = Booking.objects.filter(
        status='PENDING',
        expires_at__lt=timezone.now()
    )
    
    released_count = 0
    failed_count = 0
    
    for booking in expired_bookings:

        success, error = BookingService.expire_booking(booking)
        
        if success:
            released_count += 1
            logger.info(f"Released seats for expired booking {booking.booking_number}")
        else:
            failed_count += 1
            logger.error(f"Failed to expire booking {booking.booking_number}: {error}")
    
    logger.info(f"Booking expiration task complete: {released_count} expired, {failed_count} failed")
    return f"Released {released_count} expired bookings, {failed_count} failed"

@shared_task
def send_showtime_reminders():

    from .models import Booking
    from .email_utils import send_seat_reminder_email
    
    now = timezone.now()
    reminder_time = now + timedelta(hours=1)
    

    bookings = Booking.objects.filter(
        status='CONFIRMED',
        showtime__date=reminder_time.date(),
        showtime__start_time__hour=reminder_time.hour
    )
    
    sent_count = 0
    
    for booking in bookings:
        send_seat_reminder_email(booking.id)
        sent_count += 1
    
    return f"Sent {sent_count} showtime reminders"

@shared_task
def cleanup_old_data():

    from .models import Booking
    from datetime import date
    

    old_date = date.today() - timedelta(days=30)
    old_bookings = Booking.objects.filter(
        showtime__date__lt=old_date
    )
    
    count = old_bookings.count()

    
    return f"Found {count} old bookings to archive"