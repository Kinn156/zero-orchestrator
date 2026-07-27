import { serializeIntegrations } from "./orchestrate.js";

export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

async function parseJsonResponse(response) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return { detail: text || "Invalid JSON response" };
  }
}

function vaultPayload(integrations = []) {
  return integrations.length ? { integrations: serializeIntegrations(integrations) } : {};
}

export async function registerIntegrations(integrations) {
  const response = await fetch(`${API_BASE}/api/integrations/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ integrations: serializeIntegrations(integrations) }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Failed to register integrations");
  }
  return data;
}

export async function parseCommandRemote(prompt, integrations = []) {
  const response = await fetch(`${API_BASE}/api/parse-command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, integrations: serializeIntegrations(integrations) }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Failed to parse command");
  }
  return data;
}

export async function executeIntegration({ integration, prompt, integrations = [] }) {
  const response = await fetch(`${API_BASE}/api/execute-integration`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      integration: serializeIntegrations([integration])[0],
      prompt,
      integrations: serializeIntegrations(integrations),
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Integration action failed");
  }
  return data;
}

export async function orchestrate({
  prompt,
  supabaseUrl,
  supabaseKey,
  netlifyToken,
  netlifySiteId,
  integrations = [],
}) {
  const response = await fetch(`${API_BASE}/api/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      supabase_url: supabaseUrl || null,
      supabase_anon_key: supabaseKey || null,
      netlify_token: netlifyToken || null,
      site_id: netlifySiteId || null,
      integrations: serializeIntegrations(integrations),
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Orchestration failed");
  }
  return data;
}

export async function verifySupabase(supabaseUrl, supabaseAnonKey, integrations = []) {
  const response = await fetch(`${API_BASE}/api/verify-supabase`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      supabase_url: supabaseUrl,
      supabase_anon_key: supabaseAnonKey,
      ...vaultPayload(integrations),
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Supabase verification failed");
  }
  return data;
}

export async function deployNetlify({ netlifyToken, siteId, prompt, integrations = [] }) {
  const response = await fetch(`${API_BASE}/api/deploy-netlify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      netlify_token: netlifyToken,
      site_id: siteId || null,
      prompt: prompt || null,
      ...vaultPayload(integrations),
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Netlify deploy failed");
  }
  return data;
}

export async function createDatabaseTable({
  supabaseUrl,
  supabaseAnonKey,
  prompt,
  integrations = [],
}) {
  const response = await fetch(`${API_BASE}/api/create-table`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      supabase_url: supabaseUrl,
      supabase_anon_key: supabaseAnonKey,
      prompt,
      ...vaultPayload(integrations),
    }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Create table failed");
  }
  return data;
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return response.ok;
}

// Authentication API functions
export async function registerUser(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Registration failed");
  }
  return data;
}

export async function loginUser(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Login failed");
  }
  return data;
}

export async function generateMCPToken(userId, accessToken) {
  const response = await fetch(`${API_BASE}/api/mcp/token`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${accessToken}`
    },
    body: JSON.stringify({ user_id: userId }),
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Failed to generate MCP token");
  }
  return data;
}
