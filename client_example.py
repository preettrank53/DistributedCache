"""
DistriCache Python Client Example
Demonstrates how to interact with the DistriCache system
"""
import requests
import json
from typing import Optional, Dict, Any
import asyncio
import httpx


class DistriCacheClient:
    """Simple client for DistriCache system"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of load balancer"""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
    
    def write(self, key: str, value: str, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Write data to cache"""
        payload = {
            "key": key,
            "value": value,
            "ttl": ttl
        }
        response = self.session.post(f"{self.base_url}/data", json=payload)
        return response.json()
    
    def read(self, key: str) -> str:
        """Read data from cache"""
        response = self.session.get(f"{self.base_url}/data/{key}")
        if response.status_code == 200:
            return response.json()["value"]
        elif response.status_code == 404:
            return None
        else:
            raise Exception(f"Error: {response.status_code}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cluster statistics"""
        response = self.session.get(f"{self.base_url}/cluster/stats")
        return response.json()
    
    def add_node(self, port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """Register a new cache node"""
        payload = {"port": port, "host": host}
        response = self.session.post(
            f"{self.base_url}/cluster/add-node",
            json=payload
        )
        return response.json()
    
    def remove_node(self, port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """Remove a cache node"""
        response = self.session.delete(
            f"{self.base_url}/cluster/remove-node/{port}",
            params={"host": host}
        )
        return response.json()
    
    def close(self):
        """Close the session"""
        self.session.close()


class AsyncDistriCacheClient:
    """Async client for DistriCache system"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of load balancer"""
        response = await self.client.get(f"{self.base_url}/health")
        return response.json()
    
    async def write(self, key: str, value: str, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Write data to cache"""
        payload = {
            "key": key,
            "value": value,
            "ttl": ttl
        }
        response = await self.client.post(f"{self.base_url}/data", json=payload)
        return response.json()
    
    async def read(self, key: str) -> Optional[str]:
        """Read data from cache"""
        response = await self.client.get(f"{self.base_url}/data/{key}")
        if response.status_code == 200:
            return response.json()["value"]
        elif response.status_code == 404:
            return None
        else:
            raise Exception(f"Error: {response.status_code}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cluster statistics"""
        response = await self.client.get(f"{self.base_url}/cluster/stats")
        return response.json()
    
    async def batch_write(self, items: Dict[str, str], ttl: Optional[int] = None) -> List[Dict]:
        """Write multiple items"""
        results = []
        for key, value in items.items():
            result = await self.write(key, value, ttl)
            results.append(result)
        return results
    
    async def batch_read(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Read multiple items"""
        results = {}
        for key in keys:
            results[key] = await self.read(key)
        return results


# Example Usage
def example_sync():
    """Example using synchronous client"""
    print("=" * 60)
    print("DistriCache - Synchronous Client Example")
    print("=" * 60)
    
    client = DistriCacheClient()
    
    try:
        # Health check
        print("\n1. Health Check:")
        health = client.health_check()
        print(json.dumps(health, indent=2))
        
        # Write data
        print("\n2. Writing Data:")
        result = client.write("user:123", "John Doe", ttl=3600)
        print(json.dumps(result, indent=2))
        
        # Read data
        print("\n3. Reading Data:")
        value = client.read("user:123")
        print(f"Value: {value}")
        
        # Get stats
        print("\n4. Cluster Statistics:")
        stats = client.get_stats()
        print(json.dumps(stats, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


async def example_async():
    """Example using asynchronous client"""
    print("\n" + "=" * 60)
    print("DistriCache - Asynchronous Client Example")
    print("=" * 60)
    
    async with AsyncDistriCacheClient() as client:
        try:
            # Health check
            print("\n1. Health Check:")
            health = await client.health_check()
            print(json.dumps(health, indent=2))
            
            # Batch write
            print("\n2. Batch Writing Data:")
            items = {
                "user:1": "Alice",
                "user:2": "Bob",
                "user:3": "Charlie"
            }
            results = await client.batch_write(items, ttl=3600)
            print(f"Written {len(results)} items")
            
            # Batch read
            print("\n3. Batch Reading Data:")
            keys = ["user:1", "user:2", "user:3"]
            values = await client.batch_read(keys)
            print(json.dumps(values, indent=2))
            
            # Get stats
            print("\n4. Cluster Statistics:")
            stats = await client.get_stats()
            if stats.get("ring_stats"):
                print(f"Nodes: {stats['ring_stats'].get('num_physical_nodes')}")
                print(f"Virtual Nodes: {stats['ring_stats'].get('num_virtual_nodes')}")
        
        except Exception as e:
            print(f"Error: {e}")


def example_direct_node():
    """Example accessing cache nodes directly"""
    print("\n" + "=" * 60)
    print("DistriCache - Direct Node Access Example")
    print("=" * 60)
    
    # Access a specific node directly
    session = requests.Session()
    
    try:
        # Health check
        print("\n1. Node Health Check:")
        response = session.get("http://127.0.0.1:8001/health")
        print(json.dumps(response.json(), indent=2))
        
        # Put data
        print("\n2. Put Data:")
        payload = {"key": "test:key", "value": "test:value", "ttl": 3600}
        response = session.post("http://127.0.0.1:8001/put", json=payload)
        print(json.dumps(response.json(), indent=2))
        
        # Get data
        print("\n3. Get Data:")
        response = session.get("http://127.0.0.1:8001/get/test:key")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        
        # Get stats
        print("\n4. Node Stats:")
        response = session.get("http://127.0.0.1:8001/stats")
        print(json.dumps(response.json(), indent=2))
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()


def example_load_test():
    """Example load test"""
    print("\n" + "=" * 60)
    print("DistriCache - Load Test Example")
    print("=" * 60)
    
    client = DistriCacheClient()
    
    try:
        print("\nRunning load test...")
        
        # Write 100 items
        print("Writing 100 items...")
        for i in range(100):
            client.write(f"load:test:{i}", f"value_{i}")
        
        # Read back
        print("Reading 100 items...")
        hits = 0
        for i in range(100):
            value = client.read(f"load:test:{i}")
            if value:
                hits += 1
        
        print(f"Hit rate: {hits}/100 = {hits}%")
        
        # Get stats
        stats = client.get_stats()
        print("\nCluster Stats:")
        if stats.get("ring_stats"):
            print(f"Physical nodes: {stats['ring_stats'].get('num_physical_nodes')}")
        
        if stats.get("node_stats"):
            for node_url, node_stat in stats["node_stats"].items():
                if isinstance(node_stat, dict) and "hits" in node_stat:
                    print(f"\n{node_url}:")
                    print(f"  Hits: {node_stat.get('hits')}")
                    print(f"  Misses: {node_stat.get('misses')}")
                    print(f"  Hit Rate: {node_stat.get('hit_rate')}%")
                    print(f"  Size: {node_stat.get('current_size')}/{node_stat.get('capacity')}")
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    from typing import List
    
    # Run examples
    print("\nMake sure DistriCache is running!")
    print("Run './run.sh' or 'run.bat' to start the system\n")
    
    try:
        # Synchronous example
        example_sync()
        
        # Direct node access example
        example_direct_node()
        
        # Asynchronous example
        print("\nRunning async example...")
        asyncio.run(example_async())
        
        # Load test
        example_load_test()
    
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to DistriCache")
        print("Make sure the system is running with './run.sh' or 'run.bat'")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
