"""
Management command to view cache statistics
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings


class Command(BaseCommand):
    help = 'View cache statistics and configuration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO(
            '\n' + '='*60 + '\n'
            '📊 CACHE STATISTICS\n'
            '='*60 + '\n'
        ))
        
        # Cache backend info
        cache_backend = settings.CACHES['default']['BACKEND']
        self.stdout.write(f'Backend: {cache_backend}')
        
        if 'locmem' in cache_backend.lower():
            self.stdout.write(self.style.WARNING(
                '\n⚠️ Using LocMemCache (in-memory)'
            ))
            self.stdout.write('   - Fast but limited to single process')
            self.stdout.write('   - Cache cleared on server restart')
            self.stdout.write('   - For production, consider Redis\n')
        
        # Cache timeouts
        self.stdout.write('\n⏱️ Cache Timeouts:')
        for key, timeout in settings.CACHE_TTL.items():
            minutes = timeout // 60
            seconds = timeout % 60
            if minutes > 0:
                time_str = f'{minutes}m {seconds}s' if seconds > 0 else f'{minutes}m'
            else:
                time_str = f'{seconds}s'
            self.stdout.write(f'   - {key}: {time_str}')
        
        # Test cache
        self.stdout.write('\n🧪 Testing cache...')
        test_key = 'cache_test_key'
        test_value = 'Hello Cache!'
        
        cache.set(test_key, test_value, 60)
        retrieved = cache.get(test_key)
        
        if retrieved == test_value:
            self.stdout.write(self.style.SUCCESS('   ✅ Cache is working!'))
        else:
            self.stdout.write(self.style.ERROR('   ❌ Cache test failed!'))
        
        cache.delete(test_key)
        
        self.stdout.write('\n' + '='*60 + '\n')
        self.stdout.write('💡 Commands:')
        self.stdout.write('   python manage.py clear_cache          # Clear all cache')
        self.stdout.write('   python manage.py clear_cache --key=X  # Clear specific key')
        self.stdout.write('\n')
