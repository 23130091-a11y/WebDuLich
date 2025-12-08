"""
Management command to clear cache
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Clear application cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--key',
            type=str,
            help='Specific cache key to clear'
        )

    def handle(self, *args, **options):
        key = options.get('key')
        
        if key:
            # Clear specific key
            cache.delete(key)
            self.stdout.write(self.style.SUCCESS(
                f'✅ Cleared cache key: {key}'
            ))
        else:
            # Clear all cache
            cache.clear()
            self.stdout.write(self.style.SUCCESS(
                '✅ Cleared all cache!'
            ))
