from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone


class Command(BaseCommand):
    help = 'Make an existing user an admin with full permissions'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to make admin')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.is_email_verified = True
            profile.email_verified_at = timezone.now()
            profile.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ {username} is now an admin!\n'
                f'   Staff: {user.is_staff}\n'
                f'   Superuser: {user.is_superuser}\n'
                f'   Email Verified: {profile.is_email_verified}'
            ))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User "{username}" not found'))
