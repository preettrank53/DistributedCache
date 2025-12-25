"""
Test Load Balancer API CORS and Map Endpoint
"""
import pytest
from fastapi.testclient import TestClient
from src.proxy.lb_api import app, init_components

@pytest.fixture
async def client():
    """Create a test client with initialized components"""
    await init_components(db_path=":memory:")
    return TestClient(app)

def test_cors_headers():
    """Test that CORS headers are present"""
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "GET" in response.headers["access-control-allow-methods"]

@pytest.mark.asyncio
async def test_cluster_map_endpoint():
    """Test the /cluster/map endpoint"""
    # Initialize components manually since we're not using the startup event in TestClient directly
    await init_components(db_path=":memory:")
    
    client = TestClient(app)
    
    # Add a node to the ring (via the global hash_ring initialized in init_components)
    from src.proxy.lb_api import hash_ring
    hash_ring.add_node("http://localhost:8001")
    
    response = client.get("/cluster/map")
    assert response.status_code == 200
    data = response.json()
    
    assert "nodes" in data
    assert len(data["nodes"]) > 0
    
    first_node = data["nodes"][0]
    assert "id" in first_node
    assert "angle" in first_node
    assert first_node["id"] == "http://localhost:8001"
