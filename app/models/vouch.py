"""
Agent Ethos - Vouch Model
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, UniqueConstraint, Index


class VouchBase(SQLModel):
    """Base vouch fields."""
    score: int = Field(
        ge=-5,
        le=5,
        description="Vouch score from -5 to +5"
    )
    note: str = Field(
        default="",
        max_length=280,
        description="Optional note (max 280 chars)"
    )
    receipt_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional receipt/proof URL"
    )


class Vouch(VouchBase, table=True):
    """Vouch database model."""
    __tablename__ = "vouches"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    from_agent_id: int = Field(
        foreign_key="agents.id",
        description="Agent giving the vouch"
    )
    to_agent_id: int = Field(
        foreign_key="agents.id",
        description="Agent receiving the vouch"
    )
    flags_count: int = Field(
        default=0,
        description="Cached flag count"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Vouch timestamp"
    )
    
    __table_args__ = (
        UniqueConstraint("from_agent_id", "to_agent_id", name="uq_vouch_from_to"),
        Index("ix_vouches_to_agent", "to_agent_id"),
        Index("ix_vouches_from_agent", "from_agent_id"),
    )


class VouchCreate(SQLModel):
    """Schema for creating a vouch."""
    to_name: str = Field(description="Target agent name")
    score: int = Field(ge=-5, le=5, description="Score from -5 to +5")
    note: str = Field(default="", max_length=280)
    receipt_url: Optional[str] = Field(default=None, max_length=500)


class VouchPublic(VouchBase):
    """Public vouch response."""
    id: int
    from_agent_id: int
    to_agent_id: int
    flags_count: int
    created_at: datetime
    # Include agent names for convenience
    from_agent_name: Optional[str] = None
    to_agent_name: Optional[str] = None


class VouchResponse(SQLModel):
    """Vouch API response."""
    success: bool = True
    vouch: VouchPublic

