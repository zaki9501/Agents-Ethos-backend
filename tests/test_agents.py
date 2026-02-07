"""
Agent Ethos - Agent Tests
"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_register_agent(client):
    """Test agent registration."""
    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "new_agent", "description": "A new agent"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["success"] is True
    assert data["agent"]["name"] == "new_agent"
    assert data["agent"]["description"] == "A new agent"
    assert data["agent"]["reputation"] == 0
    assert "api_key" in data
    assert data["api_key"].startswith("ethos_sk_")


@pytest.mark.asyncio
async def test_register_unique_name(client, registered_agent):
    """Test that agent names must be unique."""
    # Try to register with same name
    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "test_agent", "description": "Duplicate"}
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_unique_name_case_insensitive(client, registered_agent):
    """Test that name uniqueness is case-insensitive."""
    # Try to register with same name but different case
    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "TEST_AGENT", "description": "Duplicate"}
    )
    
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_me(client, registered_agent):
    """Test getting current agent profile."""
    response = await client.get(
        "/api/v1/agents/me",
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["agent"]["name"] == "test_agent"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    """Test that /me requires authentication."""
    response = await client.get("/api/v1/agents/me")
    assert response.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_get_me_invalid_key(client):
    """Test that invalid API key is rejected."""
    response = await client.get(
        "/api/v1/agents/me",
        headers={"Authorization": "Bearer ethos_sk_invalid_key_here_1234567890123456789012345678901234567890"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client, registered_agent):
    """Test getting agent profile by name."""
    response = await client.get(
        "/api/v1/agents/profile",
        params={"name": "test_agent"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["agent"]["name"] == "test_agent"
    assert "recentVouches" in data


@pytest.mark.asyncio
async def test_get_profile_not_found(client):
    """Test profile lookup for non-existent agent."""
    response = await client.get(
        "/api/v1/agents/profile",
        params={"name": "nonexistent"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_profile_case_insensitive(client, registered_agent):
    """Test that profile lookup is case-insensitive."""
    response = await client.get(
        "/api/v1/agents/profile",
        params={"name": "TEST_AGENT"}
    )
    
    assert response.status_code == 200
    assert response.json()["agent"]["name"] == "test_agent"

