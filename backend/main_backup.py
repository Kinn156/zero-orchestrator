"""FastAPI backend for Supabase verification, Netlify deployment, and universal integration vault."""



from __future__ import annotations



import os

import re

import uuid

from datetime import datetime, timezone

from typing import Any, Literal, Optional



import httpx

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field
from fastmcp import FastMCP



app = FastAPI(title="Deploy Dashboard API", version="1.1.0")



app.add_middleware(

    CORSMiddleware,

    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



MOCK_SUPABASE_URL = "https://mock-project.supabase.co"

MOCK_NETLIFY_SITE = "mock-deploy-site"



# In-memory integration vault (session-scoped per server process)

_vault: dict[str, "VaultIntegration"] = {}



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





def _sync_vault(integrations: list["VaultIntegration"]) -> None:

    for item in integrations:

        _vault[item.id] = item





def _integration_active(item: VaultIntegration) -> bool:

    return bool(item.api_key and item.api_key.strip())





def _match_custom_by_name(prompt: str, integrations: list[VaultIntegration]) -> Optional[VaultIntegration]:

    lower = prompt.lower()

    for item in integrations:

        if item.name and item.name.strip() and item.name.strip().lower() in lower:

            return item

    return None





class VaultIntegration(BaseModel):

    id: str

    type: str = Field(..., description="vercel | firebase | stripe | expo_eas | custom_webhook")

    name: str

    api_key: str = ""

    endpoint_url: Optional[str] = None





class IntegrationsRegisterRequest(BaseModel):

    integrations: list[VaultIntegration] = Field(default_factory=list)





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





@app.get("/health")

async def health() -> dict[str, str]:

    return {"status": "ok"}





@app.post("/api/integrations/register")

async def register_integrations(body: IntegrationsRegisterRequest) -> dict[str, Any]:

    _sync_vault(body.integrations)

    active = sum(1 for i in body.integrations if _integration_active(i))

    return {

        "registered": len(body.integrations),

        "active": active,

        "integration_ids": [i.id for i in body.integrations],

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

        async with httpx.AsyncClient(timeout=30.0) as client:

            if not site_id:

                sites_resp = await client.get(

                    "https://api.netlify.com/api/v1/sites",

                    headers=headers,

                    params={"filter": "all", "page": 1, "per_page": 1},

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



            trigger_resp = await client.post(

                f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",

                headers=headers,

                json={"title": body.prompt or "Dashboard deploy"},

            )

    except httpx.RequestError as exc:

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

    """Interpret prompt and create a table (mock SQL generation or Supabase RPC hint)."""

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

            "(anon key cannot DDL via REST by default)."

        ),

        data={"table_name": table_name, "sql_preview": sql, "prompt": body.prompt},

    )





def _infer_table_name(prompt: str) -> str:

    words = [w.lower() for w in prompt.replace("_", " ").split() if w.isalnum()]

    candidates = [w for w in words if w not in {"a", "the", "create", "table", "for", "my", "database"}]

    if candidates:

        base = candidates[0][:32]

        return "".join(c if c.isalnum() else "_" for c in base) or "app_items"

    return "app_items"





if __name__ == "__main__":

    import uvicorn



    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

