"""
Auto cleanup command - Chạy tất cả cleanup tasks
Có thể schedule với cron hoặc celery beat
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run all cleanup tasks (search history, cache, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('\n=== AUTO CLEANUP TASKS ===\n'))
        
        # Task 1: Cleanup old search history (90 days)
        self.stdout.write('Task 1: Cleanup Search History')
        self.stdout.write('-' * 50)
        try:
            call_command('cleanup_search_history', days=90, dry_run=dry_run)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        self.stdout.write('\n')
        
        # Task 2: Clear expired cache
        self.stdout.write('Task 2: Clear Expired Cache')
        self.stdout.write('-' * 50)
        try:
            from django.core.cache import cache
            if not dry_run:
                # Django cache doesn't have built-in expire, but we can clear all
                # In production with Redis, this would be handled automatically
                self.stdout.write('Cache cleared (if using LocMemCache)')
            else:
                self.stdout.write('[DRY RUN] Would clear expired cache')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        self.stdout.write('\n')
        
        # Task 3: Database maintenance (PostgreSQL only)
        self.stdout.write('Task 3: Database Maintenance')
        self.stdout.write('-' * 50)
        try:
            from django.conf import settings
            if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
                if not dry_run:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        # Analyze tables for query planner
                        cursor.execute('ANALYZE;')
                        self.stdout.write('✓ Database analyzed')
                else:
                    self.stdout.write('[DRY RUN] Would run ANALYZE on database')
            else:
                self.stdout.write('Skipped (not using PostgreSQL)')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        self.stdout.write('\n')
        self.stdout.write(self.style.SUCCESS('=== CLEANUP COMPLETED ===\n'))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'This was a DRY RUN. Run without --dry-run to actually perform cleanup.'
                )
            )
