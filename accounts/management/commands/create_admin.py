from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create or reset admin/superuser account with verified email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Admin username (default: admin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@moviebooking.com',
            help='Admin email (default: admin@moviebooking.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Admin password (default: admin123)'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing admin user if found'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options.get('password') or 'admin123'
        reset = options['reset']

        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('  ADMIN USER CREATION/RESET TOOL'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))

        try:
            user = User.objects.filter(username=username).first()
            
            if user and not reset:
                self.stdout.write(
                    self.style.ERROR(f'❌ User "{username}" already exists!')
                )
                self.stdout.write(
                    self.style.WARNING('   Use --reset flag to reset this user\n')
                )
                return

            if user and reset:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Resetting existing user: {username}')
                )
                user.email = email
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.is_email_verified = True
                profile.email_verified_at = timezone.now()
                profile.email_otp = None
                profile.otp_created_at = None
                profile.otp_attempts = 0
                profile.save()
                
                self.stdout.write(self.style.SUCCESS(f'✅ Admin user reset successfully!\n'))
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚙️  Creating new admin user: {username}')
                )
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'is_email_verified': True,
                        'email_verified_at': timezone.now()
                    }
                )
                if not created:
                    profile.is_email_verified = True
                    profile.email_verified_at = timezone.now()
                    profile.save()
                
                self.stdout.write(self.style.SUCCESS(f'✅ Admin user created successfully!\n'))

            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(self.style.SUCCESS('  ADMIN CREDENTIALS'))
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(f'  Username:       {username}')
            self.stdout.write(f'  Email:          {email}')
            self.stdout.write(f'  Password:       {password}')
            self.stdout.write(f'  Staff Status:   {user.is_staff}')
            self.stdout.write(f'  Superuser:      {user.is_superuser}')
            self.stdout.write(f'  Active:         {user.is_active}')
            self.stdout.write(f'  Email Verified: {profile.is_email_verified}')
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

            self.stdout.write(self.style.WARNING('  ACCESS URLS:'))
            self.stdout.write('  Django Admin:  /admin/')
            self.stdout.write('  Custom Admin:  /custom-admin/')
            self.stdout.write(self.style.WARNING('='*60 + '\n'))

            self.stdout.write(
                self.style.SUCCESS('✅ Admin user is ready! You can now login to both admin panels.\n')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating/resetting admin user: {str(e)}\n')
            )
            raise CommandError(f'Failed to create/reset admin: {str(e)}')
