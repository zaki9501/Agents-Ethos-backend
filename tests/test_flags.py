"""
Agent Ethos - Flag Tests
"""
import pytest


@pytest.mark.asyncio
async def test_flag_vouch(client, registered_agent, second_agent, third_agent):
    """Test flagging a vouch."""
    # Create a vouch from first to second
    vouch_response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": 5, "note": "Great!"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    vouch_id = vouch_response.json()["vouch"]["id"]
    
    # Third agent flags the vouch
    response = await client.post(
        f"/api/v1/vouches/{vouch_id}/flag",
        json={"reason": "Suspicious activity"},
        headers={"Authorization": f"Bearer {third_agent['api_key']}"}
    )
    
    assert response.status_code == 201
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_duplicate_flag_prevented(client, registered_agent, second_agent, third_agent):
    """Test that duplicate flags are prevented."""
    # Create a vouch
    vouch_response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": 5, "note": "Great!"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    vouch_id = vouch_response.json()["vouch"]["id"]
    
    # First flag
    response = await client.post(
        f"/api/v1/vouches/{vouch_id}/flag",
        json={"reason": "Spam"},
        headers={"Authorization": f"Bearer {third_agent['api_key']}"}
    )
    assert response.status_code == 201
    
    # Duplicate flag should fail
    response = await client.post(
        f"/api/v1/vouches/{vouch_id}/flag",
        json={"reason": "Still spam"},
        headers={"Authorization": f"Bearer {third_agent['api_key']}"}
    )
    assert response.status_code == 409
    assert "already flagged" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_flag_increments_count(client, registered_agent, second_agent, third_agent):
    """Test that flagging increments the vouch's flag count."""
    # Create a vouch
    vouch_response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "second_agent", "score": 5, "note": "Great!"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    vouch_id = vouch_response.json()["vouch"]["id"]
    assert vouch_response.json()["vouch"]["flags_count"] == 0
    
    # Flag the vouch
    await client.post(
        f"/api/v1/vouches/{vouch_id}/flag",
        json={"reason": "Test"},
        headers={"Authorization": f"Bearer {third_agent['api_key']}"}
    )
    
    # Check flag count increased
    vouches = await client.get("/api/v1/vouches", params={"target": "second_agent"})
    assert vouches.json()["vouches"][0]["flags_count"] == 1


@pytest.mark.asyncio
async def test_flag_nonexistent_vouch(client, registered_agent):
    """Test flagging a non-existent vouch."""
    response = await client.post(
        "/api/v1/vouches/99999/flag",
        json={"reason": "Test"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_multiple_agents_can_flag(client, registered_agent, second_agent, third_agent):
    """Test that different agents can flag the same vouch."""
    # Create a vouch from first to third
    vouch_response = await client.post(
        "/api/v1/vouches",
        json={"to_name": "third_agent", "score": 5, "note": "Great!"},
        headers={"Authorization": f"Bearer {registered_agent['api_key']}"}
    )
    vouch_id = vouch_response.json()["vouch"]["id"]
    
    # Second agent flags
    response = await client.post(
        f"/api/v1/vouches/{vouch_id}/flag",
        json={"reason": "Reason 1"},
        headers={"Authorization": f"Bearer {second_agent['api_key']}"}
    )
    assert response.status_code == 201
    
    # Third agent (the recipient) can also flag
    response = await client.post(
        f"/api/v1/vouches/{vouch_id}/flag",
        json={"reason": "Reason 2"},
        headers={"Authorization": f"Bearer {third_agent['api_key']}"}
    )
    assert response.status_code == 201
    
    # Check flag count is 2
    vouches = await client.get("/api/v1/vouches", params={"target": "third_agent"})
    assert vouches.json()["vouches"][0]["flags_count"] == 2

