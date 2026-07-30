"""Production database models using SQLModel."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy import text
import os

# Database URL from environment variable or default to SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zero_orchestrator.db")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


class User(SQLModel, table=True):
    """User model for authentication."""
    __tablename__ = "users"
    
    id: str = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VaultIntegration(SQLModel, table=True):
    """Integration vault model with multi-tenant support."""
    __tablename__ = "vault_integrations"
    
    id: str = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    type: str = Field(max_length=100)
    name: Optional[str] = Field(default=None, max_length=255)
    api_key: Optional[str] = Field(default=None, max_length=500)
    endpoint_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MCPToken(SQLModel, table=True):
    """MCP token model for authentication."""
    __tablename__ = "mcp_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True, max_length=100)
    user_id: str = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)


class APIKey(SQLModel, table=True):
    """Personal API key model for developer access."""
    __tablename__ = "api_keys"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    key_hash: str = Field(index=True, unique=True, max_length=255)
    key_prefix: str = Field(max_length=20)  # Store prefix for identification (e.g., "zo_live_...")
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)


class UserIntegration(SQLModel, table=True):
    """Custom user API integrations (e.g., Paystack, OpenAI, custom endpoints)."""
    __tablename__ = "user_integrations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    service_name: str = Field(max_length=100)
    encrypted_api_key: str = Field(max_length=500)
    config: Optional[str] = Field(default=None, max_length=1000)  # JSON string for additional config
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def init_db():
    """Initialize database and create tables."""
    SQLModel.metadata.create_all(engine)
    
    # Create indexes for better performance
    with Session(engine) as session:
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_vault_user_id ON vault_integrations(user_id)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_mcp_token_user_id ON mcp_tokens(user_id)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_api_key_user_id ON api_keys(user_id)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_integration_user_id ON user_integrations(user_id)"))
        session.commit()


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session
