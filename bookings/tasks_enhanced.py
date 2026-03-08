

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from django.utils import timezone
from datetime import timedelta
from django_redis import get_redis_connection
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def release_expired_bookings(self):

    redis_conn = get_redis_connection("default")
    lock_key = "celery_lock:release_expired_bookings"
    

    lock_acquired = redis_conn.setnx(lock_key, "locked")
    
    if not lock_acquired:
        logger.info("Another worker is already processing expired bookings - skipping")
        return "Skipped - lock held by another worker"
    
    try:

        redis_conn.expire(lock_key, 300)
        

        from .models import Booking
        from .services import BookingService
        from .utils_enhanced import CacheInvalidator
        

        expired_bookings = Booking.objects.filter(
            status='PENDING',
            expires_at__lt=timezone.now()
        )
        
        released_count = 0
        failed_count = 0
        
        for booking in expired_bookings:
            try:

                success, error = BookingService.expire_booking(booking)
                
                if success:
                    released_count += 1

                    CacheInvalidator.invalidate_on_booking_expired(booking)
                    logger.info(f"Expired booking {booking.booking_number}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to expire {booking.booking_number}: {error}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Exception expiring {booking.booking_number}: {e}")
        
        result = f"Released {released_count} expired bookings, {failed_count} failed"
        logger.info(f"Booking expiration complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in release_expired_bookings task: {e}")

        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
    finally:

        redis_conn.delete(lock_key)

@shared_task
def send_showtime_reminders():

    try:
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
            try:
                send_seat_reminder_email(booking.id)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send reminder for booking {booking.id}: {e}")
        
        result = f"Sent {sent_count} showtime reminders"
        logger.info(result)
        return result
        
    except Exception as e:
        logger.error(f"Error in send_showtime_reminders task: {e}")
        return f"Error: {e}"

@shared_task
def cleanup_old_data():

    try:
        from .models import Booking
        from datetime import date
        

        old_date = date.today() - timedelta(days=30)
        old_bookings = Booking.objects.filter(
            showtime__date__lt=old_date
        )
        
        count = old_bookings.count()
        

        result = f"Found {count} old bookings to archive"
        logger.info(result)
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data task: {e}")
        return f"Error: {e}"

@shared_task
def warm_cache_for_upcoming_shows():

    try:
        from movies.theater_models import Showtime
        from .utils_enhanced import SeatManager
        

        now = timezone.now()
        upcoming_showtimes = Showtime.objects.filter(
            is_active=True,
            date__gte=now.date(),
            start_time__gte=now.time()
        ).order_by('date', 'start_time')[:20]  
        
        warmed_count = 0
        
        for showtime in upcoming_showtimes:
            try:

                SeatManager.get_seat_layout(showtime.id)
                SeatManager.get_available_seats(showtime.id)
                warmed_count += 1
            except Exception as e:
                logger.error(f"Cache warming failed for showtime {showtime.id}: {e}")
        
        result = f"Warmed cache for {warmed_count} showtimes"
        logger.info(result)
        return result
        
    except Exception as e:
        logger.error(f"Error in warm_cache_for_upcoming_shows task: {e}")
        return f"Error: {e}"

@shared_task
def monitor_cache_health():

    try:
        from django.core.cache import cache
        redis_conn = get_redis_connection("default")
        
        redis_conn.ping()
        
        info = redis_conn.info()
        
        metrics = {
            'connected_clients': info.get('connected_clients', 0),
            'used_memory_human': info.get('used_memory_human', 'N/A'),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
        }
        
        hits = metrics['keyspace_hits']
        misses = metrics['keyspace_misses']
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        result = f"Cache health: {hit_rate:.2f}% hit rate, {metrics['used_memory_human']} used"
        logger.info(result)
        logger.info(f"Cache metrics: {metrics}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in monitor_cache_health task: {e}")
        return f"Error: {e}"
