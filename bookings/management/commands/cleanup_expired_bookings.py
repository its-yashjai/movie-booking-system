
from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Booking
from bookings.utils import SeatManager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup expired PENDING bookings and release seats'

    def handle(self, *args, **options):
        now = timezone.now()
        
        expired_bookings = Booking.objects.filter(
            status='PENDING',
            expires_at__lt=now
        )
        
        count = expired_bookings.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ No expired bookings to cleanup')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'⏰ Found {count} expired PENDING bookings. Cleaning up...')
        )
        
        for booking in expired_bookings:
            try:
                booking.status = 'FAILED'
                booking.save()
                
                SeatManager.release_seats(
                    booking.showtime.id,
                    booking.seats,
                    booking.user.id
                )
                
                logger.info(
                    f"✅ Expired booking {booking.booking_number} marked as FAILED. "
                    f"Seats {booking.seats} released."
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {booking.booking_number} | Seats: {booking.seats}'
                    )
                )
                
            except Exception as e:
                logger.error(
                    f"❌ Error processing expired booking {booking.booking_number}: {e}"
                )
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {booking.booking_number} | Error: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Cleanup complete. Processed {count} bookings.')
        )
