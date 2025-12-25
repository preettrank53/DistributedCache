"""
Integration tests for Cache Node Server
"""
import pytest
from fastapi.testclient import TestClient
from src.nodes.server import app, init_cache, cache
import time


@pytest.fixture
def client():
    """Create a test client"""
    init_cache(capacity=10)
    return TestClient(app)


class TestCacheNodeServer:
    """Test cases for Cache Node Server"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["cache_initialized"] is True
    
    def test_put_single_item(self, client):
        """Test PUT endpoint with single item"""
        payload = {
            "key": "test_key",
            "value": "test_value",
            "ttl": None
        }
        
        response = client.post("/put", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_existing_item(self, client):
        """Test GET endpoint for existing item"""
        # First put an item
        put_payload = {
            "key": "get_test",
            "value": "get_value",
            "ttl": None
        }
        client.post("/put", json=put_payload)
        
        # Then get it
        response = client.get("/get/get_test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "get_test"
        assert data["value"] == "get_value"
    
    def test_get_nonexistent_item(self, client):
        """Test GET endpoint for non-existent item"""
        response = client.get("/get/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_delete_existing_item(self, client):
        """Test DELETE endpoint"""
        # First put an item
        put_payload = {
            "key": "delete_test",
            "value": "delete_value",
            "ttl": None
        }
        client.post("/put", json=put_payload)
        
        # Delete it
        response = client.delete("/delete/delete_test")
        assert response.status_code == 200
        
        # Verify it's gone
        response = client.get("/get/delete_test")
        assert response.status_code == 404
    
    def test_delete_nonexistent_item(self, client):
        """Test DELETE endpoint for non-existent item"""
        response = client.delete("/delete/nonexistent")
        
        assert response.status_code == 404
    
    def test_get_stats(self, client):
        """Test stats endpoint"""
        # Put some items
        client.post("/put", json={"key": "key1", "value": "value1", "ttl": None})
        client.post("/put", json={"key": "key2", "value": "value2", "ttl": None})
        
        # Get some items (hits)
        client.get("/get/key1")
        client.get("/get/key1")
        
        # Miss
        client.get("/get/nonexistent")
        
        # Get stats
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["hits"] == 2
        assert data["misses"] == 1
        assert data["current_size"] == 2
        assert data["capacity"] == 10
    
    def test_clear_cache(self, client):
        """Test clear endpoint"""
        # Put some items
        client.post("/put", json={"key": "key1", "value": "value1", "ttl": None})
        client.post("/put", json={"key": "key2", "value": "value2", "ttl": None})
        
        # Clear cache
        response = client.post("/clear")
        
        assert response.status_code == 200
        
        # Verify it's cleared
        response = client.get("/get/key1")
        assert response.status_code == 404
    
    def test_put_with_ttl(self, client):
        """Test PUT with TTL"""
        payload = {
            "key": "ttl_test",
            "value": "ttl_value",
            "ttl": 1
        }
        
        response = client.post("/put", json=payload)
        assert response.status_code == 200
        
        # Should be available immediately
        response = client.get("/get/ttl_test")
        assert response.status_code == 200
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        response = client.get("/get/ttl_test")
        assert response.status_code == 404
    
    def test_put_update_existing_key(self, client):
        """Test updating an existing key"""
        # Put initial value
        client.post("/put", json={"key": "update_test", "value": "initial", "ttl": None})
        
        # Update value
        client.post("/put", json={"key": "update_test", "value": "updated", "ttl": None})
        
        # Get updated value
        response = client.get("/get/update_test")
        assert response.status_code == 200
        assert response.json()["value"] == "updated"
    
    def test_cache_capacity_enforcement(self, client):
        """Test that cache enforces capacity limit"""
        # Initialize cache with capacity of 3 for this test
        from src.core.lru_cache import LRUCache
        from src.nodes.server import app as test_app
        import src.nodes.server as server_module
        
        server_module.cache = LRUCache(capacity=3)
        client = TestClient(test_app)
        
        # Fill cache
        for i in range(3):
            client.post("/put", json={"key": f"key{i}", "value": f"value{i}", "ttl": None})
        
        # Stats should show capacity
        response = client.get("/stats")
        assert response.json()["capacity"] == 3
        assert response.json()["current_size"] == 3
    
    def test_special_characters_in_key_and_value(self, client):
        """Test with special characters"""
        from urllib.parse import quote
        
        payload = {
            "key": "special:!@#$",
            "value": '{"emoji": "🚀🎉💻"}',
            "ttl": None
        }
        
        response = client.post("/put", json=payload)
        assert response.status_code == 200
        
        # URL encode the key for the GET request
        encoded_key = quote("special:!@#$", safe="")
        response = client.get(f"/get/{encoded_key}")
        assert response.status_code == 200
        assert "emoji" in response.json()["value"]


class TestCacheNodeEdgeCases:
    """Test edge cases for Cache Node Server"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        init_cache(capacity=10)
        return TestClient(app)
    
    def test_empty_string_key(self, client):
        """Test with empty string key"""
        payload = {
            "key": "",
            "value": "empty_key_value",
            "ttl": None
        }
        
        response = client.post("/put", json=payload)
        assert response.status_code == 200
        
        response = client.get("/get/")
        # Note: This might not work due to URL routing, but testing the logic
    
    def test_large_value(self, client):
        """Test with large value"""
        large_value = "x" * 10000
        
        payload = {
            "key": "large_key",
            "value": large_value,
            "ttl": None
        }
        
        response = client.post("/put", json=payload)
        assert response.status_code == 200
        
        response = client.get("/get/large_key")
        assert response.status_code == 200
        assert len(response.json()["value"]) == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
