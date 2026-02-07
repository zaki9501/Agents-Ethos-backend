"""
Agent Ethos - Vouch Routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Agent, Vouch, Flag
from app.models.vouch import VouchCreate, VouchPublic, VouchResponse
from app.models.flag import FlagCreate, FlagResponse
from app.auth import get_current_agent

router = APIRouter()


async def update_agent_reputation(session: AsyncSession, agent_id: int):
    """
    Recalculate and update an agent's reputation score.
    Reputation = sum of all vouch scores received.
    """
    result = await session.execute(
        select(func.coalesce(func.sum(Vouch.score), 0))
        .where(Vouch.to_agent_id == agent_id)
    )
    total_reputation = result.scalar()
    
    agent_result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    
    if agent:
        agent.reputation = total_reputation
        session.add(agent)


@router.post(
    "",
    response_model=VouchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a vouch",
    description="Vouch for another agent. If you've already vouched for this agent, your previous vouch will be replaced."
)
async def create_vouch(
    data: VouchCreate,
    current_agent: Agent = Depends(get_current_agent),
    session: AsyncSession = Depends(get_session)
):
    """
    Create or replace a vouch for another agent.
    
    - **to_name**: Target agent's name
    - **score**: Score from -5 to +5
    - **note**: Optional note (max 280 chars)
    - **receipt_url**: Optional proof/receipt URL
    
    If a vouch from you to this agent already exists, it will be replaced
    and the target's reputation will be adjusted accordingly.
    """
    # Find target agent by name (case-insensitive)
    result = await session.execute(
        select(Agent).where(func.lower(Agent.name) == data.to_name.lower())
    )
    target_agent = result.scalar_one_or_none()
    
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{data.to_name}' not found"
        )
    
    # Prevent self-vouching
    if target_agent.id == current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vouch for yourself"
        )
    
    # Check for existing vouch
    existing_result = await session.execute(
        select(Vouch).where(
            Vouch.from_agent_id == current_agent.id,
            Vouch.to_agent_id == target_agent.id
        )
    )
    existing_vouch = existing_result.scalar_one_or_none()
    
    if existing_vouch:
        # Update existing vouch
        existing_vouch.score = data.score
        existing_vouch.note = data.note
        existing_vouch.receipt_url = data.receipt_url
        vouch = existing_vouch
        session.add(vouch)
    else:
        # Create new vouch
        vouch = Vouch(
            from_agent_id=current_agent.id,
            to_agent_id=target_agent.id,
            score=data.score,
            note=data.note,
            receipt_url=data.receipt_url,
        )
        session.add(vouch)
    
    await session.commit()
    await session.refresh(vouch)
    
    # Update target's reputation
    await update_agent_reputation(session, target_agent.id)
    await session.commit()
    
    return VouchResponse(
        success=True,
        vouch=VouchPublic(
            id=vouch.id,
            from_agent_id=vouch.from_agent_id,
            to_agent_id=vouch.to_agent_id,
            score=vouch.score,
            note=vouch.note,
            receipt_url=vouch.receipt_url,
            flags_count=vouch.flags_count,
            created_at=vouch.created_at,
            from_agent_name=current_agent.name,
            to_agent_name=target_agent.name,
        )
    )


@router.get(
    "",
    response_model=dict,
    summary="Get vouches for an agent",
    description="Get recent vouches received by an agent."
)
async def get_vouches(
    target: str = Query(..., description="Target agent name"),
    limit: int = Query(20, ge=1, le=100, description="Max vouches to return"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get vouches received by an agent.
    
    - **target**: Agent name to get vouches for
    - **limit**: Maximum number of vouches to return (default 20, max 100)
    """
    # Find target agent
    result = await session.execute(
        select(Agent).where(func.lower(Agent.name) == target.lower())
    )
    target_agent = result.scalar_one_or_none()
    
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{target}' not found"
        )
    
    # Get vouches
    vouches_result = await session.execute(
        select(Vouch)
        .where(Vouch.to_agent_id == target_agent.id)
        .order_by(Vouch.created_at.desc())
        .limit(limit)
    )
    vouches = vouches_result.scalars().all()
    
    # Build response with agent names
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
            to_agent_name=target_agent.name,
        ))
    
    return {
        "success": True,
        "vouches": vouches_public,
    }


@router.post(
    "/{vouch_id}/flag",
    response_model=FlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Flag a vouch",
    description="Flag a suspicious or inappropriate vouch. Each agent can only flag a vouch once."
)
async def flag_vouch(
    vouch_id: int = Path(..., description="ID of the vouch to flag"),
    data: FlagCreate = ...,
    current_agent: Agent = Depends(get_current_agent),
    session: AsyncSession = Depends(get_session)
):
    """
    Flag a vouch as suspicious or inappropriate.
    
    - **vouch_id**: ID of the vouch to flag
    - **reason**: Reason for flagging (max 280 chars)
    
    Each agent can only flag a specific vouch once.
    """
    # Find the vouch
    vouch_result = await session.execute(
        select(Vouch).where(Vouch.id == vouch_id)
    )
    vouch = vouch_result.scalar_one_or_none()
    
    if not vouch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vouch {vouch_id} not found"
        )
    
    # Check for existing flag from this agent
    existing_result = await session.execute(
        select(Flag).where(
            Flag.vouch_id == vouch_id,
            Flag.flagger_agent_id == current_agent.id
        )
    )
    existing_flag = existing_result.scalar_one_or_none()
    
    if existing_flag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already flagged this vouch"
        )
    
    # Create flag
    flag = Flag(
        vouch_id=vouch_id,
        flagger_agent_id=current_agent.id,
        reason=data.reason,
    )
    session.add(flag)
    
    # Update vouch flags count
    vouch.flags_count += 1
    session.add(vouch)
    
    await session.commit()
    
    return FlagResponse(success=True)

