"""
Management command để cleanup SearchHistory cũ
Chạy định kỳ (daily/weekly) để tránh database phình to
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from travel.models import SearchHistory


class Command(BaseCommand):
    help = 'Cleanup old search history records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete records older than X days (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'\n=== Search History Cleanup ===')
        self.stdout.write(f'Cutoff date: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Deleting records older than {days} days\n')
        
        # Count records to delete
        old_records = SearchHistory.objects.filter(created_at__lt=cutoff_date)
        count = old_records.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No old records to delete.'))
            return
        
        # Show statistics
        total_records = SearchHistory.objects.count()
        percentage = (count / total_records * 100) if total_records > 0 else 0
        
        self.stdout.write(f'Total records: {total_records}')
        self.stdout.write(f'Records to delete: {count} ({percentage:.1f}%)')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No records were deleted.'))
            
            # Show sample records
            self.stdout.write('\nSample records that would be deleted:')
            for record in old_records[:5]:
                self.stdout.write(
                    f'  - {record.created_at.strftime("%Y-%m-%d")} | '
                    f'Query: "{record.query}" | Results: {record.results_count}'
                )
            
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more records')
        else:
            # Delete records
            deleted_count, _ = old_records.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully deleted {deleted_count} records')
            )
            
            # Show remaining records
            remaining = SearchHistory.objects.count()
            self.stdout.write(f'Remaining records: {remaining}')
            
            # Show database size saved (approximate)
            # Assume ~200 bytes per record (query + metadata)
            size_saved_kb = (deleted_count * 200) / 1024
            if size_saved_kb > 1024:
                size_saved_mb = size_saved_kb / 1024
                self.stdout.write(f'Approximate space saved: {size_saved_mb:.2f} MB')
            else:
                self.stdout.write(f'Approximate space saved: {size_saved_kb:.2f} KB')
