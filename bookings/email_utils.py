import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

def send_email_safe(task_func, *args, **kwargs):
    # Since Celery is removed, tasks run synchronously
    try:
        logger.info(f"📧 Sending email synchronously: {task_func.__name__} with args: {args}")
        result = task_func(*args, **kwargs)
        logger.info(f"✅ 📧 Email sent successfully: {task_func.__name__}. Result: {result}")
        return result
    except Exception as e:
        logger.error(
            f"❌ 📧 ERROR sending email: {task_func.__name__}\n"
            f"   Error: {type(e).__name__}: {str(e)}\n"
            f"   Args: {args}\n"
            f"   Email NOT sent to user."
        )
        return None

@shared_task
def send_booking_confirmation_email(booking_id):
    from .models import Booking
    from django.db import transaction
    
    try:
        logger.info(f"🔄 [CONFIRMATION_EMAIL] Processing confirmation email for booking_id={booking_id}")
        with transaction.atomic():
            booking = Booking.objects.get(id=booking_id)
            user = booking.user
            
            logger.info(
                f"📧 [CONFIRMATION_EMAIL] Found booking: {booking.booking_number} | "
                f"User: {user.email} | Status: {booking.status} | "
                f"Payment Received: {booking.payment_received_at is not None}"
            )
            

            if not booking.payment_received_at:
                logger.warning(
                    f"⏭️  SKIPPED: Confirmation email for {booking.booking_number} - "
                    f"payment_received_at not set (payment not received yet)"
                )
                return f"Email not sent - payment not received yet"
            

            if booking.status != 'CONFIRMED':
                logger.warning(
                    f"⏭️  SKIPPED: Confirmation email for {booking.booking_number} - "
                    f"Status is {booking.status}, not CONFIRMED"
                )
                return f"Email not sent - booking status is {booking.status}"
            

            if booking.confirmation_email_sent:
                logger.info(
                    f"⏭️  SKIPPED: Confirmation email for {booking.booking_number} - "
                    f"Already sent (idempotency check)"
                )
                return f"Email already sent - skipping"
            
            booking.confirmation_email_sent = True
            booking.save()
        
        logger.info(f"📧 Generating confirmation email for booking {booking.booking_number}")
        
        context = {
            'booking': booking,
            'user': user,
            'movie': booking.showtime.movie,
            'showtime': booking.showtime,
            'theater': booking.showtime.screen.theater,
            'total_amount': booking.total_amount,
        }
        
        text_content = render_to_string('booking_confirmation.txt', context)
        html_content = render_to_string('booking_confirmation.html', context)
        
        subject = f'🎬 Booking Confirmed - {booking.booking_number}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        
        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        

        email.send()
        
        logger.info(f"✅ 📧 CONFIRMATION EMAIL SENT | Booking: {booking.booking_number} | To: {user.email}")
        return f"Email sent successfully to {user.email}"
    except Exception as e:
        logger.error(f"❌ 📧 ERROR sending confirmation email for booking {booking_id}: {type(e).__name__}: {str(e)}")
        return f"Error sending email: {str(e)}"

@shared_task
def send_payment_failed_email(booking_id):

    from .models import Booking
    from django.db import transaction
    
    try:
        logger.info(f"🔄 [FAILURE_EMAIL] Processing payment failed email for booking_id={booking_id}")
        

        with transaction.atomic():
            booking = Booking.objects.get(id=booking_id)
            user = booking.user
            
            logger.info(
                f"❌ [FAILURE_EMAIL] Found booking: {booking.booking_number} | "
                f"User: {user.email} | Status: {booking.status} | "
                f"Payment Received: {booking.payment_received_at is not None}"
            )
            

            if booking.payment_received_at:
                logger.warning(
                    f"⏭️  Skipping payment failed email for {booking.booking_number} - "
                    f"payment_received_at is set ({booking.payment_received_at}). Payment actually succeeded!"
                )
                return f"Email not sent - payment was received"
            

            if booking.status != 'FAILED':
                logger.warning(
                    f"⏭️  Skipping payment failed email for {booking.booking_number} - "
                    f"Status is {booking.status}, not FAILED"
                )
                return f"Email not sent - booking status is {booking.status}"
            

            if booking.failure_email_sent:
                logger.warning(
                    f"⏭️  Skipping payment failed email for {booking.booking_number} - "
                    f"Email already sent"
                )
                return f"Email already sent - skipping"
            
            booking.failure_email_sent = True
            booking.save()
        
        logger.info(f"📧 Generating payment failed email for booking {booking.booking_number}")
        
        context = {
            'booking': booking,
            'user': user,
            'movie': booking.showtime.movie,
        }
        
        text_content = render_to_string('payment_failed.txt', context)
        html_content = render_to_string('payment_failed.html', context)
        
        subject = f'❌ Payment Failed - Booking {booking.booking_number}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        
        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"✅ Payment failed email sent to {user.email}")
        return f"Payment failed email sent to {user.email}"
    except Exception as e:
        logger.error(f"❌ Error sending payment failed email: {str(e)}")
        return f"Error sending payment failed email: {str(e)}"

@shared_task
def send_seat_reminder_email(booking_id):
    from .models import Booking
    
    try:
        booking = Booking.objects.get(id=booking_id)
        
        if booking.status != 'CONFIRMED':
            logger.warning(f"⚠️ Booking {booking.booking_number} is not confirmed. Skipping reminder.")
            return f"Booking not confirmed. Reminder skipped."
        
        logger.info(f"📧 Generating reminder email for booking {booking.booking_number}")
        
        context = {
            'booking': booking,
            'user': booking.user,
            'movie': booking.showtime.movie,
            'showtime': booking.showtime,
            'theater': booking.showtime.screen.theater,
        }
        
        text_content = render_to_string('showtime_reminder.txt', context)
        html_content = render_to_string('showtime_reminder.html', context)
        
        subject = f'⏰ Reminder: Your movie "{booking.showtime.movie.title}" starts soon!'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [booking.user.email]
        
        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"✅ Reminder email sent for booking {booking.booking_number}")
        return f"Reminder sent for booking {booking.booking_number}"
    except Exception as e:
        logger.error(f"❌ Error sending reminder email: {str(e)}")
        return f"Error sending reminder: {str(e)}"

@shared_task
def send_late_payment_email(booking_id):
    from .models import Booking
    
    try:
        booking = Booking.objects.get(id=booking_id)
        user = booking.user
        
        logger.info(
            f"📧 [LATE PAYMENT] Generating refund email for booking {booking.booking_number}\n"
            f"   Payment received at: {booking.payment_received_at}\n"
            f"   Window expired at: {booking.expires_at}\n"
            f"   Payment ID: {booking.payment_id}\n"
            f"   User: {user.email}"
        )
        
        context = {
            'booking': booking,
            'user': user,
            'movie': booking.showtime.movie,
            'showtime': booking.showtime,
            'theater': booking.showtime.screen.theater,
            'payment_received_at': booking.payment_received_at,
            'expires_at': booking.expires_at,
            'payment_id': booking.payment_id,
        }
        
        text_content = render_to_string('payment_late.txt', context)
        html_content = render_to_string('payment_late.html', context)
        
        subject = f'💰 Refund Initiated - Booking {booking.booking_number} (Payment After Timeout)'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        
        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"✅ [LATE PAYMENT] Refund email sent to {user.email} for booking {booking.booking_number}")
        
        booking.refund_notification_sent = True
        booking.save(update_fields=['refund_notification_sent'])
        
        return f"Late payment refund email sent to {user.email}"
    except Exception as e:
        logger.error(
            f"❌ [LATE PAYMENT] Error sending refund email for booking {booking_id}: {str(e)}\n"
            f"   Exception type: {type(e).__name__}"
        )
        return f"Error sending late payment email: {str(e)}"