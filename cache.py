"""
Cache Manager Module
Phase 4: Advanced Features

Handles caching with Redis or in-memory fallback.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from functools import wraps

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
CACHE_TTL_DEFAULT = int(os.getenv("CACHE_TTL_SECONDS", 300))  # 5 minutes
REDIS_URL = os.getenv("REDIS_URL", "")


# =====================================================
# In-Memory Cache Store
# =====================================================

class MemoryCache:
    """
    Simple in-memory cache implementation.
    Used as fallback when Redis is not available.
    """
    
    def __init__(self):
        self._store: dict = {}
        self._expires: dict = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._store:
            return None
        
        # Check expiration
        if key in self._expires:
            if datetime.now() > self._expires[key]:
                self.delete(key)
                return None
        
        return self._store.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            self._store[key] = value
            if ttl:
                self._expires[key] = datetime.now() + timedelta(seconds=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._store:
            del self._store[key]
        if key in self._expires:
            del self._expires[key]
        return True
    
    def clear(self) -> bool:
        """Clear all cache."""
        self._store.clear()
        self._expires.clear()
        return True
    
    def keys(self, pattern: str = "*") -> list:
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self._store.keys())
        # Simple pattern matching
        import fnmatch
        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]


# =====================================================
# Redis Cache Store
# =====================================================

class RedisCache:
    """
    Redis-based cache implementation.
    """
    
    def __init__(self, url: str):
        self._client = None
        self._url = url
    
    @property
    def client(self):
        """Lazy load Redis client."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self._url)
                self._client.ping()  # Test connection
                logger.info("Redis connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._client = None
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if not self.client:
                return None
            
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if not self.client:
                return False
            
            serialized = json.dumps(value, default=str)
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.client:
                self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache."""
        try:
            if self.client:
                self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> list:
        """Get keys matching pattern."""
        try:
            if self.client:
                return [k.decode() for k in self.client.keys(pattern)]
            return []
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []


# =====================================================
# Cache Manager
# =====================================================

class CacheManager:
    """
    Unified cache manager with Redis/Memory fallback.
    """
    
    def __init__(self):
        self._backend = None
        self._backend_type = "memory"
    
    @property
    def backend(self):
        """Get or initialize cache backend."""
        if self._backend is None:
            if REDIS_URL:
                try:
                    self._backend = RedisCache(REDIS_URL)
                    # Test connection
                    if self._backend.client:
                        self._backend_type = "redis"
                        logger.info("Using Redis cache")
                    else:
                        raise Exception("Redis not available")
                except Exception:
                    self._backend = MemoryCache()
                    self._backend_type = "memory"
                    logger.info("Using in-memory cache (Redis fallback)")
            else:
                self._backend = MemoryCache()
                self._backend_type = "memory"
                logger.info("Using in-memory cache")
        return self._backend
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        return self.backend.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set cached value."""
        ttl = ttl or CACHE_TTL_DEFAULT
        return self.backend.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete cached value."""
        return self.backend.delete(key)
    
    def clear(self) -> bool:
        """Clear all cache."""
        return self.backend.clear()
    
    def get_or_set(
        self,
        key: str,
        getter: callable,
        ttl: int = None
    ) -> Any:
        """
        Get from cache or compute and store.
        
        Args:
            key: Cache key
            getter: Function to call if cache miss
            ttl: Time to live in seconds
            
        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = getter()
        self.set(key, value, ttl)
        return value
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "dashboard:*")
            
        Returns:
            Number of keys deleted
        """
        keys = self.backend.keys(pattern)
        for key in keys:
            self.delete(key)
        return len(keys)
    
    def status(self) -> dict:
        """Get cache status."""
        return {
            "backend": self._backend_type,
            "keys_count": len(self.backend.keys()) if hasattr(self.backend, 'keys') else 0
        }


# Singleton instance
cache = CacheManager()


# =====================================================
# Cache Decorators
# =====================================================

def cached(ttl: int = None, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(a) for a in args if a is not None)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def cache_invalidate(*patterns):
    """
    Decorator to invalidate cache after function execution.
    
    Args:
        patterns: Cache key patterns to invalidate
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate patterns
            for pattern in patterns:
                cache.invalidate_pattern(pattern)
            
            return result
        
        return wrapper
    return decorator


# =====================================================
# Cache Keys
# =====================================================

class CacheKeys:
    """
    Standard cache key definitions.
    """
    
    # Dashboard
    DASHBOARD_SUMMARY = "dashboard:summary:{date}"
    
    # Crew
    CREW_LIST = "crew:list"
    CREW_DETAIL = "crew:detail:{crew_id}"
    CREW_HOURS = "crew:hours:{date}"
    
    # Flights
    FLIGHTS = "flights:{date}"
    FLIGHT_DETAIL = "flights:detail:{flight_id}"
    
    # Standby
    STANDBY = "standby:{date}"
    
    # FTL
    FTL_SUMMARY = "ftl:summary:{date}"
    FTL_TOP_28D = "ftl:top28d:{date}"
    FTL_TOP_12M = "ftl:top12m"
    
    # Alerts
    ALERTS_ACTIVE = "alerts:active"
    
    @staticmethod
    def format(key: str, **kwargs) -> str:
        """Format key with parameters."""
        return key.format(**kwargs)


# =====================================================
# Test
# =====================================================

if __name__ == "__main__":
    print("="*60)
    print("Cache Manager Test")
    print("="*60)
    
    # Test cache operations
    print(f"\nCache Status: {cache.status()}")
    
    # Set and get
    cache.set("test:key", {"value": 123}, ttl=60)
    result = cache.get("test:key")
    print(f"Set/Get Test: {result}")
    
    # get_or_set
    def compute_value():
        return {"computed": True}
    
    result = cache.get_or_set("test:computed", compute_value, ttl=60)
    print(f"Get or Set Test: {result}")
    
    # Test decorator
    @cached(ttl=60, key_prefix="test")
    def expensive_function(x, y):
        return x + y
    
    result1 = expensive_function(1, 2)
    result2 = expensive_function(1, 2)  # Should be cached
    print(f"Cached Decorator Test: {result1 == result2}")
    
    # Clear
    cache.clear()
    print("Cache cleared")
    
    print("\nCache Manager initialized successfully!")
