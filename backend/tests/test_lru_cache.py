"""
Unit tests for LRUCache implementation
"""
import pytest
import time
from src.core.lru_cache import LRUCache


class TestLRUCache:
    """Test cases for LRUCache"""
    
    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance for each test"""
        return LRUCache(capacity=3)
    
    def test_init_valid_capacity(self):
        """Test cache initialization with valid capacity"""
        cache = LRUCache(capacity=10)
        assert cache.capacity == 10
        assert cache.size() == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_init_invalid_capacity(self):
        """Test cache initialization with invalid capacity"""
        with pytest.raises(ValueError):
            LRUCache(capacity=0)
        
        with pytest.raises(ValueError):
            LRUCache(capacity=-1)
    
    def test_put_single_item(self, cache):
        """Test putting a single item in cache"""
        cache.put("key1", "value1")
        assert cache.size() == 1
        assert cache.get("key1") == "value1"
    
    def test_put_multiple_items(self, cache):
        """Test putting multiple items within capacity"""
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        assert cache.size() == 3
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_lru_eviction(self, cache):
        """Test that LRU item is evicted when capacity exceeded"""
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        # At capacity: key1, key2, key3
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add key4, should evict key2 (least recently used)
        cache.put("key4", "value4")
        
        assert cache.size() == 3
        assert cache.get("key2") is None  # key2 should be evicted
        assert cache.get("key1") == "value1"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_get_hit_and_miss(self, cache):
        """Test cache hit and miss statistics"""
        cache.put("key1", "value1")
        
        # First get - hit
        result = cache.get("key1")
        assert result == "value1"
        assert cache.hits == 1
        assert cache.misses == 0
        
        # Get non-existent - miss
        result = cache.get("nonexistent")
        assert result is None
        assert cache.hits == 1
        assert cache.misses == 1
    
    def test_delete_existing_key(self, cache):
        """Test deleting an existing key"""
        cache.put("key1", "value1")
        assert cache.size() == 1
        
        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.size() == 0
        assert cache.get("key1") is None
    
    def test_delete_nonexistent_key(self, cache):
        """Test deleting a non-existent key"""
        deleted = cache.delete("nonexistent")
        assert deleted is False
    
    def test_update_existing_key(self, cache):
        """Test updating an existing key"""
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.put("key1", "value1_updated")
        assert cache.size() == 1  # Should not increase size
        assert cache.get("key1") == "value1_updated"
    
    def test_ttl_expiration(self, cache):
        """Test TTL (Time To Live) expiration"""
        cache.put("key1", "value1", ttl=1)  # 1 second TTL
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get("key1") is None
    
    def test_ttl_no_expiration(self, cache):
        """Test that items without TTL don't expire"""
        cache.put("key1", "value1")  # No TTL
        
        # Should be available after delay
        time.sleep(0.5)
        assert cache.get("key1") == "value1"
    
    def test_clear_cache(self, cache):
        """Test clearing the cache"""
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # Create some stats
        
        assert cache.size() == 2
        assert cache.hits == 1
        
        cache.clear()
        
        assert cache.size() == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_get_stats(self, cache):
        """Test getting cache statistics"""
        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["current_size"] == 1
        assert stats["capacity"] == 3
        assert stats["hit_rate"] == 50.0
    
    def test_get_stats_no_requests(self, cache):
        """Test statistics with no requests"""
        stats = cache.get_stats()
        
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0
        assert stats["current_size"] == 0
    
    def test_lru_order_with_accesses(self, cache):
        """Test LRU order after multiple accesses"""
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        
        # Access pattern: a, b, a
        cache.get("a")
        cache.get("b")
        cache.get("a")
        
        # Add new item, should evict c (least recently used)
        cache.put("d", "4")
        
        assert cache.get("c") is None
        assert cache.get("a") == "1"
        assert cache.get("b") == "2"
        assert cache.get("d") == "4"


class TestLRUCacheEdgeCases:
    """Test edge cases for LRUCache"""
    
    def test_single_capacity_cache(self):
        """Test cache with capacity of 1"""
        cache = LRUCache(capacity=1)
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.put("key2", "value2")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_large_capacity_cache(self):
        """Test cache with large capacity"""
        cache = LRUCache(capacity=1000)
        
        for i in range(1000):
            cache.put(f"key{i}", f"value{i}")
        
        assert cache.size() == 1000
        assert cache.get("key0") == "value0"
        assert cache.get("key999") == "value999"
    
    def test_cache_with_none_values(self):
        """Test storing None values"""
        cache = LRUCache(capacity=5)
        
        # This should still work
        cache.put("key1", None)
        result = cache.get("key1")
        
        # get() returns None for non-existent keys, so we need to check if key exists
        assert "key1" in cache.cache
        assert cache.cache["key1"][0] is None
    
    def test_cache_with_empty_string_key(self):
        """Test cache with empty string as key"""
        cache = LRUCache(capacity=5)
        
        cache.put("", "empty_key_value")
        assert cache.get("") == "empty_key_value"
    
    def test_cache_with_special_characters(self):
        """Test cache with special characters in key and value"""
        cache = LRUCache(capacity=5)
        
        special_key = "!@#$%^&*()"
        special_value = "🚀🎉💻"
        
        cache.put(special_key, special_value)
        assert cache.get(special_key) == special_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
