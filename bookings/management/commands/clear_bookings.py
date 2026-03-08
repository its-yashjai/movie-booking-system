from django.core.management.base import BaseCommand
from django.core.cache import cache
from bookings.models import Booking, Transaction
from movies.models import Movie, Genre, Language
from movies.theater_models import City, Theater, Screen, Showtime
from django.db import connection

class Command(BaseCommand):
    help = 'Clear all data: bookings, movies, shows, theaters, and seat reservations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )
        parser.add_argument(
            '--bookings-only',
            action='store_true',
            help='Only clear bookings and transactions, keep movies/theaters',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        bookings_only = options.get('bookings_only', False)

        if not force:
            if bookings_only:
                msg = '⚠️  This will DELETE ALL bookings and transactions!\n'
            else:
                msg = '⚠️  This will DELETE EVERYTHING: bookings, movies, shows, theaters!\n'
            
            confirm = input(msg + 'Are you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('❌ Cancelled.'))
                return

        try:
            self.stdout.write('🧹 Clearing Redis cache...')
            cache.clear()
            self.stdout.write(self.style.SUCCESS('✅ Redis cache cleared'))

            self.stdout.write('🗑️  Deleting all transactions...')
            transaction_count = Transaction.objects.all().count()
            Transaction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {transaction_count} transactions'))

            self.stdout.write('🗑️  Deleting all bookings...')
            booking_count = Booking.objects.all().count()
            Booking.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {booking_count} bookings'))

            if not bookings_only:
            
                self.stdout.write('🗑️  Deleting all showtimes...')
                showtime_count = Showtime.objects.all().count()
                Showtime.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {showtime_count} showtimes'))

                self.stdout.write('🗑️  Deleting all screens...')
                screen_count = Screen.objects.all().count()
                Screen.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {screen_count} screens'))

                self.stdout.write('🗑️  Deleting all theaters...')
                theater_count = Theater.objects.all().count()
                Theater.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {theater_count} theaters'))

                self.stdout.write('🗑️  Deleting all cities...')
                city_count = City.objects.all().count()
                City.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {city_count} cities'))

                self.stdout.write('🗑️  Deleting all movies...')
                movie_count = Movie.objects.all().count()
                Movie.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {movie_count} movies'))

                self.stdout.write('🗑️  Deleting all genres...')
                genre_count = Genre.objects.all().count()
                Genre.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {genre_count} genres'))

                self.stdout.write('🗑️  Deleting all languages...')
                language_count = Language.objects.all().count()
                Language.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {language_count} languages'))

            self.stdout.write(self.style.SUCCESS('\n🎉 All data cleared!'))
            self.stdout.write(self.style.SUCCESS('You can now add fresh test data.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
