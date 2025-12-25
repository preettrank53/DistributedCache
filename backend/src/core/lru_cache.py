"""
LRU Cache Implementation using OrderedDict
"""
from collections import OrderedDict
from typing import Any, Optional
from datetime import datetime, timedelta
import time


class LRUCache:
    """
    Least Recently Used (LRU) Cache implementation.
    
    Uses OrderedDict to maintain insertion order and evict LRU items
    when capacity is reached.
    """
    
    def __init__(self, capacity: int = 100):
        """
        Initialize the LRU Cache.
        
        Args:
            capacity: Maximum number of items in the cache
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self.capacity = capacity
        self.cache: OrderedDict[str, tuple[Any, Optional[float]]] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value if found and not expired, None otherwise
        """
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, expiry = self.cache[key]
        
        # Check if expired
        if expiry is not None and time.time() > expiry:
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (mark as recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return value
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Put a value in the cache.
        
        Args:
            key: The key to store
            value: The value to store
            ttl: Time to live in seconds (None = no expiry)
        """
        # Calculate expiry time
        expiry = None
        if ttl is not None:
            expiry = time.time() + ttl
        
        # If key exists, remove it first to avoid duplicate entries
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.capacity:
            # Remove least recently used item (first item)
            self.cache.popitem(last=False)
        
        # Add the new item
        self.cache[key] = (value, expiry)
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.
        
        Args:
            key: The key to delete
            
        Returns:
            True if deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def size(self) -> int:
        """Get current number of items in cache."""
        return len(self.cache)
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hits, misses, and current size
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "current_size": self.size(),
            "capacity": self.capacity
        }
    
    def get_all_keys_with_ttl(self) -> list[dict]:
        """
        Get all keys with their values and remaining TTL.
        
        Returns:
            List of dictionaries with key, value, and ttl_remaining
        """
        current_time = time.time()
        keys_data = []
        
        for key, (value, expiry) in self.cache.items():
            # Skip expired keys
            if expiry is not None and current_time > expiry:
                continue
            
            # Calculate remaining TTL
            if expiry is not None:
                ttl_remaining = max(0, expiry - current_time)
            else:
                ttl_remaining = None  # No expiry
            
            keys_data.append({
                "key": key,
                "value": value,
                "ttl_remaining": round(ttl_remaining, 1) if ttl_remaining is not None else None
            })
        
        return keys_data
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired keys from the cache.
        
        Returns:
            Number of keys removed
        """
        current_time = time.time()
        expired_keys = []
        
        for key, (value, expiry) in self.cache.items():
            if expiry is not None and current_time > expiry:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
