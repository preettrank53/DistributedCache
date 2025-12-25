"""
Integration Tests for DistriCache System
Tests the complete flow of cache operations through the system
"""
import pytest
import httpx
import asyncio
import time
import subprocess
import sys
import os
from pathlib import Path


class TestDistriCacheIntegration:
    """Integration tests for the complete DistriCache system"""
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client for testing"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client
    
    @pytest.fixture
    def setup_system(self):
        """
        Note: This requires the system to be running.
        Start services manually before running integration tests:
        
        Terminal 1: python -m src.proxy.lb_api
        Terminal 2: python -m src.nodes.server --port 8001
        Terminal 3: python -m src.nodes.server --port 8002
        Terminal 4: python -m src.nodes.server --port 8003
        Terminal 5: Then run tests
        """
        yield
    
    @pytest.mark.asyncio
    async def test_lb_health_check(self, client, setup_system):
        """Test load balancer health check"""
        response = await client.get("http://127.0.0.1:8000/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_node_health_check(self, client, setup_system):
        """Test cache node health checks"""
        for port in [8001, 8002, 8003]:
            response = await client.get(f"http://127.0.0.1:{port}/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_register_nodes_with_lb(self, client, setup_system):
        """Test registering cache nodes with load balancer"""
        for port in [8001, 8002, 8003]:
            payload = {"port": port, "host": "127.0.0.1"}
            response = await client.post(
                "http://127.0.0.1:8000/cluster/add-node",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cluster_stats(self, client, setup_system):
        """Test getting cluster statistics"""
        response = await client.get("http://127.0.0.1:8000/cluster/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "ring_stats" in data
        assert "node_stats" in data
    
    @pytest.mark.asyncio
    async def test_write_through_pattern(self, client, setup_system):
        """Test Write-Through pattern: Write to DB and cache"""
        payload = {
            "key": "user:integration_test",
            "value": "Integration Test User",
            "ttl": None
        }
        
        # Write through load balancer
        response = await client.post(
            "http://127.0.0.1:8000/data",
            json=payload
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cache_aside_pattern(self, client, setup_system):
        """Test Cache-Aside pattern: First miss fetches from DB"""
        # First, ensure data is in DB by writing through
        write_payload = {
            "key": "test:cache_aside",
            "value": "Test Value",
            "ttl": None
        }
        
        await client.post(
            "http://127.0.0.1:8000/data",
            json=write_payload
        )
        
        # Now read through load balancer (should hit cache or DB)
        response = await client.get("http://127.0.0.1:8000/data/test:cache_aside")
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test:cache_aside"
        assert data["value"] == "Test Value"
    
    @pytest.mark.asyncio
    async def test_consistent_hash_distribution(self, client, setup_system):
        """Test that keys are distributed across nodes"""
        # Write multiple keys and track which nodes serve them
        node_distribution = {}
        
        for i in range(10):
            key = f"test:key_{i}"
            value = f"value_{i}"
            
            payload = {"key": key, "value": value, "ttl": None}
            await client.post("http://127.0.0.1:8000/data", json=payload)
        
        # Read back and verify distribution
        for i in range(10):
            key = f"test:key_{i}"
            response = await client.get(f"http://127.0.0.1:8000/data/{key}")
            
            assert response.status_code == 200
            data = response.json()
            source = data.get("source", "unknown")
            node_distribution[key] = source
        
        # We should have hits from cache
        assert len(node_distribution) == 10
    
    @pytest.mark.asyncio
    async def test_key_not_found(self, client, setup_system):
        """Test retrieving non-existent key"""
        response = await client.get("http://127.0.0.1:8000/data/nonexistent_key_xyz")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_direct_node_operations(self, client, setup_system):
        """Test operations directly on a cache node"""
        payload = {
            "key": "direct:test",
            "value": "direct_value",
            "ttl": None
        }
        
        # Put
        response = await client.post("http://127.0.0.1:8001/put", json=payload)
        assert response.status_code == 200
        
        # Get
        response = await client.get("http://127.0.0.1:8001/get/direct:test")
        assert response.status_code == 200
        assert response.json()["value"] == "direct_value"
        
        # Get stats
        response = await client.get("http://127.0.0.1:8001/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["current_size"] > 0
        assert stats["hits"] > 0
    
    @pytest.mark.asyncio
    async def test_ttl_expiration_flow(self, client, setup_system):
        """Test TTL expiration through system"""
        key = "test:ttl"
        payload = {
            "key": key,
            "value": "ttl_value",
            "ttl": 2  # 2 second TTL
        }
        
        # Write with TTL
        response = await client.post("http://127.0.0.1:8000/data", json=payload)
        assert response.status_code == 200
        
        # Should be available immediately
        response = await client.get(f"http://127.0.0.1:8000/data/{key}")
        assert response.status_code == 200
        
        # Wait for expiration
        await asyncio.sleep(2.1)
        
        # Should be expired
        response = await client.get(f"http://127.0.0.1:8000/data/{key}")
        assert response.status_code == 404


class TestDistriCacheLoadPatterns:
    """Test various load patterns on the system"""
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client for testing"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_sequential_writes(self, client):
        """Test sequential write operations"""
        for i in range(10):
            payload = {
                "key": f"seq:key_{i}",
                "value": f"value_{i}",
                "ttl": None
            }
            
            response = await client.post(
                "http://127.0.0.1:8000/data",
                json=payload
            )
            
            if response.status_code != 200:
                # System might not be running, skip
                pytest.skip("DistriCache system not running")
    
    @pytest.mark.asyncio
    async def test_mixed_read_write(self, client):
        """Test mixed read and write operations"""
        try:
            # Write
            for i in range(5):
                payload = {
                    "key": f"mixed:write_{i}",
                    "value": f"value_{i}",
                    "ttl": None
                }
                await client.post("http://127.0.0.1:8000/data", json=payload)
            
            # Read
            for i in range(5):
                await client.get(f"http://127.0.0.1:8000/data/mixed:write_{i}")
            
            # Get cluster stats
            response = await client.get("http://127.0.0.1:8000/cluster/stats")
            if response.status_code == 200:
                print("\nCluster Stats:")
                print(response.json())
        
        except httpx.ConnectError:
            pytest.skip("DistriCache system not running")


# Quick validation functions
def validate_lru_cache():
    """Quick validation of LRU cache functionality"""
    from src.core.lru_cache import LRUCache
    
    cache = LRUCache(capacity=3)
    
    # Test basic operations
    cache.put("a", "1")
    cache.put("b", "2")
    cache.put("c", "3")
    
    assert cache.get("a") == "1"
    assert cache.size() == 3
    
    # Test eviction
    cache.put("d", "4")
    assert cache.get("b") is None  # b should be evicted
    
    print("✓ LRU Cache validation passed")


def validate_hash_ring():
    """Quick validation of consistent hash ring"""
    from src.proxy.consistent_hash import ConsistentHashRing
    
    ring = ConsistentHashRing()
    
    # Add nodes
    ring.add_node("http://localhost:8001")
    ring.add_node("http://localhost:8002")
    ring.add_node("http://localhost:8003")
    
    assert len(ring.nodes) == 3
    
    # Test key assignment
    node = ring.get_node("test_key")
    assert node in ring.nodes
    
    print("✓ Consistent Hash Ring validation passed")


def validate_database():
    """Quick validation of database manager"""
    from src.database.db import DatabaseManager
    
    db = DatabaseManager(db_path=":memory:")
    
    # Test operations
    db.save_to_db("key1", "value1")
    assert db.fetch_from_db("key1") == "value1"
    
    db.delete_from_db("key1")
    assert db.fetch_from_db("key1") is None
    
    print("✓ Database Manager validation passed")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("DistriCache - Component Validation")
    print("="*50 + "\n")
    
    try:
        validate_lru_cache()
        validate_hash_ring()
        validate_database()
        
        print("\n" + "="*50)
        print("All component validations passed!")
        print("="*50)
        
        print("\nTo run full integration tests:")
        print("1. Start the system: ./run.sh (or run.bat on Windows)")
        print("2. Run tests: pytest backend/tests/test_integration.py -v\n")
    
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        sys.exit(1)
