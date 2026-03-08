
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moviebooking.settings')

app = Celery('moviebooking')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

from bookings import email_utils  # noqa: F401

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

app.conf.beat_schedule = {
    'release-expired-bookings-every-minute': {
        'task': 'bookings.tasks.release_expired_bookings',
        'schedule': 60.0,  # Every minute
    },
    'send-showtime-reminders-every-hour': {
        'task': 'bookings.tasks.send_showtime_reminders',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-data-daily': {
        'task': 'bookings.tasks.cleanup_old_data',
        'schedule': 86400.0,  # Daily
    },
}