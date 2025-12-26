"""
Load Balancer / Proxy API for DistriCache
Routes requests to appropriate cache nodes using Consistent Hashing
"""
import argparse
import httpx
import logging
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import asyncio
import subprocess
import sys
import os
import random
import time

from src.proxy.consistent_hash import ConsistentHashRing
from src.database.db import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models
class DataRequest(BaseModel):
    """Request model for POST /data endpoint"""
    key: str
    value: str
    ttl: Optional[int] = None


class DataResponse(BaseModel):
    """Response model for GET /data endpoint"""
    key: str
    value: str
    source: str  # "cache" or "database"
    latency_ms: Optional[float] = None  # Response time in milliseconds


class NodeRegisterRequest(BaseModel):
    """Request model for adding nodes to the cluster"""
    port: int
    host: str = "127.0.0.1"


class NodeStats(BaseModel):
    """Statistics from a cache node"""
    hits: int
    misses: int
    hit_rate: float
    current_size: int
    capacity: int


# Initialize FastAPI app
app = FastAPI(title="DistriCache Load Balancer", version="1.0.0")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
hash_ring: Optional[ConsistentHashRing] = None
db_manager: Optional[DatabaseManager] = None
http_client: Optional[httpx.AsyncClient] = None
chaos_monkey_task: Optional[asyncio.Task] = None
chaos_monkey_enabled: bool = False
partition_map: dict[str, set[str]] = {}  # Network partition blacklist: {source_port: {blocked_ports}}


class ChaosMonkey:
    """
    Chaos Monkey service for fault tolerance testing.
    Randomly kills cache nodes to demonstrate system resilience.
    """
    
    def __init__(self, min_nodes: int = 3, interval_min: int = 5, interval_max: int = 8):
        """
        Initialize Chaos Monkey.
        
        Args:
            min_nodes: Minimum nodes to keep alive (safety check)
            interval_min: Minimum seconds between destructions
            interval_max: Maximum seconds between destructions
        """
        self.min_nodes = min_nodes
        self.interval_min = interval_min
        self.interval_max = interval_max
        self.is_running = False
        
    async def destruction_loop(self) -> None:
        """
        Main chaos loop: randomly kills nodes at random intervals.
        """
        logger.warning("🔥 CHAOS MONKEY UNLEASHED! 🔥")
        
        while self.is_running:
            try:
                # Random interval between destructions
                wait_time = random.randint(self.interval_min, self.interval_max)
                await asyncio.sleep(wait_time)
                
                if not self.is_running:
                    break
                
                # Safety check: ensure we have enough nodes
                if not hash_ring or len(hash_ring.nodes) <= self.min_nodes:
                    logger.warning(f"⚠️  CHAOS MONKEY: Only {len(hash_ring.nodes) if hash_ring else 0} nodes remaining. Sparing the cluster...")
                    continue
                
                # Select random victim
                victim_node = random.choice(list(hash_ring.nodes))
                port = victim_node.split(":")[-1]
                
                # Execute the destruction
                logger.error(f"💀 CHAOS MONKEY STRIKE! Killing node {port}")
                hash_ring.remove_node(victim_node)
                logger.info(f"💥 CRASH! Node {port} has been terminated. Remaining nodes: {len(hash_ring.nodes)}")
                
            except Exception as e:
                logger.error(f"Chaos Monkey error: {e}")
                
        logger.info("🛑 Chaos Monkey has been stopped")
    
    def start(self) -> None:
        """Start the chaos monkey."""
        self.is_running = True
        
    def stop(self) -> None:
        """Stop the chaos monkey."""
        self.is_running = False


# Initialize Chaos Monkey
chaos_monkey = ChaosMonkey(min_nodes=3, interval_min=5, interval_max=8)


def check_partition(source_node: str, target_node: str) -> bool:
    """
    Check if there's a network partition between two nodes.
    
    Args:
        source_node: Source node URL (e.g., "http://127.0.0.1:8001")
        target_node: Target node URL (e.g., "http://127.0.0.1:8002")
        
    Returns:
        True if partition exists (nodes cannot communicate), False otherwise
    """
    source_port = source_node.split(":")[-1]
    target_port = target_node.split(":")[-1]
    
    # Check both directions (bidirectional partition)
    source_blocked = target_port in partition_map.get(source_port, set())
    target_blocked = source_port in partition_map.get(target_port, set())
    
    return source_blocked or target_blocked


async def replicate_with_partition_check(node_url: str, payload: dict, operation: str = "put") -> tuple[bool, str]:
    """
    Attempt to replicate data to a node with partition checking.
    
    Args:
        node_url: Target node URL
        payload: Data to replicate
        operation: Operation type ("put" or "delete")
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if partition exists
    if check_partition("http://127.0.0.1:8000", node_url):
        port = node_url.split(":")[-1]
        return False, f"Network Unreachable (Partition) - Node {port}"
    
    try:
        endpoint = f"{node_url}/{operation}"
        if operation == "put":
            response = await http_client.post(endpoint, json=payload)
        elif operation == "delete":
            key = payload.get("key")
            response = await http_client.delete(f"{node_url}/delete/{key}")
        else:
            return False, f"Unknown operation: {operation}"
            
        if response.status_code == 200:
            return True, "Success"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"


async def init_components(db_path: str) -> None:
    """Initialize components"""
    global hash_ring, db_manager, http_client
    # Reduced virtual nodes for cleaner visualization (was 150)
    hash_ring = ConsistentHashRing(num_virtual_nodes=10)
    db_manager = DatabaseManager(db_path=db_path)
    http_client = httpx.AsyncClient(timeout=10.0)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize on startup"""
    await init_components(db_path="cache_db.sqlite")
    logger.info("Load Balancer started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown"""
    global http_client, chaos_monkey_task, chaos_monkey_enabled
    
    # Stop chaos monkey if running
    if chaos_monkey_enabled and chaos_monkey_task:
        chaos_monkey_enabled = False
        chaos_monkey.stop()
        chaos_monkey_task.cancel()
        try:
            await chaos_monkey_task
        except asyncio.CancelledError:
            pass
    
    if http_client:
        await http_client.aclose()


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "nodes": hash_ring.get_ring_stats() if hash_ring else {}
    }


@app.get("/cluster/map")
async def get_cluster_map() -> dict:
    """
    Returns the position of every node on the ring.
    Example Output: { "nodes": [ {"id": "http://localhost:8001", "angle": 45}, ... ] }
    """
    if not hash_ring:
        return {"nodes": []}
    return hash_ring.get_nodes_metadata()


@app.get("/data/{key}", response_model=DataResponse)
async def get_data(
    key: str,
    bypass_cache: bool = Query(False, description="Bypass cache and fetch directly from database (slow)")
) -> DataResponse:
    """
    Get data using Cache-Aside pattern with optional cache bypass for performance demos.
    
    1. Find responsible node using consistent hashing
    2. Try to get from cache node (unless bypass_cache=True)
    3. If miss or bypass, fetch from database and populate cache
    4. Return to user with latency metrics
    
    Args:
        key: The key to retrieve
        bypass_cache: If True, skip cache and fetch from DB (simulates slow path)
        
    Returns:
        DataResponse with key, value, source, and latency_ms
        
    Raises:
        HTTPException: If key not found or error occurs
    """
    start_time = time.time()
    
    if not hash_ring or not db_manager or not http_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Load balancer not initialized"
        )
    
    if not hash_ring.nodes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No cache nodes available"
        )
    
    # Get the node responsible for this key
    node_url = hash_ring.get_node(key)
    
    # BYPASS MODE: Force database fetch (slow path for demo)
    if bypass_cache:
        logger.warning(f"[BYPASS] Fetching '{key}' directly from database (simulated slow query)")
        
        # Simulate slow database query (300ms latency)
        await asyncio.sleep(0.3)
        
        db_value = db_manager.fetch_from_db(key)
        
        if db_value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key '{key}' not found in database"
            )
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Database fetch completed in {latency_ms:.2f}ms")
        
        return DataResponse(
            key=key,
            value=db_value,
            source="database",
            latency_ms=round(latency_ms, 2)
        )
    
    # NORMAL MODE: Try cache first (fast path)
    logger.info(f"Key '{key}' routed to node: {node_url}")
    
    # Try to get from cache node
    try:
        response = await http_client.get(f"{node_url}/get/{key}")
        if response.status_code == 200:
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Cache HIT for key '{key}' on node {node_url} ({latency_ms:.2f}ms)")
            return DataResponse(
                key=key,
                value=data["value"],
                source="cache",
                latency_ms=round(latency_ms, 2)
            )
    except Exception as e:
        logger.warning(f"Error reaching cache node {node_url}: {e}")
    
    # Cache miss: Fetch from database
    logger.info(f"Cache MISS for key '{key}', fetching from database")
    db_value = db_manager.fetch_from_db(key)
    
    if db_value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key '{key}' not found in database"
        )
    
    # Populate cache with the value (default TTL: 30 seconds for cache-miss refills)
    try:
        put_payload = {"key": key, "value": db_value, "ttl": 30}
        await http_client.post(f"{node_url}/put", json=put_payload)
        logger.info(f"Populated cache for key '{key}' on node {node_url} with TTL=30s")
    except Exception as e:
        logger.warning(f"Failed to populate cache: {e}")
    
    latency_ms = (time.time() - start_time) * 1000
    
    return DataResponse(
        key=key,
        value=db_value,
        source="database",
        latency_ms=round(latency_ms, 2)
    )


@app.post("/data")
async def post_data(request: DataRequest) -> dict:
    """
    Write data using Write-Through pattern.
    
    1. Write to database
    2. Invalidate/Update the key in cache node
    3. Return success
    
    Args:
        request: DataRequest with key, value, and optional ttl
        
    Returns:
        Dictionary with status
        
    Raises:
        HTTPException: If error occurs
    """
    if not hash_ring or not db_manager or not http_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Load balancer not initialized"
        )
    
    if not hash_ring.nodes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No cache nodes available"
        )
    
    # Write to database
    db_success = db_manager.save_to_db(request.key, request.value)
    if not db_success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write to database"
        )
    
    logger.info(f"Wrote key '{request.key}' to database")
    
    # Invalidate/Update in cache nodes (Replication Factor = 2)
    target_nodes = hash_ring.get_nodes(request.key, count=2)
    successful_nodes = []
    failed_replications = []

    put_payload = {
        "key": request.key,
        "value": request.value,
        "ttl": request.ttl
    }

    # Check if there's a partition between the replica nodes
    partition_blocks_replication = False
    if len(target_nodes) >= 2:
        partition_blocks_replication = check_partition(target_nodes[0], target_nodes[1])

    for node_url in target_nodes:
        # If partition exists between replicas, fail replication to second node
        if partition_blocks_replication and node_url == target_nodes[1]:
            port = node_url.split(":")[-1]
            logger.warning(f"❌ Replication BLOCKED for key '{request.key}' to node {port}: Network partition exists")
            failed_replications.append({"node": node_url, "port": port, "reason": "Network Unreachable (Partition)"})
            continue
            
        success, message = await replicate_with_partition_check(node_url, put_payload, "put")
        if success:
            logger.info(f"✅ Replicated key '{request.key}' to node {node_url}")
            successful_nodes.append(node_url)
        else:
            port = node_url.split(":")[-1]
            logger.warning(f"❌ Replication FAILED for key '{request.key}' to node {port}: {message}")
            failed_replications.append({"node": node_url, "port": port, "reason": message})
    
    return {
        "status": "success",
        "message": f"Key '{request.key}' written to database and replicated to {len(successful_nodes)}/{len(target_nodes)} nodes",
        "key": request.key,
        "ttl": request.ttl,
        "nodes": successful_nodes,
        "failed_replications": failed_replications  # Return failed replications for visualization
    }


@app.post("/cluster/add-node")
async def add_node(request: NodeRegisterRequest) -> dict:
    """
    Register a new cache node in the cluster.
    
    Args:
        request: NodeRegisterRequest with port and optional host
        
    Returns:
        Dictionary with status and ring statistics
    """
    if not hash_ring:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Load balancer not initialized"
        )
    
    node_url = f"http://{request.host}:{request.port}"
    
    # Verify node is reachable, if not, try to start it
    is_running = False
    if http_client:
        try:
            response = await http_client.get(f"{node_url}/health")
            if response.status_code == 200:
                is_running = True
        except Exception:
            pass # Node is not running

    if not is_running:
        # Only allow auto-starting local nodes
        if request.host not in ["127.0.0.1", "localhost"]:
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST, 
                 detail="Cannot auto-start remote nodes. Please start the node manually."
             )

        logger.info(f"Node {node_url} not running. Attempting to start...")
        try:
            # Spawn the node process
            cmd = [sys.executable, "-m", "src.nodes.server", "--port", str(request.port)]
            cwd = os.getcwd()
            logger.info(f"Spawning process: {' '.join(cmd)} in {cwd}")
            
            subprocess.Popen(
                cmd,
                cwd=cwd,
                # Detach process so it keeps running if LB restarts (platform dependent, keeping simple for now)
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            # Wait for node to become healthy
            logger.info(f"Waiting for node {request.port} to start...")
            max_retries = 10
            for i in range(max_retries):
                await asyncio.sleep(1)
                try:
                    response = await http_client.get(f"{node_url}/health")
                    if response.status_code == 200:
                        is_running = True
                        logger.info(f"Node {request.port} started successfully")
                        break
                except Exception:
                    continue
            
            if not is_running:
                 raise HTTPException(
                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                     detail=f"Failed to start node on port {request.port} (timeout)"
                 )
                 
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to spawn node process: {str(e)}"
            )
    
    # Add node to ring
    hash_ring.add_node(node_url)
    logger.info(f"Added node {node_url} to cluster")
    
    return {
        "status": "success",
        "message": f"Node {node_url} added to cluster",
        "node_url": node_url,
        "ring_stats": hash_ring.get_ring_stats()
    }


@app.delete("/cluster/remove-node/{port}")
async def remove_node(port: int, host: str = "127.0.0.1") -> dict:
    """
    Remove a cache node from the cluster.
    
    Args:
        port: Port of the node
        host: Host of the node (default: 127.0.0.1)
        
    Returns:
        Dictionary with status and ring statistics
    """
    if not hash_ring:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Load balancer not initialized"
        )
    
    node_url = f"http://{host}:{port}"
    
    if node_url not in hash_ring.nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_url} not found in cluster"
        )
    
    hash_ring.remove_node(node_url)
    logger.info(f"Removed node {node_url} from cluster")
    
    return {
        "status": "success",
        "message": f"Node {node_url} removed from cluster",
        "node_url": node_url,
        "ring_stats": hash_ring.get_ring_stats()
    }


@app.get("/cluster/stats")
async def cluster_stats() -> dict:
    """
    Get cluster statistics.
    
    Returns:
        Dictionary with cluster information
    """
    if not hash_ring or not http_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Load balancer not initialized"
        )
    
    ring_stats = hash_ring.get_ring_stats()
    node_stats = {}
    
    # Get stats from each node
    for node_url in hash_ring.nodes:
        try:
            response = await http_client.get(f"{node_url}/stats")
            if response.status_code == 200:
                node_stats[node_url] = response.json()
        except Exception as e:
            logger.warning(f"Failed to get stats from {node_url}: {e}")
            node_stats[node_url] = {"error": str(e)}
    
    return {
        "ring_stats": ring_stats,
        "node_stats": node_stats
    }


@app.get("/stats/global")
async def global_stats() -> dict:
    """
    Get aggregated global statistics for observability dashboard.
    Returns data optimized for charts and visualizations.
    
    Returns:
        dict: Global statistics including hit_rate, total_requests, node_load, request_distribution
    """
    if not hash_ring or not http_client:
        return {
            "hit_rate": 0.0,
            "total_requests": 0,
            "node_load": [],
            "request_distribution": [
                {"name": "Hits", "value": 0},
                {"name": "Misses", "value": 0}
            ]
        }
    
    total_hits = 0
    total_misses = 0
    node_load = []
    
    # Aggregate stats from all cache nodes
    for node_url in hash_ring.nodes:
        try:
            response = await http_client.get(f"{node_url}/stats")
            if response.status_code == 200:
                data = response.json()
                total_hits += data.get("hits", 0)
                total_misses += data.get("misses", 0)
                
                # Extract port number for cleaner display
                port = node_url.split(":")[-1]
                node_load.append({
                    "name": port,
                    "keys": data.get("current_size", 0)
                })
        except Exception as e:
            logger.warning(f"Failed to fetch stats from {node_url}: {e}")
    
    total_requests = total_hits + total_misses
    hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0
    
    # Sort node_load by port number for consistent chart display
    node_load.sort(key=lambda x: int(x["name"]))
    
    return {
        "hit_rate": round(hit_rate, 1),
        "total_requests": total_requests,
        "node_load": node_load,
        "request_distribution": [
            {"name": "Hits", "value": total_hits},
            {"name": "Misses", "value": total_misses}
        ]
    }


@app.get("/debug/keys")
async def get_all_keys() -> dict:
    """
    Get all active keys across all cache nodes with their TTL information.
    Aggregates keys from all nodes in the cluster.
    
    Returns:
        dict: List of all keys with their values and remaining TTL
    """
    if not hash_ring or not http_client:
        return {
            "keys": [],
            "total_keys": 0,
            "nodes_queried": 0
        }
    
    all_keys = []
    nodes_queried = 0
    seen_keys = set()  # Track unique keys to avoid duplicates from replication
    
    # Query all cache nodes
    for node_url in hash_ring.nodes:
        try:
            response = await http_client.get(f"{node_url}/debug/keys", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                nodes_queried += 1
                
                # Add keys from this node (avoid duplicates)
                for key_info in data.get("keys", []):
                    key_name = key_info["key"]
                    
                    # Only add if not seen before (deduplication for replicated keys)
                    if key_name not in seen_keys:
                        seen_keys.add(key_name)
                        
                        # Extract port number for node identification
                        port = node_url.split(":")[-1]
                        key_info["node"] = port
                        all_keys.append(key_info)
                    
        except Exception as e:
            logger.warning(f"Failed to fetch keys from {node_url}: {e}")
    
    # Sort by remaining TTL (shortest first) for better visualization
    all_keys_with_ttl = [k for k in all_keys if k["ttl_remaining"] is not None]
    all_keys_without_ttl = [k for k in all_keys if k["ttl_remaining"] is None]
    
    all_keys_with_ttl.sort(key=lambda x: x["ttl_remaining"])
    
    final_keys = all_keys_with_ttl + all_keys_without_ttl
    
    return {
        "keys": final_keys,
        "total_keys": len(final_keys),
        "nodes_queried": nodes_queried
    }


@app.post("/chaos/start")
async def start_chaos() -> dict:
    """
    Start the Chaos Monkey destruction loop.
    
    Returns:
        dict: Status message
    """
    global chaos_monkey_task, chaos_monkey_enabled
    
    if chaos_monkey_enabled:
        return {
            "status": "already_running",
            "message": "Chaos Monkey is already unleashed!"
        }
    
    if not hash_ring or len(hash_ring.nodes) <= chaos_monkey.min_nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start Chaos Monkey: Need more than {chaos_monkey.min_nodes} nodes in the cluster"
        )
    
    chaos_monkey_enabled = True
    chaos_monkey.start()
    chaos_monkey_task = asyncio.create_task(chaos_monkey.destruction_loop())
    
    logger.warning("🔥 CHAOS MODE ACTIVATED! 🔥")
    
    return {
        "status": "started",
        "message": "Chaos Monkey unleashed! Nodes will be randomly terminated.",
        "current_nodes": len(hash_ring.nodes),
        "min_nodes_threshold": chaos_monkey.min_nodes
    }


@app.post("/chaos/stop")
async def stop_chaos() -> dict:
    """
    Stop the Chaos Monkey destruction loop.
    
    Returns:
        dict: Status message
    """
    global chaos_monkey_task, chaos_monkey_enabled
    
    if not chaos_monkey_enabled:
        return {
            "status": "not_running",
            "message": "Chaos Monkey is not active"
        }
    
    chaos_monkey_enabled = False
    chaos_monkey.stop()
    
    if chaos_monkey_task:
        chaos_monkey_task.cancel()
        try:
            await chaos_monkey_task
        except asyncio.CancelledError:
            pass
        chaos_monkey_task = None
    
    logger.info("🛑 CHAOS MODE DEACTIVATED")
    
    return {
        "status": "stopped",
        "message": "Chaos Monkey has been stopped",
        "remaining_nodes": len(hash_ring.nodes) if hash_ring else 0
    }


@app.get("/chaos/status")
async def chaos_status() -> dict:
    """
    Get the current status of Chaos Monkey.
    
    Returns:
        dict: Status information
    """
    return {
        "enabled": chaos_monkey_enabled,
        "is_running": chaos_monkey.is_running,
        "current_nodes": len(hash_ring.nodes) if hash_ring else 0,
        "min_nodes_threshold": chaos_monkey.min_nodes,
        "can_start": hash_ring and len(hash_ring.nodes) > chaos_monkey.min_nodes
    }


# ============================================================================
# NETWORK PARTITION ENDPOINTS
# ============================================================================

@app.post("/partition/create")
async def create_partition(source_port: str, target_port: str) -> dict:
    """
    Create a network partition between two nodes (bidirectional).
    
    Args:
        source_port: Port of source node (e.g., "8001")
        target_port: Port of target node (e.g., "8002")
        
    Returns:
        dict: Status message
    """
    global partition_map
    
    # Initialize sets if needed
    if source_port not in partition_map:
        partition_map[source_port] = set()
    if target_port not in partition_map:
        partition_map[target_port] = set()
    
    # Create bidirectional partition
    partition_map[source_port].add(target_port)
    partition_map[target_port].add(source_port)
    
    logger.warning(f"⚡ NETWORK PARTITION CREATED: {source_port} <--X--> {target_port}")
    
    return {
        "status": "success",
        "message": f"Network partition created between nodes {source_port} and {target_port}",
        "partition": f"{source_port}<--X-->{target_port}"
    }


@app.post("/partition/remove")
async def remove_partition(source_port: str, target_port: str) -> dict:
    """
    Remove a network partition between two nodes.
    
    Args:
        source_port: Port of source node (e.g., "8001")
        target_port: Port of target node (e.g., "8002")
        
    Returns:
        dict: Status message
    """
    global partition_map
    
    removed = False
    
    # Remove bidirectional partition
    if source_port in partition_map and target_port in partition_map[source_port]:
        partition_map[source_port].remove(target_port)
        removed = True
    
    if target_port in partition_map and source_port in partition_map[target_port]:
        partition_map[target_port].remove(source_port)
        removed = True
    
    if removed:
        logger.info(f"✅ NETWORK PARTITION REMOVED: {source_port} <--> {target_port}")
        return {
            "status": "success",
            "message": f"Network partition removed between nodes {source_port} and {target_port}"
        }
    else:
        return {
            "status": "not_found",
            "message": f"No partition exists between nodes {source_port} and {target_port}"
        }


@app.get("/partition/list")
async def list_partitions() -> dict:
    """
    List all active network partitions.
    
    Returns:
        dict: List of all partitions
    """
    partitions = []
    seen = set()
    
    for source_port, blocked_ports in partition_map.items():
        for target_port in blocked_ports:
            # Avoid duplicates (since partitions are bidirectional)
            pair = tuple(sorted([source_port, target_port]))
            if pair not in seen:
                seen.add(pair)
                partitions.append({
                    "source": source_port,
                    "target": target_port,
                    "bidirectional": True
                })
    
    return {
        "partitions": partitions,
        "count": len(partitions)
    }


@app.post("/partition/clear")
async def clear_all_partitions() -> dict:
    """
    Clear all network partitions.
    
    Returns:
        dict: Status message
    """
    global partition_map
    count = len(partition_map)
    partition_map = {}
    
    logger.info(f"🔧 All network partitions cleared ({count} nodes affected)")
    
    return {
        "status": "success",
        "message": f"All network partitions cleared",
        "affected_nodes": count
    }


def main() -> None:
    """Main entry point for the load balancer"""
    parser = argparse.ArgumentParser(description="DistriCache Load Balancer")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the load balancer on (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="cache_db.sqlite",
        help="Path to SQLite database (default: cache_db.sqlite)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting Load Balancer on {args.host}:{args.port}")
    logger.info(f"Database: {args.db}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
