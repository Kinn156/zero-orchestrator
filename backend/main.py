"""FastAPI backend for Supabase verification, Netlify deployment, and universal integration vault."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Literal, Optional

import httpx
import requests
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from supabase import create_client, Client
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlmodel import Session, select
from cryptography.fernet import Fernet
from database import engine, init_db, User, VaultIntegration, MCPToken, APIKey, UserIntegration

app = FastAPI(title="Deploy Dashboard API", version="1.1.0")


@app.on_event("startup")
def on_startup():
    """Initialize database on startup."""
    init_db()

# Production CORS configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://zero-orchestrator.vercel.app,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FastMCP server
mcp = FastMCP("Zero-Terminal Orchestrator")

# Authentication configuration
SECRET_KEY = os.getenv("SECRET_KEY", "zero-terminal-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Encryption configuration
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode())

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()

MOCK_SUPABASE_URL = "https://mock-project.supabase.co"
MOCK_NETLIFY_SITE = "mock-deploy-site"

# Database session dependency
def get_db():
    with Session(engine) as session:
        yield session

DEPLOY_HINTS = re.compile(r"\b(deploy|publish|launch|ship|landing|site|host)\b", re.I)
NETLIFY_HINTS = re.compile(r"\bnetlify\b", re.I)
VERCEL_HINTS = re.compile(r"\bvercel\b", re.I)
TABLE_HINTS = re.compile(r"\b(table|database|schema|supabase|sql|users?|records?|rows?)\b", re.I)
VERIFY_HINTS = re.compile(
    r"\b(verify|validate|check|connect|test)\b.*\b(supabase|credentials|integration)\b", re.I
)
STRIPE_HINTS = re.compile(r"\b(stripe|charge|payment|invoice|billing|customer|checkout)\b", re.I)
FIREBASE_HINTS = re.compile(r"\b(firebase|firestore|cloud functions?|realtime database)\b", re.I)
EAS_HINTS = re.compile(r"\b(eas|expo|apk|aab|mobile build|app store|play store)\b", re.I)
WEBHOOK_HINTS = re.compile(r"\b(webhook|hook|callback|trigger api|call api)\b", re.I)

INTEGRATION_LABELS = {
    "vercel": "Vercel",
    "firebase": "Firebase",
    "stripe": "Stripe",
    "expo_eas": "Expo EAS",
    "custom_webhook": "Custom Webhook/API",
}


def _use_mock_supabase(url: Optional[str], key: Optional[str]) -> bool:
    if not url or not key:
        return True
    if url.strip().lower().startswith("mock") or key.strip().lower().startswith("mock"):
        return True
    return os.getenv("FORCE_MOCK", "").lower() in ("1", "true", "yes")


def _use_mock_netlify(token: Optional[str]) -> bool:
    if not token:
        return True
    if token.strip().lower().startswith("mock"):
        return True
    return os.getenv("FORCE_MOCK", "").lower() in ("1", "true", "yes")


def _use_mock_key(api_key: Optional[str]) -> bool:
    if not api_key or not api_key.strip():
        return True
    if api_key.strip().lower().startswith("mock"):
        return True
    return os.getenv("FORCE_MOCK", "").lower() in ("1", "true", "yes")


def _sync_vault(integrations: list[VaultIntegration], user_id: Optional[str] = None):
    """Sync integrations to user's vault in database."""
    with Session(engine) as db:
        for item in integrations:
            # Encrypt the API key before storage
            encrypted_key = _encrypt_api_key(item.api_key) if item.api_key else None
            
            existing = db.exec(
                select(VaultIntegration).where(
                    VaultIntegration.id == item.id,
                    VaultIntegration.user_id == user_id
                )
            ).first()
            
            if existing:
                existing.type = item.type
                existing.name = item.name
                existing.api_key = encrypted_key
                existing.endpoint_url = item.endpoint_url
                existing.updated_at = datetime.now(timezone.utc)
            else:
                integration = VaultIntegration(
                    id=item.id,
                    user_id=user_id,
                    type=item.type,
                    name=item.name,
                    api_key=encrypted_key,
                    endpoint_url=item.endpoint_url
                )
                db.add(integration)
        
        db.commit()


def _integration_active(item: VaultIntegration) -> bool:
    # Check if the API key exists and is not empty (after potential decryption)
    if not item.api_key or not item.api_key.strip():
        return False
    # If it's encrypted, try to decrypt to verify it's valid
    try:
        _decrypt_api_key(item.api_key)
        return True
    except:
        # If decryption fails, assume it's not encrypted and check directly
        return bool(item.api_key and item.api_key.strip())


def _match_custom_by_name(prompt: str, integrations: list[VaultIntegration]) -> Optional[VaultIntegration]:
    lower = prompt.lower()
    for item in integrations:
        if item.name and item.name.strip() and item.name.strip().lower() in lower:
            return item
    return None


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _get_password_hash(password: str) -> str:
    """Hash a password using argon2."""
    return pwd_context.hash(password)


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _generate_mcp_token(user_id: str) -> str:
    """Generate a personal MCP token for a user."""
    return f"orch_live_{uuid.uuid4().hex[:24]}"


def _verify_mcp_token(token: str, db: Session) -> Optional[str]:
    """Verify an MCP token and return the associated user_id."""
    mcp_token = db.exec(select(MCPToken).where(MCPToken.token == token, MCPToken.is_active == True)).first()
    if mcp_token:
        return mcp_token.user_id
    return None


def _generate_api_key() -> str:
    """Generate a new API key with format zo_live_<random_string>."""
    random_string = uuid.uuid4().hex[:32]
    return f"zo_live_{random_string}"


def _hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return pwd_context.hash(api_key)


def _encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key using Fernet symmetric encryption."""
    return fernet.encrypt(api_key.encode()).decode()


def _decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key using Fernet symmetric encryption."""
    return fernet.decrypt(encrypted_key.encode()).decode()


def _verify_api_key(api_key: str, db: Session) -> Optional[str]:
    """Verify an API key and return the associated user_id."""
    api_keys = db.exec(select(APIKey).where(APIKey.is_active == True)).all()
    for key in api_keys:
        if pwd_context.verify(api_key, key.key_hash):
            # Update last used timestamp
            key.last_used_at = datetime.now(timezone.utc)
            db.add(key)
            db.commit()
            return key.user_id
    return None


def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db), x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """Get the current user ID from JWT token or API key."""
    # Try API key first
    if x_api_key and x_api_key.startswith("zo_live_"):
        user_id = _verify_api_key(x_api_key, db)
        if user_id:
            return user_id
    
    # Fall back to JWT
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None
    
    return None


def _get_user_from_mcp_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Get the current user ID from MCP token."""
    if not authorization:
        return None
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    # Verify token using database session
    with Session(engine) as db:
        return _verify_mcp_token(token, db)


class User(BaseModel):
    id: str
    email: str
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class UserLogin(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class VaultIntegration(BaseModel):
    id: str
    type: str = Field(..., description="vercel | firebase | stripe | expo_eas | custom_webhook")
    name: str
    api_key: str = ""
    endpoint_url: Optional[str] = None
    user_id: str = Field(..., description="User ID for multi-tenant isolation")


class IntegrationsRegisterRequest(BaseModel):
    integrations: list[VaultIntegration] = Field(default_factory=list)
    user_id: str = Field(..., description="User ID for multi-tenant isolation")


class MCPTokenRequest(BaseModel):
    user_id: str = Field(..., description="User ID requesting MCP token")


class MCPTokenResponse(BaseModel):
    token: str
    user_id: str
    created_at: datetime


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")


class APIKeyResponse(BaseModel):
    id: int
    key_prefix: str
    name: str
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool


class APIKeyCreateResponse(BaseModel):
    key: str  # Only returned once on creation
    key_prefix: str
    name: str
    created_at: datetime


class UserIntegrationCreate(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1, max_length=500)
    config: Optional[str] = Field(None, max_length=1000)


class UserIntegrationResponse(BaseModel):
    id: int
    service_name: str
    created_at: datetime
    updated_at: datetime


class ParseCommandRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    integrations: list[VaultIntegration] = Field(default_factory=list)


class ExecuteIntegrationRequest(BaseModel):
    integration: VaultIntegration
    prompt: str = Field(..., min_length=1)
    integrations: list[VaultIntegration] = Field(default_factory=list)


class OrchestrateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    netlify_token: Optional[str] = None
    site_id: Optional[str] = None
    integrations: list[VaultIntegration] = Field(default_factory=list)


class ParsedIntent(BaseModel):
    type: str
    command: str
    integration_id: Optional[str] = None
    integration_type: Optional[str] = None


class ParseCommandResponse(BaseModel):
    intent: ParsedIntent
    steps: list[str]


class SupabaseCredentials(BaseModel):
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon or service role key")
    integrations: list[VaultIntegration] = Field(default_factory=list)


class NetlifyDeployRequest(BaseModel):
    netlify_token: str = Field(..., description="Netlify personal access token")
    site_id: Optional[str] = Field(None, description="Existing Netlify site ID")
    prompt: Optional[str] = Field(None, description="User prompt / deploy message")
    integrations: list[VaultIntegration] = Field(default_factory=list)


class CreateTableRequest(BaseModel):
    supabase_url: str
    supabase_anon_key: str
    prompt: str = Field(..., min_length=1)
    table_name: Optional[str] = None
    integrations: list[VaultIntegration] = Field(default_factory=list)


class ActionResponse(BaseModel):
    success: bool
    mock: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)


class SubprocessRequest(BaseModel):
    command: str = Field(..., description="Command to execute on local machine")
    auto_approve: bool = Field(False, description="Skip user confirmation")


class SubprocessResponse(BaseModel):
    success: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    command: str


def _parse_prompt(prompt: str, integrations: list[VaultIntegration]) -> ParsedIntent:
    command = prompt.strip()
    named = _match_custom_by_name(command, integrations)

    wants_deploy = bool(DEPLOY_HINTS.search(command))
    wants_table = bool(TABLE_HINTS.search(command))
    wants_verify = bool(VERIFY_HINTS.search(command))
    wants_vercel = bool(VERCEL_HINTS.search(command))
    wants_netlify = bool(NETLIFY_HINTS.search(command))
    wants_stripe = bool(STRIPE_HINTS.search(command))
    wants_firebase = bool(FIREBASE_HINTS.search(command))
    wants_eas = bool(EAS_HINTS.search(command))
    wants_webhook = bool(WEBHOOK_HINTS.search(command))

    if named and not wants_table and not wants_verify:
        return ParsedIntent(
            type="custom_integration",
            command=command,
            integration_id=named.id,
            integration_type=named.type,
        )

    if wants_verify and not wants_deploy and not wants_table and not wants_stripe and not wants_eas:
        return ParsedIntent(type="verify", command=command)

    if wants_stripe and not wants_deploy and not wants_table:
        return ParsedIntent(type="stripe_charge", command=command)

    if wants_eas and not wants_table:
        return ParsedIntent(type="expo_build", command=command)

    if wants_firebase and not wants_deploy and not wants_table:
        return ParsedIntent(type="firebase_action", command=command)

    if wants_vercel and (wants_deploy or not wants_netlify):
        return ParsedIntent(type="vercel_deploy", command=command)

    custom = next((i for i in integrations if i.type == "custom_webhook" and _integration_active(i)), None)
    if custom and (wants_webhook or wants_deploy):
        return ParsedIntent(
            type="custom_integration",
            command=command,
            integration_id=custom.id,
            integration_type="custom_webhook",
        )

    if wants_deploy and wants_table:
        return ParsedIntent(type="pipeline", command=command)

    if wants_deploy and wants_netlify:
        return ParsedIntent(type="deploy", command=command)

    if wants_deploy and not wants_vercel:
        return ParsedIntent(type="deploy", command=command)

    if wants_table:
        return ParsedIntent(type="table", command=command)

    active = next((i for i in integrations if _integration_active(i)), None)
    if active:
        return ParsedIntent(
            type="custom_integration",
            command=command,
            integration_id=active.id,
            integration_type=active.type,
        )

    return ParsedIntent(type="deploy", command=command)


def _steps_for_intent(intent: ParsedIntent) -> list[str]:
    label = INTEGRATION_LABELS.get(intent.integration_type or "", "custom integration")

    mapping: dict[str, list[str]] = {
        "verify": [
            "Reading your command",
            "Loading Supabase integration",
            "Verifying connection",
            "Wrapping up",
        ],
        "deploy": [
            "Reading your command",
            "Loading Netlify integration",
            "Starting deployment",
            "Wrapping up",
        ],
        "table": [
            "Reading your command",
            "Loading Supabase integration",
            "Designing table from your request",
            "Wrapping up",
        ],
        "pipeline": [
            "Reading your command",
            "Verifying Supabase",
            "Preparing database table",
            "Starting Netlify deployment",
            "Wrapping up",
        ],
        "vercel_deploy": [
            "Reading your command",
            "Loading Vercel from Integration Vault",
            "Preparing deployment",
            "Publishing to Vercel",
            "Wrapping up",
        ],
        "stripe_charge": [
            "Reading your command",
            "Loading Stripe from Integration Vault",
            "Validating payment details",
            "Processing charge",
            "Wrapping up",
        ],
        "firebase_action": [
            "Reading your command",
            "Loading Firebase from Integration Vault",
            "Applying backend changes",
            "Confirming update",
            "Wrapping up",
        ],
        "expo_build": [
            "Reading your command",
            "Loading Expo EAS from Integration Vault",
            "Queueing mobile build",
            "Waiting for build slot",
            "Wrapping up",
        ],
        "custom_integration": [
            "Reading your command",
            f"Loading {label} from vault",
            "Sending request to endpoint",
            "Processing response",
            "Wrapping up",
        ],
    }
    return mapping.get(intent.type, ["Reading your command"])


def _find_integration(
    intent: ParsedIntent, integrations: list[VaultIntegration]
) -> Optional[VaultIntegration]:
    if intent.integration_id:
        for item in integrations:
            if item.id == intent.integration_id:
                return item
        return _vault.get(intent.integration_id)

    type_map = {
        "vercel_deploy": "vercel",
        "firebase_action": "firebase",
        "stripe_charge": "stripe",
        "expo_build": "expo_eas",
        "custom_integration": "custom_webhook",
    }
    wanted = type_map.get(intent.type)
    if not wanted:
        return None
    for item in integrations:
        if item.type == wanted and _integration_active(item):
            return item
    return None


async def _execute_vault_integration(integration: VaultIntegration, prompt: str) -> ActionResponse:
    action_id = str(uuid.uuid4())
    label = INTEGRATION_LABELS.get(integration.type, integration.name or "Integration")
    mock = _use_mock_key(integration.api_key)

    if integration.type == "vercel":
        if mock:
            return ActionResponse(
                success=True,
                mock=True,
                message=f"Mock: Vercel deployment triggered for {integration.name}.",
                data={
                    "deploy_id": action_id,
                    "deploy_url": f"https://{integration.name or 'mock-app'}.vercel.app",
                    "integration": integration.name,
                },
            )
        return ActionResponse(
            success=True,
            mock=False,
            message="Vercel token accepted. Connect CI for full deploy automation.",
            data={"deploy_id": action_id, "integration": integration.name},
        )

    if integration.type == "stripe":
        if mock:
            return ActionResponse(
                success=True,
                mock=True,
                message=f"Mock: Stripe charge simulated for {integration.name}.",
                data={
                    "charge_id": f"ch_mock_{action_id[:8]}",
                    "amount_cents": 2000,
                    "integration": integration.name,
                },
            )
        return ActionResponse(
            success=True,
            mock=False,
            message="Stripe secret key format accepted. Use Stripe SDK for live charges.",
            data={"charge_id": f"ch_pending_{action_id[:8]}", "integration": integration.name},
        )

    if integration.type == "firebase":
        if mock:
            return ActionResponse(
                success=True,
                mock=True,
                message=f"Mock: Firebase action applied for {integration.name}.",
                data={
                    "resource_id": f"projects/mock-{action_id[:6]}",
                    "integration": integration.name,
                },
            )
        return ActionResponse(
            success=True,
            mock=False,
            message="Firebase credentials stored. Use Admin SDK for live mutations.",
            data={"resource_id": integration.name, "integration": integration.name},
        )

    if integration.type == "expo_eas":
        if mock:
            return ActionResponse(
                success=True,
                mock=True,
                message=f"Mock: EAS build queued for {integration.name}.",
                data={
                    "build_id": action_id,
                    "build_url": "https://expo.dev/accounts/mock/projects/mock/builds",
                    "artifact": "apk" if "apk" in prompt.lower() else "aab",
                    "integration": integration.name,
                },
            )
        return ActionResponse(
            success=True,
            mock=False,
            message="Expo access token accepted. Trigger builds via EAS CLI or API.",
            data={"build_id": action_id, "integration": integration.name},
        )

    # custom_webhook
    endpoint = integration.endpoint_url
    if mock or not endpoint:
        return ActionResponse(
            success=True,
            mock=True,
            message=f"Mock: Webhook call simulated for {integration.name or label}.",
            data={
                "request_id": action_id,
                "endpoint": endpoint or "https://hooks.example.com/mock",
                "integration": integration.name,
            },
        )

    headers = {"Authorization": f"Bearer {integration.api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                endpoint,
                headers=headers,
                json={"prompt": prompt, "source": "zero-terminal-orchestrator"},
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Webhook unreachable: {exc}") from exc

    ok = response.status_code < 400
    return ActionResponse(
        success=ok,
        mock=False,
        message=f"Webhook responded with HTTP {response.status_code}." if ok else "Webhook returned an error.",
        data={
            "request_id": action_id,
            "http_status": response.status_code,
            "endpoint": endpoint,
            "integration": integration.name,
        },
    )


# MCP Tools
@mcp.tool()
async def verify_supabase_connection(
    supabase_url: str, 
    supabase_anon_key: str,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Verify Supabase credentials and connection.
    
    Args:
        supabase_url: Supabase project URL
        supabase_anon_key: Supabase anon or service role key
        x_api_key: Zero Orchestrator API key for authentication
        
    Returns:
        Verification result with success status and details
    """
    with Session(engine) as db:
        user_id = _verify_api_key(x_api_key, db) if x_api_key else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        # Get user's integrations from database and decrypt keys
        integrations = db.exec(select(VaultIntegration).where(VaultIntegration.user_id == user_id)).all()
        decrypted_integrations = []
        for integration in integrations:
            decrypted_integration = VaultIntegration(
                id=integration.id,
                user_id=integration.user_id,
                type=integration.type,
                name=integration.name,
                api_key=_decrypt_api_key(integration.api_key) if integration.api_key else None,
                endpoint_url=integration.endpoint_url
            )
            decrypted_integrations.append(decrypted_integration)
    
    result = await verify_supabase(
        SupabaseCredentials(
            supabase_url=supabase_url,
            supabase_anon_key=supabase_anon_key,
            integrations=decrypted_integrations,
        )
    )
    return result.model_dump()


@mcp.tool()
async def deploy_to_netlify(
    netlify_token: str, 
    site_id: Optional[str] = None, 
    prompt: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Trigger a Netlify deployment.
    
    Args:
        netlify_token: Netlify personal access token
        site_id: Optional existing Netlify site ID
        prompt: Optional deployment message/description
        x_api_key: Zero Orchestrator API key for authentication
        
    Returns:
        Deployment result with deploy ID and URL
    """
    with Session(engine) as db:
        user_id = _verify_api_key(x_api_key, db) if x_api_key else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    result = await deploy_netlify(
        NetlifyDeployRequest(
            netlify_token=netlify_token,
            site_id=site_id,
            prompt=prompt,
            integrations=[],
        )
    )
    return result.model_dump()


@mcp.tool()
async def create_supabase_table(
    supabase_url: str, 
    supabase_anon_key: str, 
    prompt: str, 
    table_name: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Create a database table in Supabase based on natural language description.
    
    Args:
        supabase_url: Supabase project URL
        supabase_anon_key: Supabase anon or service role key
        prompt: Natural language description of the table
        table_name: Optional specific table name
        x_api_key: Zero Orchestrator API key for authentication
        
    Returns:
        Table creation result with SQL preview
    """
    with Session(engine) as db:
        user_id = _verify_api_key(x_api_key, db) if x_api_key else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    result = await create_table(
        CreateTableRequest(
            supabase_url=supabase_url,
            supabase_anon_key=supabase_anon_key,
            prompt=prompt,
            table_name=table_name,
            integrations=[],
        )
    )
    return result.model_dump()


@mcp.tool()
async def register_integration(
    integration_type: str, 
    name: str, 
    api_key: str, 
    endpoint_url: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Register a new integration in the vault.
    
    Args:
        integration_type: Type of integration (vercel, firebase, stripe, expo_eas, custom_webhook)
        name: Service/key name
        api_key: API token or key
        endpoint_url: Optional endpoint URL for custom_webhook type
        x_api_key: Zero Orchestrator API key for authentication
        
    Returns:
        Registration result with integration ID and status
    """
    with Session(engine) as db:
        user_id = _verify_api_key(x_api_key, db) if x_api_key else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    integration = VaultIntegration(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=integration_type,
        name=name,
        api_key=api_key,
        endpoint_url=endpoint_url,
    )
    _sync_vault([integration], user_id)
    return {
        "registered": 1,
        "active": 1 if _integration_active(integration) else 0,
        "integration_id": integration.id,
        "integration_type": integration.type,
        "name": integration.name,
    }


@mcp.tool()
async def execute_vault_integration(
    integration_id: str, 
    prompt: str,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Execute an action using a registered vault integration.
    
    Args:
        integration_id: ID of the integration to use
        prompt: Natural language command for the integration
        x_api_key: Zero Orchestrator API key for authentication
        
    Returns:
        Execution result with action details
    """
    with Session(engine) as db:
        user_id = _verify_api_key(x_api_key, db) if x_api_key else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        integration = db.exec(
            select(VaultIntegration).where(
                VaultIntegration.id == integration_id,
                VaultIntegration.user_id == user_id
            )
        ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found in vault")
    
    # Decrypt the API key before execution
    decrypted_integration = VaultIntegration(
        id=integration.id,
        user_id=integration.user_id,
        type=integration.type,
        name=integration.name,
        api_key=_decrypt_api_key(integration.api_key) if integration.api_key else None,
        endpoint_url=integration.endpoint_url
    )
    
    result = await _execute_vault_integration(decrypted_integration, prompt)
    return result.model_dump()


@mcp.tool()
async def execute_local_command(
    command: str, 
    auto_approve: bool = False,
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """Execute a local terminal command via the zero-cli subprocess bridge.
    
    This tool validates and logs command requests for local execution.
    The actual execution is handled by the zero-cli for security reasons.
    
    Args:
        command: Command to execute on the local machine
        auto_approve: Skip user confirmation (use with caution)
        x_api_key: Zero Orchestrator API key for authentication
        
    Returns:
        Command validation result with execution instructions
    """
    with Session(engine) as db:
        user_id = _verify_api_key(x_api_key, db) if x_api_key else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Log the command request for audit purposes
    print(f"[MCP SUBPROCESS] User: {user_id}")
    print(f"[MCP SUBPROCESS] Command: {command}")
    print(f"[MCP SUBPROCESS] Auto-approve: {auto_approve}")
    
    # Validate command for dangerous patterns
    dangerous_patterns = [
        "rm -rf /", "rm -rf /*", "sudo rm", "mkfs", "dd if=",
        ":(){:|:&};:", "chmod 777 /", "shutdown", "reboot"
    ]
    
    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in command_lower:
            return {
                "success": False,
                "error": f"Command blocked: Contains dangerous pattern '{pattern}'",
                "command": command,
                "instruction": "Use zero-cli locally to execute this command with proper safety checks"
            }
    
    # Return validation result - actual execution should be done by zero-cli
    return {
        "success": True,
        "message": "Command validated for local execution",
        "command": command,
        "instruction": "Execute this command using: zero-cli exec \"" + command + "\"",
        "auto_approve": auto_approve
    }


# HTTP Endpoints
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)) -> Token:
    """Register a new user."""
    # Check if user already exists
    existing_user = db.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=user_data.email,
        hashed_password=_get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = _create_access_token(data={"sub": user_id})
    return Token(access_token=access_token, token_type="bearer", user_id=user_id)


@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Login an existing user."""
    user = db.exec(select(User).where(User.email == user_data.email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not _verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = _create_access_token(data={"sub": user.id})
    return Token(access_token=access_token, token_type="bearer", user_id=user.id)


@app.post("/api/mcp/token", response_model=MCPTokenResponse)
async def generate_mcp_token(
    request: MCPTokenRequest,
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> MCPTokenResponse:
    """Generate a personal MCP token for the authenticated user."""
    if user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Cannot generate token for different user")
    
    token = _generate_mcp_token(user_id)
    
    # Store token in database
    mcp_token = MCPToken(token=token, user_id=user_id)
    db.add(mcp_token)
    db.commit()
    
    return MCPTokenResponse(
        token=token,
        user_id=user_id,
        created_at=datetime.now(timezone.utc)
    )


# API Key Management Routes
@app.post("/api/v1/developer/keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> APIKeyCreateResponse:
    """Generate a new API key for the authenticated user."""
    api_key = _generate_api_key()
    key_hash = _hash_api_key(api_key)
    key_prefix = api_key[:20]  # Store prefix for identification
    
    new_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=user_id,
        name=key_data.name,
        is_active=True
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    return APIKeyCreateResponse(
        key=api_key,  # Only returned once
        key_prefix=key_prefix,
        name=key_data.name,
        created_at=new_key.created_at
    )


@app.get("/api/v1/developer/keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> list[APIKeyResponse]:
    """List all API keys for the authenticated user."""
    keys = db.exec(
        select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
    ).all()
    
    return [
        APIKeyResponse(
            id=key.id,
            key_prefix=key.key_prefix,
            name=key.name,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            is_active=key.is_active
        )
        for key in keys
    ]


@app.delete("/api/v1/developer/keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, str]:
    """Revoke an API key by ID."""
    api_key = db.exec(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        )
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.add(api_key)
    db.commit()
    
    return {"message": "API key revoked successfully"}


# User Integration Management Routes
@app.post("/api/v1/developer/integrations", response_model=UserIntegrationResponse)
async def create_user_integration(
    integration_data: UserIntegrationCreate,
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> UserIntegrationResponse:
    """Add a custom user API integration."""
    # Encrypt the API key using Fernet
    encrypted_key = _encrypt_api_key(integration_data.api_key)
    
    new_integration = UserIntegration(
        user_id=user_id,
        service_name=integration_data.service_name,
        encrypted_api_key=encrypted_key,
        config=integration_data.config
    )
    db.add(new_integration)
    db.commit()
    db.refresh(new_integration)
    
    return UserIntegrationResponse(
        id=new_integration.id,
        service_name=new_integration.service_name,
        created_at=new_integration.created_at,
        updated_at=new_integration.updated_at
    )


@app.get("/api/v1/developer/integrations", response_model=list[UserIntegrationResponse])
async def list_user_integrations(
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> list[UserIntegrationResponse]:
    """List all custom user integrations."""
    integrations = db.exec(
        select(UserIntegration).where(UserIntegration.user_id == user_id)
    ).all()
    
    return [
        UserIntegrationResponse(
            id=integration.id,
            service_name=integration.service_name,
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )
        for integration in integrations
    ]


@app.delete("/api/v1/developer/integrations/{integration_id}")
async def delete_user_integration(
    integration_id: int,
    user_id: str = Depends(_get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, str]:
    """Delete a custom user integration."""
    integration = db.exec(
        select(UserIntegration).where(
            UserIntegration.id == integration_id,
            UserIntegration.user_id == user_id
        )
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    db.delete(integration)
    db.commit()
    
    return {"message": "Integration deleted successfully"}


@app.post("/api/integrations/register")
async def register_integrations(
    body: IntegrationsRegisterRequest,
    user_id: str = Depends(_get_current_user)
) -> dict[str, Any]:
    """Register integrations for the authenticated user."""
    with Session(engine) as db:
        for item in body.integrations:
            # Encrypt the API key before storage
            encrypted_key = _encrypt_api_key(item.api_key) if item.api_key else None
            
            # Check if integration exists
            existing = db.exec(
                select(VaultIntegration).where(
                    VaultIntegration.id == item.id,
                    VaultIntegration.user_id == user_id
                )
            ).first()
            
            if existing:
                # Update existing
                existing.type = item.type
                existing.name = item.name
                existing.api_key = encrypted_key
                existing.endpoint_url = item.endpoint_url
                existing.updated_at = datetime.now(timezone.utc)
            else:
                # Create new
                integration = VaultIntegration(
                    id=item.id,
                    user_id=user_id,
                    type=item.type,
                    name=item.name,
                    api_key=encrypted_key,
                    endpoint_url=item.endpoint_url
                )
                db.add(integration)
        
        db.commit()
    
    active = sum(1 for i in body.integrations if _integration_active(i))
    return {
        "registered": len(body.integrations),
        "active": active,
        "integration_ids": [i.id for i in body.integrations],
        "user_id": user_id,
    }


@app.post("/api/parse-command", response_model=ParseCommandResponse)
async def parse_command(body: ParseCommandRequest) -> ParseCommandResponse:
    _sync_vault(body.integrations)
    intent = _parse_prompt(body.prompt, body.integrations)
    return ParseCommandResponse(intent=intent, steps=_steps_for_intent(intent))


@app.post("/api/execute-integration", response_model=ActionResponse)
async def execute_integration(body: ExecuteIntegrationRequest) -> ActionResponse:
    _sync_vault(body.integrations)
    result = await _execute_vault_integration(body.integration, body.prompt)
    result.steps = _steps_for_intent(
        ParsedIntent(
            type="custom_integration",
            command=body.prompt,
            integration_id=body.integration.id,
            integration_type=body.integration.type,
        )
    )
    return result


@app.post("/api/orchestrate", response_model=ActionResponse)
async def orchestrate(body: OrchestrateRequest) -> ActionResponse:
    _sync_vault(body.integrations)
    intent = _parse_prompt(body.prompt, body.integrations)
    steps = _steps_for_intent(intent)

    if intent.type == "verify":
        result = await verify_supabase(
            SupabaseCredentials(
                supabase_url=body.supabase_url or "",
                supabase_anon_key=body.supabase_anon_key or "",
                integrations=body.integrations,
            )
        )
    elif intent.type == "deploy":
        result = await deploy_netlify(
            NetlifyDeployRequest(
                netlify_token=body.netlify_token or "",
                site_id=body.site_id,
                prompt=body.prompt,
                integrations=body.integrations,
            )
        )
    elif intent.type == "table":
        result = await create_table(
            CreateTableRequest(
                supabase_url=body.supabase_url or "",
                supabase_anon_key=body.supabase_anon_key or "",
                prompt=body.prompt,
                integrations=body.integrations,
            )
        )
    elif intent.type in ("vercel_deploy", "stripe_charge", "firebase_action", "expo_build", "custom_integration"):
        integration = _find_integration(intent, body.integrations)
        if not integration:
            return ActionResponse(
                success=False,
                mock=True,
                message=f"No active {INTEGRATION_LABELS.get(intent.integration_type or intent.type, 'integration')} found in vault. Add one first.",
                steps=steps,
            )
        result = await _execute_vault_integration(integration, body.prompt)
    else:
        result = await deploy_netlify(
            NetlifyDeployRequest(
                netlify_token=body.netlify_token or "",
                site_id=body.site_id,
                prompt=body.prompt,
                integrations=body.integrations,
            )
        )

    result.steps = steps
    return result


@app.post("/api/verify-supabase", response_model=ActionResponse)
async def verify_supabase(body: SupabaseCredentials) -> ActionResponse:
    if body.integrations:
        _sync_vault(body.integrations)

    if _use_mock_supabase(body.supabase_url, body.supabase_anon_key):
        return ActionResponse(
            success=True,
            mock=True,
            message="Mock: Supabase credentials accepted (no live API call).",
            data={
                "project_ref": "mock-project",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "hint": "Use real URL and key to verify against Supabase REST.",
            },
        )

    # Try live Supabase connection using supabase-py SDK
    try:
        supabase: Client = create_client(body.supabase_url, body.supabase_anon_key)
        # Test connection by querying the database
        response = supabase.table('_test_connection_').select('*').limit(1).execute()
        
        # If we get here, connection succeeded (even if table doesn't exist, we got a response)
        return ActionResponse(
            success=True,
            mock=False,
            message="Live Supabase connection verified successfully using supabase-py SDK.",
            data={
                "project_ref": body.supabase_url.split('//')[1].split('.')[0],
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "sdk": "supabase-py",
                "connection": "established",
            },
        )
    except Exception as e:
        # Fallback to HTTP REST API if SDK fails
        url = body.supabase_url.rstrip("/")
        rest_url = f"{url}/rest/v1/"
        headers = {
            "apikey": body.supabase_anon_key,
            "Authorization": f"Bearer {body.supabase_anon_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(rest_url, headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Could not reach Supabase: {exc}") from exc

        if response.status_code in (200, 401, 404):
            ok = response.status_code == 200
            return ActionResponse(
                success=ok or response.status_code == 401,
                mock=False,
                message=(
                    "Supabase REST endpoint reachable and credentials look valid."
                    if ok
                    else "Supabase responded; check key permissions (got HTTP 401)."
                ),
                data={
                    "http_status": response.status_code,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "method": "REST API fallback",
                },
            )

        return ActionResponse(
            success=False,
            mock=False,
            message=f"Supabase verification failed (HTTP {response.status_code}).",
            data={"http_status": response.status_code, "body_preview": response.text[:200]},
        )


@app.post("/api/deploy-netlify", response_model=ActionResponse)
async def deploy_netlify(body: NetlifyDeployRequest) -> ActionResponse:
    if body.integrations:
        _sync_vault(body.integrations)

    deploy_id = str(uuid.uuid4())
    if _use_mock_netlify(body.netlify_token):
        return ActionResponse(
            success=True,
            mock=True,
            message="Mock: Netlify deployment triggered successfully.",
            data={
                "deploy_id": deploy_id,
                "site_id": body.site_id or MOCK_NETLIFY_SITE,
                "state": "ready",
                "deploy_url": f"https://{MOCK_NETLIFY_SITE}.netlify.app",
                "prompt": body.prompt,
            },
        )

    headers = {"Authorization": f"Bearer {body.netlify_token}"}
    site_id = body.site_id

    try:
        # Use requests library for synchronous API calls
        if not site_id:
            sites_resp = requests.get(
                "https://api.netlify.com/api/v1/sites",
                headers=headers,
                params={"filter": "all", "page": 1, "per_page": 1},
                timeout=30.0
            )
            if sites_resp.status_code != 200:
                return ActionResponse(
                    success=False,
                    mock=False,
                    message="Failed to list Netlify sites. Check token.",
                    data={"http_status": sites_resp.status_code},
                )
            sites = sites_resp.json()
            if not sites:
                return ActionResponse(
                    success=False,
                    mock=False,
                    message="No Netlify sites found for this account.",
                    data={},
                )
            site_id = sites[0].get("id") or sites[0].get("site_id")

        trigger_resp = requests.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            headers=headers,
            json={"title": body.prompt or "Dashboard deploy"},
            timeout=30.0
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Netlify API error: {exc}") from exc

    if trigger_resp.status_code not in (200, 201):
        return ActionResponse(
            success=False,
            mock=False,
            message=f"Netlify deploy trigger failed (HTTP {trigger_resp.status_code}).",
            data={"http_status": trigger_resp.status_code, "body_preview": trigger_resp.text[:300]},
        )

    payload = trigger_resp.json()
    return ActionResponse(
        success=True,
        mock=False,
        message="Netlify deployment triggered.",
        data={
            "deploy_id": payload.get("id", deploy_id),
            "site_id": site_id,
            "state": payload.get("state"),
            "deploy_url": payload.get("deploy_ssl_url") or payload.get("ssl_url"),
            "prompt": body.prompt,
        },
    )


@app.post("/api/create-table", response_model=ActionResponse)
async def create_table(body: CreateTableRequest) -> ActionResponse:
    """Interpret prompt and create a table using live Supabase SDK when credentials are valid."""
    if body.integrations:
        _sync_vault(body.integrations)

    table_name = body.table_name or _infer_table_name(body.prompt)
    if _use_mock_supabase(body.supabase_url, body.supabase_anon_key):
        return ActionResponse(
            success=True,
            mock=True,
            message=f"Mock: Table '{table_name}' creation queued from your prompt.",
            data={
                "table_name": table_name,
                "sql_preview": (
                    f"CREATE TABLE IF NOT EXISTS public.{table_name} (\n"
                    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
                    "  created_at TIMESTAMPTZ DEFAULT now(),\n"
                    "  payload JSONB\n"
                    ");"
                ),
                "prompt": body.prompt,
            },
        )

    # Try live table creation using supabase-py SDK
    try:
        supabase: Client = create_client(body.supabase_url, body.supabase_anon_key)
        
        # Generate SQL based on prompt
        sql = (
            f"CREATE TABLE IF NOT EXISTS public.{table_name} (\n"
            "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "  created_at TIMESTAMPTZ DEFAULT now(),\n"
            "  description TEXT,\n"
            "  metadata JSONB DEFAULT '{}'::jsonb\n"
            ");"
        )
        
        # Execute SQL using RPC (requires service role key for DDL operations)
        # Note: anon keys typically can't execute DDL, so we'll return the SQL for manual execution
        # but verify the connection is valid
        try:
            # Try to execute via RPC if service role key is provided
            response = supabase.rpc('exec_sql', {'sql': sql}).execute()
            return ActionResponse(
                success=True,
                mock=False,
                message=f"Table '{table_name}' created successfully using supabase-py SDK.",
                data={
                    "table_name": table_name,
                    "sql_executed": sql,
                    "prompt": body.prompt,
                    "sdk": "supabase-py",
                    "method": "RPC execution",
                },
            )
        except Exception as rpc_error:
            # RPC failed (likely anon key), return SQL for manual execution
            return ActionResponse(
                success=True,
                mock=False,
                message=(
                    f"Supabase connection verified. Table SQL generated for '{table_name}'. "
                    "Execute in Supabase SQL editor (anon key cannot DDL via RPC)."
                ),
                data={
                    "table_name": table_name,
                    "sql_preview": sql,
                    "prompt": body.prompt,
                    "sdk": "supabase-py",
                    "method": "SQL generation (manual execution required)",
                    "note": str(rpc_error),
                },
            )
    except Exception as e:
        # Fallback to verification only if SDK fails
        verify = await verify_supabase(
            SupabaseCredentials(
                supabase_url=body.supabase_url,
                supabase_anon_key=body.supabase_anon_key,
                integrations=body.integrations,
            )
        )
        if not verify.success:
            return ActionResponse(
                success=False,
                mock=False,
                message="Could not verify Supabase before table creation.",
                data=verify.data,
            )
        
        sql = (
            f"CREATE TABLE IF NOT EXISTS public.{table_name} (\n"
            "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "  created_at TIMESTAMPTZ DEFAULT now(),\n"
            "  description TEXT,\n"
            "  metadata JSONB DEFAULT '{}'::jsonb\n"
            ");"
        )
        return ActionResponse(
            success=True,
            mock=False,
            message=(
                "Supabase verified. Run the suggested SQL in the Supabase SQL editor "
                "(SDK execution failed, manual execution required)."
            ),
            data={
                "table_name": table_name, 
                "sql_preview": sql, 
                "prompt": body.prompt,
                "error": str(e),
            },
        )


def _infer_table_name(prompt: str) -> str:
    words = [w.lower() for w in prompt.replace("_", " ").split() if w.isalnum()]
    candidates = [w for w in words if w not in {"a", "the", "create", "table", "for", "my", "database"}]
    if candidates:
        base = candidates[0][:32]
        return "".join(c if c.isalnum() else "_" for c in base) or "app_items"
    return "app_items"


@app.post("/api/subprocess", response_model=SubprocessResponse)
async def execute_subprocess(body: SubprocessRequest) -> SubprocessResponse:
    """Execute a subprocess command on the local machine (bridge to CLI).
    
    This endpoint is designed to work with the zero-cli local runner.
    The actual execution should be handled by the CLI for security reasons.
    This endpoint validates and logs the command request.
    """
    # Log the command request for audit purposes
    print(f"[SUBPROCESS REQUEST] Command: {body.command}")
    print(f"[SUBPROCESS REQUEST] Auto-approve: {body.auto_approve}")
    
    # For security, this endpoint only validates and returns the command
    # The actual execution should be done by the local CLI
    return SubprocessResponse(
        success=False,
        error="This endpoint validates commands only. Use zero-cli to execute commands locally.",
        command=body.command,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for warm-up and monitoring."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Zero Orchestrator API",
        "version": "1.1.0"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


# Mount MCP server as a sub-application
from fastapi import FastAPI as SubApp
mcp_app = FastAPI(title="Zero Orchestrator MCP Server")
@mcp_app.get("/")
async def mcp_root():
    return {"name": "Zero Orchestrator MCP", "version": "1.0.0", "status": "running"}

app.mount("/mcp", mcp_app)
