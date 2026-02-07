"""
Agent Ethos - Authentication & Security
"""
import secrets
import hashlib
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Agent

# Bearer token security scheme
security = HTTPBearer(
    scheme_name="API Key",
    description="Agent API key in format: ethos_sk_..."
)

# API key prefix
API_KEY_PREFIX = "ethos_sk_"


def generate_api_key() -> str:
    """
    Generate a secure API key.
    Format: ethos_sk_<32 random hex chars>
    """
    random_part = secrets.token_hex(32)
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash API key using SHA-256.
    
    Note: For MVP, SHA-256 is acceptable.
    TODO: Upgrade to argon2 for production.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key_format(api_key: str) -> bool:
    """Verify API key has correct format."""
    return api_key.startswith(API_KEY_PREFIX) and len(api_key) == len(API_KEY_PREFIX) + 64


async def get_agent_by_api_key(
    session: AsyncSession,
    api_key: str
) -> Optional[Agent]:
    """Look up agent by API key hash."""
    if not verify_api_key_format(api_key):
        return None
    
    key_hash = hash_api_key(api_key)
    result = await session.execute(
        select(Agent).where(Agent.api_key_hash == key_hash)
    )
    return result.scalar_one_or_none()


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Agent:
    """
    Dependency to get the current authenticated agent.
    Raises 401 if invalid or missing API key.
    """
    api_key = credentials.credentials
    
    agent = await get_agent_by_api_key(session, api_key)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return agent


async def get_optional_agent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    session: AsyncSession = Depends(get_session)
) -> Optional[Agent]:
    """
    Dependency to optionally get the current agent.
    Returns None if no valid API key provided.
    """
    if not credentials:
        return None
    
    return await get_agent_by_api_key(session, credentials.credentials)

