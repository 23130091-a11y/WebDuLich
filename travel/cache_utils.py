"""
Cache utilities for Travel app
Provides helper functions for caching data
"""

import hashlib
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_cache_key(prefix, *args, **kwargs):
    """
    Generate a unique cache key from prefix and arguments
    
    Example:
        get_cache_key('search', query='da-nang', page=1)
        → 'search:da-nang:1'
    """
    parts = [prefix]
    
    # Add positional args
    for arg in args:
        parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for key in sorted(kwargs.keys()):
        value = kwargs[key]
        if value is not None:
            parts.append(f"{key}:{value}")
    
    cache_key = ':'.join(parts)
    
    # Hash if too long (memcached has 250 char limit)
    if len(cache_key) > 200:
        hash_suffix = hashlib.md5(cache_key.encode()).hexdigest()[:8]
        cache_key = f"{prefix}:{hash_suffix}"
    
    return cache_key


def get_or_set_cache(key, callback, timeout=None):
    """
    Get value from cache, or compute and cache it
    
    Args:
        key: Cache key
        callback: Function to call if cache miss
        timeout: Cache timeout in seconds
        
    Example:
        def expensive_query():
            return Destination.objects.all()
        
        destinations = get_or_set_cache(
            'all_destinations',
            expensive_query,
            timeout=300
        )
    """
    # Try to get from cache
    value = cache.get(key)
    
    if value is not None:
        logger.debug(f"Cache HIT: {key}")
        return value
    
    # Cache miss - compute value
    logger.debug(f"Cache MISS: {key}")
    value = callback()
    
    # Store in cache
    if timeout is None:
        timeout = settings.CACHE_TTL.get('default', 300)
    
    cache.set(key, value, timeout)
    return value


def invalidate_cache(pattern=None, keys=None):
    """
    Invalidate cache by pattern or specific keys
    
    Args:
        pattern: Cache key pattern (e.g., 'search:*')
        keys: List of specific keys to delete
        
    Example:
        # Invalidate all search caches
        invalidate_cache(pattern='search:*')
        
        # Invalidate specific keys
        invalidate_cache(keys=['homepage', 'top_destinations'])
    """
    if keys:
        for key in keys:
            cache.delete(key)
            logger.info(f"Cache invalidated: {key}")
    
    if pattern:
        # Note: LocMemCache doesn't support pattern deletion
        # For production, use Redis with cache.delete_pattern(pattern)
        logger.warning(f"Pattern deletion not supported in LocMemCache: {pattern}")


def cache_page_custom(timeout=300, key_prefix='page'):
    """
    Decorator to cache entire view response
    
    Example:
        @cache_page_custom(timeout=600, key_prefix='destination')
        def destination_detail(request, id):
            ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Generate cache key from URL and query params
            cache_key = get_cache_key(
                key_prefix,
                request.path,
                request.GET.urlencode()
            )
            
            # Try cache
            response = cache.get(cache_key)
            if response is not None:
                logger.debug(f"Page cache HIT: {cache_key}")
                return response
            
            # Generate response
            logger.debug(f"Page cache MISS: {cache_key}")
            response = view_func(request, *args, **kwargs)
            
            # Cache response
            cache.set(cache_key, response, timeout)
            return response
        
        return wrapper
    return decorator


def get_cache_stats():
    """
    Get cache statistics (for debugging)
    
    Returns:
        dict: Cache stats
    """
    # Note: LocMemCache doesn't provide detailed stats
    # For production Redis, you can get hits/misses/size
    return {
        'backend': 'LocMemCache',
        'note': 'Detailed stats available with Redis backend'
    }
