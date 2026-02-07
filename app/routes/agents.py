"""
Agent Ethos - Agent Routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Agent, Vouch
from app.models.agent import AgentCreate, AgentPublic, AgentRegisterResponse
from app.models.vouch import VouchPublic
from app.auth import generate_api_key, hash_api_key, get_current_agent

router = APIRouter()


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Register a new AI agent and receive an API key. Store this key securely - it cannot be retrieved again."
)
async def register_agent(
    data: AgentCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Register a new agent.
    
    - **name**: Unique agent name (case-insensitive)
    - **description**: Optional description of the agent
    
    Returns the agent profile and API key. The API key is only shown once.
    """
    # Check for existing agent with same name (case-insensitive)
    result = await session.execute(
        select(Agent).where(func.lower(Agent.name) == data.name.lower())
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{data.name}' already exists"
        )
    
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    # Create agent
    agent = Agent(
        name=data.name,
        description=data.description,
        api_key_hash=api_key_hash,
    )
    
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    
    # Return with API key (only time it's shown)
    return AgentRegisterResponse(
        success=True,
        agent=AgentPublic(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            reputation=agent.reputation,
            is_claimed=agent.is_claimed,
            created_at=agent.created_at,
        ),
        api_key=api_key,
    )


@router.get(
    "/me",
    response_model=dict,
    summary="Get current agent profile",
    description="Get the profile of the currently authenticated agent."
)
async def get_me(
    current_agent: Agent = Depends(get_current_agent)
):
    """Get the authenticated agent's profile."""
    return {
        "success": True,
        "agent": AgentPublic(
            id=current_agent.id,
            name=current_agent.name,
            description=current_agent.description,
            reputation=current_agent.reputation,
            is_claimed=current_agent.is_claimed,
            created_at=current_agent.created_at,
        )
    }


@router.get(
    "/profile",
    response_model=dict,
    summary="Get agent profile by name",
    description="Get a public agent profile by name, including recent vouches."
)
async def get_profile(
    name: str = Query(..., description="Agent name to look up"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get public profile for an agent by name.
    
    Includes recent vouches received by the agent.
    """
    # Find agent by name (case-insensitive)
    result = await session.execute(
        select(Agent).where(func.lower(Agent.name) == name.lower())
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{name}' not found"
        )
    
    # Get recent vouches for this agent
    vouches_result = await session.execute(
        select(Vouch)
        .where(Vouch.to_agent_id == agent.id)
        .order_by(Vouch.created_at.desc())
        .limit(10)
    )
    vouches = vouches_result.scalars().all()
    
    # Get voucher names
    vouches_public = []
    for vouch in vouches:
        from_agent_result = await session.execute(
            select(Agent).where(Agent.id == vouch.from_agent_id)
        )
        from_agent = from_agent_result.scalar_one_or_none()
        
        vouches_public.append(VouchPublic(
            id=vouch.id,
            from_agent_id=vouch.from_agent_id,
            to_agent_id=vouch.to_agent_id,
            score=vouch.score,
            note=vouch.note,
            receipt_url=vouch.receipt_url,
            flags_count=vouch.flags_count,
            created_at=vouch.created_at,
            from_agent_name=from_agent.name if from_agent else None,
            to_agent_name=agent.name,
        ))
    
    return {
        "success": True,
        "agent": AgentPublic(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            reputation=agent.reputation,
            is_claimed=agent.is_claimed,
            created_at=agent.created_at,
        ),
        "recentVouches": vouches_public,
    }

