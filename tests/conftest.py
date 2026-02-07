"""
Agent Ethos - Test Configuration
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_session

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create test database session."""
    async_session_factory = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(async_engine):
    """Create test HTTP client with overridden database."""
    async_session_factory = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def override_get_session():
        async with async_session_factory() as session:
            yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_agent(client):
    """Create a registered agent and return agent data with API key."""
    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "test_agent", "description": "A test agent"}
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "agent": data["agent"],
        "api_key": data["api_key"],
    }


@pytest_asyncio.fixture
async def second_agent(client):
    """Create a second registered agent."""
    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "second_agent", "description": "Another test agent"}
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "agent": data["agent"],
        "api_key": data["api_key"],
    }


@pytest_asyncio.fixture
async def third_agent(client):
    """Create a third registered agent."""
    response = await client.post(
        "/api/v1/agents/register",
        json={"name": "third_agent", "description": "Third test agent"}
    )
    assert response.status_code == 201
    data = response.json()
    return {
        "agent": data["agent"],
        "api_key": data["api_key"],
    }

