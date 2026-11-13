import time

# Simple in-memory TTL cache
_CACHE = {}

def cache_set(key: str, value: any, ttl_seconds: int = 300):
    """
    Store value with expiration time.
    """
    try:
        expire_time = time.time() + ttl_seconds
        _CACHE[key] = {
            "value": value,
            "expire_time": expire_time
        }
    except Exception as e:
        print(f"Error in cache_set: {e}")

def cache_get(key: str, return_expired_on_fail=False) -> any:
    """
    Retrieve value if not expired.
    If return_expired_on_fail is True, ignores TTL (useful as last-resort fallback).
    """
    try:
        if key not in _CACHE:
            return None
            
        item = _CACHE[key]
        if time.time() > item["expire_time"] and not return_expired_on_fail:
            return None
            
        return item["value"]
    except Exception as e:
        print(f"Error in cache_get: {e}")
        return None

def cache_clear():
    """Clear all cache."""
    _CACHE.clear()
