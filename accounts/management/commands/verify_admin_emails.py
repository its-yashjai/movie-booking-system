from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Verify email for all admin and staff users'

    def handle(self, *args, **options):
        admin_users = User.objects.filter(is_superuser=True) | User.objects.filter(is_staff=True)
        admin_users = admin_users.distinct()
        
        if not admin_users:
            self.stdout.write(self.style.WARNING('No admin or staff users found'))
            return
        
        fixed_count = 0
        created_count = 0
        
        for user in admin_users:
            try:
                profile = user.profile
                if not profile.is_email_verified:
                    profile.is_email_verified = True
                    profile.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Verified email for: {user.username} ({user.email})')
                    )
                    fixed_count += 1
                else:
                    self.stdout.write(f'   Already verified: {user.username}')
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(user=user, is_email_verified=True)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created verified profile for: {user.username} ({user.email})')
                )
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Complete! Fixed {fixed_count} profiles, created {created_count} new profiles'
            )
        )
