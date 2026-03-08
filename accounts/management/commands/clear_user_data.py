import os
import sys
import django

# Configure Django settings if running directly
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moviebooking.settings')
    django.setup()

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from accounts.models import UserProfile
from bookings.models import Booking, Transaction


class Command(BaseCommand):
    help = 'Clear all user data and booking history from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the deletion without asking',
        )

    def handle(self, *args, **options):
        # Count records before deletion
        user_count = User.objects.count()
        booking_count = Booking.objects.count()
        transaction_count = Transaction.objects.count()
        log_count = LogEntry.objects.count()

        self.stdout.write(self.style.WARNING(
            f'\n⚠️  This will delete:\n'
            f'  - {user_count} user(s)\n'
            f'  - {booking_count} booking(s)\n'
            f'  - {transaction_count} transaction(s)\n'
            f'  - {log_count} admin log entry(ies)\n'
        ))

        if not options['confirm']:
            confirm = input('\n⚠️  Are you sure you want to delete all user data and admin logs? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        # Delete admin logs first
        LogEntry.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {log_count} admin log entry(ies)'))

        # Delete transactions first (they reference bookings)
        Transaction.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {transaction_count} transaction(s)'))

        # Delete bookings (they reference users)
        Booking.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {booking_count} booking(s)'))

        # Delete user profiles and users
        UserProfile.objects.all().delete()
        # Keep superusers if any
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {user_count} user(s) (keeping superusers)'))

        self.stdout.write(self.style.SUCCESS('\n✓ All user data, bookings, and admin history cleared successfully!\n'))
