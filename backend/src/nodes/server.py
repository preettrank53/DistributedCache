"""
Cache Node Server - FastAPI application for individual cache nodes
"""
import argparse
import sys
import asyncio
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging

from src.core.lru_cache import LRUCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models
class PutRequest(BaseModel):
    """Request model for PUT endpoint"""
    key: str
    value: str
    ttl: Optional[int] = None  # Time to live in seconds


class CacheStats(BaseModel):
    """Response model for stats endpoint"""
    hits: int
    misses: int
    hit_rate: float
    current_size: int
    capacity: int


class GetResponse(BaseModel):
    """Response model for GET endpoint"""
    key: str
    value: str


# Initialize FastAPI app and LRU Cache
app = FastAPI(title="DistriCache Node", version="1.0.0")
cache: Optional[LRUCache] = None
cleanup_task: Optional[asyncio.Task] = None


def init_cache(capacity: int = 100) -> None:
    """Initialize the cache"""
    global cache
    cache = LRUCache(capacity=capacity)


async def background_cleanup() -> None:
    """Background task to periodically clean up expired keys"""
    while True:
        try:
            await asyncio.sleep(5)  # Run every 5 seconds
            if cache is not None:
                removed = cache.cleanup_expired()
                if removed > 0:
                    logger.info(f"Background cleanup: Removed {removed} expired keys")
        except asyncio.CancelledError:
            logger.info("Background cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background cleanup: {e}")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize cache on startup"""
    global cleanup_task
    if cache is None:
        init_cache()
    logger.info(f"Cache node started with capacity: {cache.capacity}")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(background_cleanup())
    logger.info("Started background cleanup task")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on shutdown"""
    global cleanup_task
    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("Cache node shutting down")



@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cache_initialized": cache is not None,
        "current_size": cache.size() if cache else 0
    }


@app.get("/get/{key}", response_model=GetResponse)
async def get_key(key: str) -> GetResponse:
    """
    Get a value from the cache.
    
    Args:
        key: The key to retrieve
        
    Returns:
        GetResponse with key and value
        
    Raises:
        HTTPException: 404 if key not found
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    value = cache.get(key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key '{key}' not found"
        )
    
    logger.info(f"Cache HIT for key: {key}")
    return GetResponse(key=key, value=value)


@app.post("/put")
async def put_key(request: PutRequest) -> dict:
    """
    Put a value in the cache.
    
    Args:
        request: PutRequest with key, value, and optional ttl
        
    Returns:
        Dictionary with status and message
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    cache.put(request.key, request.value, ttl=request.ttl)
    logger.info(f"Cache PUT for key: {request.key}, ttl: {request.ttl}")
    
    return {
        "status": "success",
        "message": f"Key '{request.key}' stored successfully",
        "ttl": request.ttl
    }


@app.delete("/delete/{key}")
async def delete_key(key: str) -> dict:
    """
    Delete a key from the cache.
    
    Args:
        key: The key to delete
        
    Returns:
        Dictionary with status
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    deleted = cache.delete(key)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key '{key}' not found"
        )
    
    logger.info(f"Cache DELETE for key: {key}")
    return {
        "status": "success",
        "message": f"Key '{key}' deleted successfully"
    }


@app.get("/stats", response_model=CacheStats)
async def get_stats() -> CacheStats:
    """
    Get cache statistics.
    
    Returns:
        CacheStats with hits, misses, hit_rate, and size information
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    stats = cache.get_stats()
    return CacheStats(**stats)


@app.post("/clear")
async def clear_cache() -> dict:
    """
    Clear all items from the cache.
    
    Returns:
        Dictionary with status
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    cache.clear()
    logger.info("Cache cleared")
    
    return {
        "status": "success",
        "message": "Cache cleared successfully"
    }


@app.get("/debug/keys")
async def get_all_keys() -> dict:
    """
    Get all keys with their values and remaining TTL.
    
    Returns:
        Dictionary with list of keys and their TTL information
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    keys_data = cache.get_all_keys_with_ttl()
    
    return {
        "keys": keys_data,
        "total_keys": len(keys_data)
    }


@app.post("/cleanup")
async def cleanup_expired_keys() -> dict:
    """
    Manually trigger cleanup of expired keys.
    
    Returns:
        Dictionary with number of keys removed
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache not initialized"
        )
    
    removed_count = cache.cleanup_expired()
    
    return {
        "status": "success",
        "removed_keys": removed_count,
        "message": f"Removed {removed_count} expired keys"
    }


def main() -> None:
    """Main entry point for the cache node server"""
    parser = argparse.ArgumentParser(description="DistriCache Node Server")
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to run the server on (default: 8001)"
    )
    parser.add_argument(
        "--capacity",
        type=int,
        default=100,
        help="Cache capacity (default: 100)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    
    # Initialize cache
    init_cache(capacity=args.capacity)
    
    logger.info(f"Starting Cache Node on {args.host}:{args.port}")
    logger.info(f"Cache capacity: {args.capacity}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
