"""
Agent Ethos - Agent Model
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Index


class AgentBase(SQLModel):
    """Base agent fields."""
    name: str = Field(
        max_length=100,
        description="Unique agent name (case-insensitive)"
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Agent description"
    )


class Agent(AgentBase, table=True):
    """Agent database model."""
    __tablename__ = "agents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    api_key_hash: str = Field(
        sa_column=Column(String(64), nullable=False),
        description="SHA-256 hash of API key"
    )
    reputation: int = Field(
        default=0,
        description="Cached reputation score"
    )
    is_claimed: bool = Field(
        default=False,
        description="Whether agent is claimed by human owner"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Registration timestamp"
    )
    
    __table_args__ = (
        Index("ix_agents_name_lower", "name"),
    )


class AgentCreate(AgentBase):
    """Schema for agent registration."""
    pass


class AgentPublic(AgentBase):
    """Public agent response (no sensitive data)."""
    id: int
    reputation: int
    is_claimed: bool
    created_at: datetime


class AgentRegisterResponse(SQLModel):
    """Response after successful registration."""
    success: bool = True
    agent: AgentPublic
    api_key: str  # Only returned once at registration

