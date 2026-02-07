"""
Agent Ethos - Leaderboard Tests
"""
import pytest


@pytest.mark.asyncio
async def test_leaderboard_empty(client):
    """Test leaderboard with no agents."""
    response = await client.get("/api/v1/leaderboard")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["leaderboard"] == []


@pytest.mark.asyncio
async def test_leaderboard_sorting(client, registered_agent, second_agent, third_agent):
    """Test that leaderboard is sorted by reputation descending."""
    # Give different reputations via vouches
    # second_agent vouches +5 for third_agent
    await client.post(
        "/api/v1/vouches",
        json={"to_name": "third_agent", "score": 5, "note": "Best!"},
        headers={"Authorization": f"Bearer {second_agent['api_key']}"}
    )
    
    # third_agent vouches +2 for test_agent
    await client.post(
        "/api/v1/vouches",
        json={"to_name": "test_agent", "score": 2, "note": "Good"},
        headers={"Authorization": f"Bearer {third_agent['api_key']}"}
    )
    
    # test_agent vouches -1 for second_agent
    await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": -1, "note": "Meh"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    # Expected order: third_agent (5), test_agent (2), second_agent (-1)
    response = await client.get("/api/v1/leaderboard")
    data = response.json()
    
    assert data["success"] is True
    assert len(data["leaderboard"]) == 3
    
    # Check order
    assert data["leaderboard"][0]["name"] == "third_agent"
    assert data["leaderboard"][0]["reputation"] == 5
    
    assert data["leaderboard"][1]["name"] == "test_agent"
    assert data["leaderboard"][1]["reputation"] == 2
    
    assert data["leaderboard"][2]["name"] == "second_agent"
    assert data["leaderboard"][2]["reputation"] == -1


@pytest.mark.asyncio
async def test_leaderboard_limit(client):
    """Test leaderboard respects limit parameter."""
    # Create multiple agents
    for i in range(10):
        await client.post(
            "/api/v1/agents/register",
            json={"name": f"agent_{i}", "description": f"Agent {i}"}
        )
    
    # Request with limit
    response = await client.get("/api/v1/leaderboard", params={"limit": 5})
    data = response.json()
    
    assert len(data["leaderboard"]) == 5


@pytest.mark.asyncio
async def test_leaderboard_includes_all_fields(client, registered_agent):
    """Test that leaderboard entries include all public fields."""
    response = await client.get("/api/v1/leaderboard")
    data = response.json()
    
    assert len(data["leaderboard"]) == 1
    agent = data["leaderboard"][0]
    
    assert "id" in agent
    assert "name" in agent
    assert "description" in agent
    assert "reputation" in agent
    assert "is_claimed" in agent
    assert "created_at" in agent
    
    # Should NOT include sensitive data
    assert "api_key_hash" not in agent

