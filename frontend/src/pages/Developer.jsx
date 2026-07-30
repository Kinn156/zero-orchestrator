import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../api.js";

export default function Developer() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("api-keys");
  
  // API Keys state
  const [apiKeys, setApiKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newApiKey, setNewApiKey] = useState("");
  const [showNewKey, setShowNewKey] = useState(false);
  
  // User Integrations state
  const [userIntegrations, setUserIntegrations] = useState([]);
  const [newServiceName, setNewServiceName] = useState("");
  const [newServiceKey, setNewServiceKey] = useState("");
  
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (!savedUser) {
      navigate('/login');
      return;
    }
    setUser(JSON.parse(savedUser));
    fetchApiKeys();
    fetchUserIntegrations();
  }, [navigate]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { "Authorization": `Bearer ${token}` } : {};
  };

  const fetchApiKeys = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/developer/keys`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setApiKeys(data);
      }
    } catch (error) {
      console.error("Failed to fetch API keys:", error);
    }
  };

  const fetchUserIntegrations = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/developer/integrations`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setUserIntegrations(data);
      }
    } catch (error) {
      console.error("Failed to fetch integrations:", error);
    }
  };

  const createApiKey = async () => {
    if (!newKeyName.trim()) return;
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/developer/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ name: newKeyName })
      });
      
      if (response.ok) {
        const data = await response.json();
        setNewApiKey(data.key);
        setShowNewKey(true);
        setNewKeyName("");
        fetchApiKeys();
      }
    } catch (error) {
      console.error("Failed to create API key:", error);
    }
  };

  const revokeApiKey = async (keyId) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/developer/keys/${keyId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        fetchApiKeys();
      }
    } catch (error) {
      console.error("Failed to revoke API key:", error);
    }
  };

  const createUserIntegration = async () => {
    if (!newServiceName.trim() || !newServiceKey.trim()) return;
    
    try {
      const response = await fetch(`${API_BASE}/api/v1/developer/integrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ 
          service_name: newServiceName,
          api_key: newServiceKey
        })
      });
      
      if (response.ok) {
        setNewServiceName("");
        setNewServiceKey("");
        fetchUserIntegrations();
      }
    } catch (error) {
      console.error("Failed to create integration:", error);
    }
  };

  const deleteUserIntegration = async (integrationId) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/developer/integrations/${integrationId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        fetchUserIntegrations();
      }
    } catch (error) {
      console.error("Failed to delete integration:", error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-2xl font-bold text-white">Developer & Extensions</h1>
              <p className="mt-1 text-sm text-slate-400">Manage API keys, custom integrations, and download extensions</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="text-sm text-slate-400 hover:text-white"
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        {/* Tabs */}
        <div className="mb-6 flex gap-2 border-b border-slate-800">
          <button
            onClick={() => setActiveTab("api-keys")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "api-keys"
                ? "border-b-2 border-orange-400 text-orange-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            API Keys
          </button>
          <button
            onClick={() => setActiveTab("integrations")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "integrations"
                ? "border-b-2 border-orange-400 text-orange-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            External APIs
          </button>
          <button
            onClick={() => setActiveTab("extensions")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "extensions"
                ? "border-b-2 border-orange-400 text-orange-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Download Extension
          </button>
        </div>

        {/* API Keys Tab */}
        {activeTab === "api-keys" && (
          <div className="space-y-6">
            <div className="panel p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-4">API Key Manager</h2>
              <p className="text-sm text-slate-400 mb-6">
                Generate personal API keys to access Zero Orchestrator programmatically. Keys are returned only once.
              </p>

              {/* Create API Key */}
              <div className="mb-6 flex gap-3">
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="Key name (e.g., 'Production', 'Development')"
                  className="input-field flex-1"
                />
                <button
                  onClick={createApiKey}
                  className="btn-primary"
                >
                  Generate Key
                </button>
              </div>

              {/* New Key Display */}
              {showNewKey && (
                <div className="mb-6 p-4 rounded-lg bg-orange-500/10 border border-orange-500/20">
                  <p className="text-sm text-orange-200 mb-2">Your new API key (copy this now, it won't be shown again):</p>
                  <code className="block p-3 bg-slate-900 rounded text-xs text-orange-400 break-all">
                    {newApiKey}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(newApiKey);
                      setShowNewKey(false);
                    }}
                    className="mt-3 text-sm text-orange-300 hover:text-orange-200"
                  >
                    Copy and Close
                  </button>
                </div>
              )}

              {/* API Keys List */}
              <div className="space-y-3">
                {apiKeys.length === 0 ? (
                  <p className="text-sm text-slate-500">No API keys generated yet.</p>
                ) : (
                  apiKeys.map((key) => (
                    <div key={key.id} className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                      <div>
                        <p className="text-sm font-medium text-white">{key.name}</p>
                        <p className="text-xs text-slate-400 font-mono">{key.key_prefix}...</p>
                        <p className="text-xs text-slate-500 mt-1">
                          Created: {new Date(key.created_at).toLocaleDateString()}
                          {key.last_used_at && ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                        </p>
                      </div>
                      {key.is_active && (
                        <button
                          onClick={() => revokeApiKey(key.id)}
                          className="text-sm text-red-400 hover:text-red-300"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* External APIs Tab */}
        {activeTab === "integrations" && (
          <div className="space-y-6">
            <div className="panel p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-4">External APIs</h2>
              <p className="text-sm text-slate-400 mb-6">
                Add third-party API integrations (e.g., Paystack, OpenAI, custom endpoints) for use in your workflows.
              </p>

              {/* Add Integration */}
              <div className="mb-6 space-y-3">
                <input
                  type="text"
                  value={newServiceName}
                  onChange={(e) => setNewServiceName(e.target.value)}
                  placeholder="Service name (e.g., 'Paystack', 'OpenAI')"
                  className="input-field"
                />
                <input
                  type="password"
                  value={newServiceKey}
                  onChange={(e) => setNewServiceKey(e.target.value)}
                  placeholder="API Key"
                  className="input-field"
                />
                <button
                  onClick={createUserIntegration}
                  className="btn-primary w-full"
                >
                  Add Integration
                </button>
              </div>

              {/* Integrations List */}
              <div className="space-y-3">
                {userIntegrations.length === 0 ? (
                  <p className="text-sm text-slate-500">No external integrations added yet.</p>
                ) : (
                  userIntegrations.map((integration) => (
                    <div key={integration.id} className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                      <div>
                        <p className="text-sm font-medium text-white">{integration.service_name}</p>
                        <p className="text-xs text-slate-500">
                          Added: {new Date(integration.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteUserIntegration(integration.id)}
                        className="text-sm text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Download Extension Tab */}
        {activeTab === "extensions" && (
          <div className="space-y-6">
            <div className="panel p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-4">Download Extension</h2>
              <p className="text-sm text-slate-400 mb-6">
                Download the Zero Orchestrator MCP extension for Claude Desktop or VS Code to integrate directly with your development environment.
              </p>

              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                  <h3 className="text-sm font-medium text-white mb-2">Claude Desktop Extension</h3>
                  <p className="text-xs text-slate-400 mb-3">
                    Install the .mcpb file to add Zero Orchestrator tools to Claude Desktop.
                  </p>
                  <button className="btn-primary text-sm">
                    Download .mcpb File
                  </button>
                </div>

                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                  <h3 className="text-sm font-medium text-white mb-2">VS Code Extension</h3>
                  <p className="text-xs text-slate-400 mb-3">
                    Use the MCP server configuration to connect VS Code to Zero Orchestrator.
                  </p>
                  <button className="btn-primary text-sm">
                    View Setup Instructions
                  </button>
                </div>

                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                  <h3 className="text-sm font-medium text-white mb-2">MCP Server Configuration</h3>
                  <p className="text-xs text-slate-400 mb-3">
                    Server URL: <code className="text-orange-400">{API_BASE}/mcp</code>
                  </p>
                  <p className="text-xs text-slate-400">
                    Authentication: Use your personal API key via <code className="text-orange-400">X-API-Key</code> header
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
