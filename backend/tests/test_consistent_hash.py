"""
Unit tests for ConsistentHashRing implementation
"""
import pytest
from src.proxy.consistent_hash import ConsistentHashRing


class TestConsistentHashRing:
    """Test cases for ConsistentHashRing"""
    
    @pytest.fixture
    def ring(self):
        """Create a fresh hash ring for each test"""
        return ConsistentHashRing(num_virtual_nodes=150)
    
    def test_init(self):
        """Test ConsistentHashRing initialization"""
        ring = ConsistentHashRing(num_virtual_nodes=150)
        
        assert ring.num_virtual_nodes == 150
        assert len(ring.ring) == 0
        assert len(ring.nodes) == 0
    
    def test_add_single_node(self, ring):
        """Test adding a single node"""
        node_url = "http://localhost:8001"
        ring.add_node(node_url)
        
        assert node_url in ring.nodes
        # Due to hash collisions, the actual number might be less than virtual nodes
        # But it should be a significant percentage (at least 70%)
        assert len(ring.ring) >= 100  # At least ~67% of 150
    
    def test_add_multiple_nodes(self, ring):
        """Test adding multiple nodes"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        assert len(ring.nodes) == 3
        # Due to hash collisions, the actual number might be less
        # But should still be substantial (at least 55% of 450)
        assert len(ring.ring) >= 240  # At least ~55% of 450
    
    def test_add_duplicate_node(self, ring):
        """Test adding the same node twice"""
        node_url = "http://localhost:8001"
        
        ring.add_node(node_url)
        initial_ring_size = len(ring.ring)
        
        # Try to add same node again
        ring.add_node(node_url)
        
        # Ring size should remain the same
        assert len(ring.ring) == initial_ring_size
    
    def test_remove_node(self, ring):
        """Test removing a node"""
        node_url = "http://localhost:8001"
        ring.add_node(node_url)
        
        assert node_url in ring.nodes
        ring_size_before = len(ring.ring)
        assert ring_size_before > 0
        
        ring.remove_node(node_url)
        
        assert node_url not in ring.nodes
        assert len(ring.ring) == 0
    
    def test_remove_nonexistent_node(self, ring):
        """Test removing a node that doesn't exist"""
        node_url = "http://localhost:8001"
        
        # Should not raise an error
        ring.remove_node(node_url)
        
        assert node_url not in ring.nodes
    
    def test_get_node_single_node(self, ring):
        """Test get_node with single node"""
        node_url = "http://localhost:8001"
        ring.add_node(node_url)
        
        # Any key should map to this node
        assert ring.get_node("key1") == node_url
        assert ring.get_node("key2") == node_url
        assert ring.get_node("anybkey") == node_url
    
    def test_get_node_multiple_nodes(self, ring):
        """Test get_node with multiple nodes"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        # Get nodes for various keys
        node1 = ring.get_node("key1")
        node2 = ring.get_node("key2")
        node3 = ring.get_node("key3")
        
        # All should be valid nodes
        assert node1 in nodes
        assert node2 in nodes
        assert node3 in nodes
    
    def test_get_node_consistency(self, ring):
        """Test that get_node returns consistent results"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        # Same key should always map to same node
        node1 = ring.get_node("consistent_key")
        node2 = ring.get_node("consistent_key")
        node3 = ring.get_node("consistent_key")
        
        assert node1 == node2 == node3
    
    def test_get_node_empty_ring(self, ring):
        """Test get_node with empty ring"""
        result = ring.get_node("any_key")
        assert result is None
    
    def test_get_nodes_single_node(self, ring):
        """Test get_nodes with single node"""
        node_url = "http://localhost:8001"
        ring.add_node(node_url)
        
        nodes = ring.get_nodes("key1", count=3)
        
        assert len(nodes) == 1
        assert nodes[0] == node_url
    
    def test_get_nodes_multiple_nodes(self, ring):
        """Test get_nodes with multiple nodes"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        # Get 2 nodes for replication
        result_nodes = ring.get_nodes("key1", count=2)
        
        assert len(result_nodes) <= 2
        assert all(node in nodes for node in result_nodes)
    
    def test_get_nodes_count_exceeds_physical_nodes(self, ring):
        """Test get_nodes when count exceeds number of physical nodes"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        # Request more nodes than exist
        result_nodes = ring.get_nodes("key1", count=5)
        
        assert len(result_nodes) == 2  # Should only return 2
    
    def test_hash_consistency(self, ring):
        """Test that hash function produces consistent results"""
        key = "test_key"
        hash1 = ring._hash(key)
        hash2 = ring._hash(key)
        
        assert hash1 == hash2
        assert 0 <= hash1 < 360
    
    def test_node_redistribution(self, ring):
        """Test that adding a node doesn't completely redistribute all keys"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        # Get initial node assignments for various keys
        initial_assignments = {}
        test_keys = [f"key{i}" for i in range(100)]
        
        for key in test_keys:
            initial_assignments[key] = ring.get_node(key)
        
        # Add a new node
        ring.add_node("http://localhost:8003")
        
        # Check how many keys got reassigned
        reassigned_count = 0
        for key in test_keys:
            if ring.get_node(key) != initial_assignments[key]:
                reassigned_count += 1
        
        # Most keys should remain on their original node
        # (with 150 virtual nodes, roughly 1/3 should move)
        assert reassigned_count >= 20  # At least some redistribution
        assert reassigned_count <= 50  # But not too much
    
    def test_ring_stats(self, ring):
        """Test get_ring_stats method"""
        nodes = [
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003"
        ]
        
        for node in nodes:
            ring.add_node(node)
        
        stats = ring.get_ring_stats()
        
        assert stats["num_physical_nodes"] == 3
        # Due to hash collisions, actual might be less than 450
        # But should be substantial (at least 55%)
        assert stats["num_virtual_nodes"] >= 240
        assert len(stats["nodes"]) == 3
        assert stats["virtual_nodes_per_physical"] == 150


class TestConsistentHashRingEdgeCases:
    """Test edge cases for ConsistentHashRing"""
    
    def test_ring_with_one_virtual_node(self):
        """Test ring with minimal virtual nodes"""
        ring = ConsistentHashRing(num_virtual_nodes=1)
        
        ring.add_node("http://localhost:8001")
        assert len(ring.ring) == 1
    
    def test_ring_with_many_virtual_nodes(self):
        """Test ring with many virtual nodes"""
        ring = ConsistentHashRing(num_virtual_nodes=1000)
        
        ring.add_node("http://localhost:8001")
        # With 1000 virtual nodes in 360-degree hash space,
        # heavy collisions expected. Just verify we get some nodes.
        assert len(ring.ring) > 300  # Some meaningful percentage
    
    def test_node_url_with_special_characters(self):
        """Test node URLs with special characters"""
        ring = ConsistentHashRing()
        
        node_url = "http://cache-node-1.internal:8001"
        ring.add_node(node_url)
        
        assert ring.get_node("key1") == node_url
    
    def test_get_node_with_empty_string_key(self):
        """Test get_node with empty string key"""
        ring = ConsistentHashRing()
        ring.add_node("http://localhost:8001")
        
        node = ring.get_node("")
        assert node == "http://localhost:8001"
    
    def test_hash_range_validation(self):
        """Verify hash values are in valid range"""
        ring = ConsistentHashRing()
        
        test_keys = ["key1", "key2", "key999", "!@#$", "🚀"]
        
        for key in test_keys:
            hash_val = ring._hash(key)
            assert 0 <= hash_val < 360, f"Hash value {hash_val} out of range for key {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
