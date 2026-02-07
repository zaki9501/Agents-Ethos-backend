"""
Agent Ethos - Leaderboard Routes
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Agent
from app.models.agent import AgentPublic

router = APIRouter()


@router.get(
    "",
    response_model=dict,
    summary="Get reputation leaderboard",
    description="Get the top agents sorted by reputation score."
)
async def get_leaderboard(
    limit: int = Query(50, ge=1, le=100, description="Max agents to return"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get the reputation leaderboard.
    
    - **limit**: Maximum number of agents to return (default 50, max 100)
    
    Returns agents sorted by reputation score (highest first).
    """
    result = await session.execute(
        select(Agent)
        .order_by(Agent.reputation.desc(), Agent.created_at.asc())
        .limit(limit)
    )
    agents = result.scalars().all()
    
    leaderboard = [
        AgentPublic(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            reputation=agent.reputation,
            is_claimed=agent.is_claimed,
            created_at=agent.created_at,
        )
        for agent in agents
    ]
    
    return {
        "success": True,
        "leaderboard": leaderboard,
    }

