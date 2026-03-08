from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count


class Command(BaseCommand):
    help = 'Remove duplicate users by email, keeping the most recent one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        duplicate_emails = (
            User.objects.exclude(email='')
            .values('email')
            .annotate(email_count=Count('id'))
            .filter(email_count__gt=1)
        )

        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS('No duplicate users found!'))
            return

        total_removed = 0
        self.stdout.write(f'Found {len(duplicate_emails)} email(s) with duplicates:\n')
        
        for item in duplicate_emails:
            email = item['email']
            count = item['email_count']
            
            users = User.objects.filter(email=email).order_by('-date_joined')
            
            keep_user = users.first()
            duplicate_users = users.exclude(id=keep_user.id)
            
            self.stdout.write(f'\n📧 Email: {email}')
            self.stdout.write(f'   Total users: {count}')
            self.stdout.write(f'   ✅ Keeping: {keep_user.username} (ID: {keep_user.id}, joined: {keep_user.date_joined})')
            
            for dup_user in duplicate_users:
                self.stdout.write(
                    self.style.WARNING(
                        f'   ❌ {"Would delete" if dry_run else "Deleting"}: {dup_user.username} '
                        f'(ID: {dup_user.id}, joined: {dup_user.date_joined})'
                    )
                )
                
                if not dry_run:
                    dup_user.delete()
                    total_removed += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n\nDRY RUN: Would have removed {total_removed} duplicate user(s)'
                )
            )
            self.stdout.write('Run without --dry-run to actually delete duplicates')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n\n✅ Successfully removed {total_removed} duplicate user(s)!'
                )
            )
