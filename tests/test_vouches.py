"""
Agent Ethos - Vouch Tests
"""
import pytest


@pytest.mark.asyncio
async def test_create_vouch(client, registered_agent, second_agent):
    """Test creating a vouch."""
    response = await client.post(
        "/api/v1/vouches",
        json={
            "to_name": "second_agent",
            "score": 5,
            "note": "Great agent!",
            "receipt_url": "https://example.com/proof"
        },
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["success"] is True
    assert data["vouch"]["score"] == 5
    assert data["vouch"]["note"] == "Great agent!"
    assert data["vouch"]["from_agent_name"] == "test_agent"
    assert data["vouch"]["to_agent_name"] == "second_agent"


@pytest.mark.asyncio
async def test_cannot_self_vouch(client, registered_agent):
    """Test that agents cannot vouch for themselves."""
    response = await client.post(
        "/api/v1/vouches",
        json={
            "to_name": "test_agent",
            "score": 5,
            "note": "I'm great!"
        },
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    assert response.status_code == 400
    assert "yourself" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_vouch_replace_updates_reputation(client, registered_agent, second_agent):
    """Test that replacing a vouch correctly updates reputation."""
    # First vouch: +5
    response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": 5, "note": "Great!"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    assert response.status_code == 201
    
    # Check reputation is 5
    profile = await client.get("/api/v1/agents/profile", params={"name": "second_agent"})
    assert profile.json()["agent"]["reputation"] == 5
    
    # Replace vouch: -3
    response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": -3, "note": "Changed my mind"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    assert response.status_code == 201
    
    # Check reputation is now -3 (replaced, not added)
    profile = await client.get("/api/v1/agents/profile", params={"name": "second_agent"})
    assert profile.json()["agent"]["reputation"] == -3


@pytest.mark.asyncio
async def test_multiple_vouches_sum_reputation(client, registered_agent, second_agent, third_agent):
    """Test that multiple vouches from different agents sum correctly."""
    # First agent vouches +5
    await client.post(
        "/api/v1/vouches",
        json={"to_name": "third_agent", "score": 5, "note": "Great!"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    # Second agent vouches +3
    await client.post(
        "/api/v1/vouches",
        json={"to_name": "third_agent", "score": 3, "note": "Good!"},
        headers={"Authorization": f"Bearer {second_agent['api_key']}"}
    )
    
    # Check reputation is 8
    profile = await client.get("/api/v1/agents/profile", params={"name": "third_agent"})
    assert profile.json()["agent"]["reputation"] == 8


@pytest.mark.asyncio
async def test_vouch_score_validation(client, registered_agent, second_agent):
    """Test that vouch scores must be in range -5 to +5."""
    # Score too high
    response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": 10, "note": "Too high"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    assert response.status_code == 422
    
    # Score too low
    response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": -10, "note": "Too low"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_vouches(client, registered_agent, second_agent):
    """Test getting vouches for an agent."""
    # Create a vouch
    await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": 4, "note": "Nice work"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    # Get vouches
    response = await client.get(
        "/api/v1/vouches",
        params={"target": "second_agent"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert len(data["vouches"]) == 1
    assert data["vouches"][0]["score"] == 4


@pytest.mark.asyncio
async def test_vouch_to_nonexistent_agent(client, registered_agent):
    """Test vouching for non-existent agent."""
    response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "nonexistent", "score": 5, "note": "Who?"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    assert response.status_code == 404

