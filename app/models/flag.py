"""
Agent Ethos - Flag Model
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Index


class FlagBase(SQLModel):
    """Base flag fields."""
    reason: str = Field(
        max_length=280,
        description="Reason for flagging (max 280 chars)"
    )


class Flag(FlagBase, table=True):
    """Flag database model."""
    __tablename__ = "flags"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    vouch_id: int = Field(
        foreign_key="vouches.id",
        description="Flagged vouch"
    )
    flagger_agent_id: int = Field(
        foreign_key="agents.id",
        description="Agent who flagged"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Flag timestamp"
    )
    
    __table_args__ = (
        UniqueConstraint("vouch_id", "flagger_agent_id", name="uq_flag_vouch_flagger"),
        Index("ix_flags_vouch", "vouch_id"),
    )


class FlagCreate(SQLModel):
    """Schema for creating a flag."""
    reason: str = Field(max_length=280)


class FlagPublic(FlagBase):
    """Public flag response."""
    id: int
    vouch_id: int
    flagger_agent_id: int
    created_at: datetime
    flagger_name: Optional[str] = None


class FlagResponse(SQLModel):
    """Flag API response."""
    success: bool = True

