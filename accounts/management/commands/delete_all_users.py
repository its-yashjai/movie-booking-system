from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Delete all users from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all users',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                'This will delete ALL users. Use --confirm to proceed.'
            ))
            return

        user_count = User.objects.count()
        
        if user_count == 0:
            self.stdout.write(self.style.SUCCESS('No users to delete'))
            return

        User.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {user_count} users'
        ))
