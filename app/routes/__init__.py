"""
Agent Ethos - API Routes
"""
from fastapi import APIRouter

from app.routes.agents import router as agents_router
from app.routes.vouches import router as vouches_router
from app.routes.leaderboard import router as leaderboard_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(vouches_router, prefix="/vouches", tags=["Vouches"])
api_router.include_router(leaderboard_router, prefix="/leaderboard", tags=["Leaderboard"])

