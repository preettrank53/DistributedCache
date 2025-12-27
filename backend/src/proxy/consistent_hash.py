"""
Consistent Hashing Ring Implementation for DistriCache
"""
import hashlib
from typing import Optional, List
from bisect import bisect_right


class ConsistentHashRing:
    """
    Consistent Hashing Ring for distributed cache nodes.
    
    Maps keys and nodes to a ring using MD5 hashing.
    Ensures minimal redistribution when nodes are added/removed.
    """
    
    def __init__(self, num_virtual_nodes: int = 5):
        """
        Initialize the Consistent Hash Ring.
        
        Args:
            num_virtual_nodes: Number of virtual nodes per physical node
                               (lower value = more visible variance, more realistic demo)
        """
        self.num_virtual_nodes = num_virtual_nodes
        self.ring: dict[int, str] = {}  # hash -> node_url
        self.sorted_keys: List[int] = []  # sorted hash values
        self.nodes: set[str] = set()  # physical nodes
    
    def _hash(self, key: str) -> int:
        """
        Hash a key using MD5 and map to range [0, 360].
        
        Args:
            key: The key to hash
            
        Returns:
            Hash value in range [0, 360]
        """
        hash_obj = hashlib.md5(key.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        return hash_int % 360
    
    def add_node(self, node_url: str) -> None:
        """
        Add a node to the hash ring.
        
        Creates virtual nodes for better distribution.
        
        Args:
            node_url: The URL of the node (e.g., 'http://localhost:8001')
        """
        if node_url in self.nodes:
            return  # Node already exists
        
        self.nodes.add(node_url)
        
        # Add virtual nodes
        for i in range(self.num_virtual_nodes):
            virtual_key = f"{node_url}:{i}"
            hash_value = self._hash(virtual_key)
            self.ring[hash_value] = node_url
        
        # Sort keys for binary search
        self._update_sorted_keys()
    
    def remove_node(self, node_url: str) -> None:
        """
        Remove a node from the hash ring.
        
        Args:
            node_url: The URL of the node to remove
        """
        if node_url not in self.nodes:
            return  # Node doesn't exist
        
        self.nodes.discard(node_url)
        
        # Remove all virtual nodes for this physical node
        keys_to_delete = [
            hash_value for hash_value, url in self.ring.items()
            if url == node_url
        ]
        
        for key in keys_to_delete:
            del self.ring[key]
        
        # Sort keys for binary search
        self._update_sorted_keys()
    
    def get_node(self, key: str) -> Optional[str]:
        """
        Get the node responsible for a given key.
        
        Uses consistent hashing to find the next node
        clockwise on the ring.
        
        Args:
            key: The key to find the node for
            
        Returns:
            The node URL, or None if no nodes exist
        """
        if not self.ring:
            return None
        
        hash_value = self._hash(key)
        
        # Find the first node with hash >= key's hash
        idx = bisect_right(self.sorted_keys, hash_value)
        
        # If no node found, wrap around to the first node
        if idx == len(self.sorted_keys):
            idx = 0
        
        return self.ring[self.sorted_keys[idx]]
    
    def get_nodes(self, key: str, count: int = 3) -> List[str]:
        """
        Get multiple nodes responsible for a given key.
        
        Useful for replication.
        
        Args:
            key: The key to find nodes for
            count: Number of nodes to return
            
        Returns:
            List of node URLs
        """
        if not self.ring:
            return []
        
        hash_value = self._hash(key)
        nodes = []
        idx = bisect_right(self.sorted_keys, hash_value)
        
        # Collect up to 'count' unique physical nodes
        seen = set()
        for _ in range(len(self.sorted_keys)):
            if idx == len(self.sorted_keys):
                idx = 0
            
            node_url = self.ring[self.sorted_keys[idx]]
            if node_url not in seen:
                nodes.append(node_url)
                seen.add(node_url)
                if len(nodes) == count:
                    break
            
            idx += 1
        
        return nodes
    
    def _update_sorted_keys(self) -> None:
        """Update sorted keys list for binary search."""
        self.sorted_keys = sorted(self.ring.keys())
    
    def get_ring_stats(self) -> dict:
        """
        Get statistics about the hash ring.
        
        Returns:
            Dictionary with ring information
        """
        return {
            "num_physical_nodes": len(self.nodes),
            "num_virtual_nodes": len(self.ring),
            "nodes": list(self.nodes),
            "virtual_nodes_per_physical": self.num_virtual_nodes
        }

    def get_nodes_metadata(self) -> dict:
        """
        Returns the position of every node on the ring.
        
        Returns:
            Dictionary with list of node positions
        """
        nodes_metadata = []
        for angle, node_url in self.ring.items():
            nodes_metadata.append({
                "id": node_url,
                "angle": angle
            })
        
        # Sort by angle for easier visualization
        nodes_metadata.sort(key=lambda x: x["angle"])
        
        return {"nodes": nodes_metadata}
