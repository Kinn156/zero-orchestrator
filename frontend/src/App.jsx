import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import Toast from "./components/Toast.jsx";

import {

  checkHealth,

  createDatabaseTable,

  deployNetlify,

  executeIntegration,

  registerIntegrations,

  verifySupabase,

  registerUser,

  loginUser,

  generateMCPToken,

  API_BASE,

} from "./api.js";

import {

  detectMode,

  findIntegrationForIntent,

  humanizeOutcome,

  INTEGRATION_TYPES,

  integrationTypeLabel,

  isIntegrationActive,

  parseCommand,

  stepsForIntent,

} from "./orchestrate.js";



const MODE_LABELS = {

  mock: "Mock",

  live: "Live",

  mixed: "Mixed",

};



const EMPTY_FORM = {

  type: "vercel",

  name: "",

  apiKey: "",

  endpointUrl: "",

};






function StreamIcon({ status }) {

  if (status === "running") {

    return (

      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">

        <span className="h-2.5 w-2.5 animate-pulse-soft rounded-full bg-orange-400" />

      </span>

    );

  }

  if (status === "done") {

    return (

      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center text-emerald-400">

        ✓

      </span>

    );

  }

  if (status === "error") {

    return (

      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center text-red-400">

        !

      </span>

    );

  }

  return (

    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center text-slate-600">

      ·

    </span>

  );

}



function ActionStream({ entries, streamRef }) {

  return (

    <div

      ref={streamRef}

      className="panel-muted max-h-[420px] min-h-[280px] overflow-y-auto p-3 sm:p-4"

    >

      {entries.length === 0 ? (

        <div className="flex h-full min-h-[240px] flex-col items-center justify-center text-center">

          <p className="font-display text-sm font-medium text-slate-300">Action Stream</p>

          <p className="mt-2 max-w-sm text-sm text-slate-500">

            Run a natural language command to see step-by-step progress here—no raw logs or JSON.

          </p>

        </div>

      ) : (

        <ul className="space-y-1">

          {entries.map((entry) => (

            <li

              key={entry.id}

              className={`stream-item ${

                entry.status === "running"

                  ? "stream-item-active"

                  : entry.status === "error"

                    ? "stream-item-error"

                    : entry.status === "done"

                      ? "stream-item-done"

                      : ""

              }`}

            >

              <StreamIcon status={entry.status} />

              <div className="min-w-0 flex-1">

                <p

                  className={

                    entry.status === "error"

                      ? "text-red-200"

                      : entry.status === "done"

                        ? "text-slate-200"

                        : "text-slate-300"

                  }

                >

                  {entry.message}

                </p>

                <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-600">

                  {entry.time}

                </p>

              </div>

            </li>

          ))}

        </ul>

      )}

    </div>

  );

}



function IntegrationStatusBadge({ active }) {

  return (

    <span

      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${

        active

          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"

          : "border-slate-600 bg-surface-900 text-slate-500"

      }`}

    >

      <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-emerald-400" : "bg-slate-600"}`} />

      {active ? "Active" : "Inactive"}

    </span>

  );

}



function VaultIntegrationCard({ integration, onRemove }) {

  const active = isIntegrationActive(integration);

  const maskedKey = integration.apiKey

    ? `${integration.apiKey.slice(0, 4)}${"•".repeat(Math.min(8, integration.apiKey.length))}`

    : "No key set";



  return (

    <article className="panel-muted p-4">

      <header className="mb-3 flex items-start justify-between gap-2">

        <div className="min-w-0">

          <div className="flex flex-wrap items-center gap-2">

            <h3 className="font-display text-sm font-semibold text-white">

              {integration.name || integrationTypeLabel(integration.type)}

            </h3>

            <IntegrationStatusBadge active={active} />

          </div>

          <p className="mt-0.5 text-xs text-slate-500">

            {integrationTypeLabel(integration.type)}

          </p>

        </div>

        <button

          type="button"

          className="shrink-0 text-xs text-slate-500 hover:text-red-300"

          onClick={() => onRemove(integration.id)}

        >

          Remove

        </button>

      </header>

      <dl className="space-y-2 text-xs">

        <div className="flex justify-between gap-3">

          <dt className="text-slate-500">API key</dt>

          <dd className="truncate font-mono text-slate-400">{maskedKey}</dd>

        </div>

        {integration.endpointUrl ? (

          <div className="flex justify-between gap-3">

            <dt className="shrink-0 text-slate-500">Endpoint</dt>

            <dd className="truncate font-mono text-slate-400">{integration.endpointUrl}</dd>

          </div>

        ) : null}

      </dl>

    </article>

  );

}



function IntegrationModal({ open, form, formError, onChange, onClose, onSave }) {

  useEffect(() => {

    if (!open) return undefined;

    const onKey = (e) => {

      if (e.key === "Escape") onClose();

    };

    window.addEventListener("keydown", onKey);

    return () => window.removeEventListener("keydown", onKey);

  }, [open, onClose]);



  if (!open) return null;



  const showEndpoint = form.type === "custom_webhook";



  return (

    <div className="modal-backdrop" role="presentation" onClick={onClose}>

      <div

        className="modal-panel"

        role="dialog"

        aria-modal="true"

        aria-labelledby="integration-modal-title"

        onClick={(e) => e.stopPropagation()}

      >

        <header className="mb-5 flex items-start justify-between gap-3">

          <div>

            <h2 id="integration-modal-title" className="font-display text-lg font-semibold text-white">

              Add Integration

            </h2>

            <p className="mt-1 text-sm text-slate-400">

              Register a service in your vault for natural language commands.

            </p>

          </div>

          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">

            ×

          </button>

        </header>



        <form

          className="space-y-4"

          onSubmit={(e) => {

            e.preventDefault();

            onSave();

          }}

        >

          <label className="block">

            <span className="mb-1.5 block text-xs font-medium text-slate-400">Integration type</span>

            <select

              className="input-field"

              value={form.type}

              onChange={(e) => onChange("type", e.target.value)}

            >

              {INTEGRATION_TYPES.map((type) => (

                <option key={type.id} value={type.id}>

                  {type.label} — {type.subtitle}

                </option>

              ))}

            </select>

          </label>



          <label className="block">

            <span className="mb-1.5 block text-xs font-medium text-slate-400">Service / key name</span>

            <input

              className="input-field"

              placeholder="e.g. Production Vercel"

              value={form.name}

              onChange={(e) => onChange("name", e.target.value)}

            />

          </label>



          <label className="block">

            <span className="mb-1.5 block text-xs font-medium text-slate-400">API token / key</span>

            <input

              className="input-field font-mono text-xs"

              type="password"

              placeholder="Paste secret key or token"

              value={form.apiKey}

              onChange={(e) => onChange("apiKey", e.target.value)}

            />

          </label>



          {showEndpoint ? (

            <label className="block">

              <span className="mb-1.5 block text-xs font-medium text-slate-400">

                Endpoint URL <span className="text-slate-600">(optional for mock)</span>

              </span>

              <input

                className="input-field font-mono text-xs"

                placeholder="https://api.example.com/hook"

                value={form.endpointUrl}

                onChange={(e) => onChange("endpointUrl", e.target.value)}

              />

            </label>

          ) : null}



          {formError ? <p className="text-sm text-red-300">{formError}</p> : null}



          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">

            <button type="button" className="btn-ghost sm:min-w-[100px]" onClick={onClose}>

              Cancel

            </button>

            <button type="submit" className="btn-primary sm:min-w-[140px]">

              Save to Vault

            </button>

          </div>

        </form>

      </div>

    </div>

  );

}



function formatTime(date = new Date()) {

  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

}



function Modal({ open, onClose, children }) {

  useEffect(() => {

    if (!open) return undefined;

    const onKey = (e) => {

      if (e.key === "Escape") onClose();

    };

    window.addEventListener("keydown", onKey);

    return () => window.removeEventListener("keydown", onKey);

  }, [open, onClose]);



  if (!open) return null;



  return (

    <div className="modal-backdrop" role="presentation" onClick={onClose}>

      <div

        className="modal-panel"

        role="dialog"

        aria-modal="true"

        onClick={(e) => e.stopPropagation()}

      >

        {children}

      </div>

    </div>

  );

}



const CUSTOM_INTENT_TYPES = new Set([

  "vercel_deploy",

  "stripe_charge",

  "firebase_action",

  "expo_build",

  "custom_integration",

]);



export default function App() {

  const [supabaseUrl, setSupabaseUrl] = useState("");

  const [supabaseKey, setSupabaseKey] = useState("");

  const [netlifyToken, setNetlifyToken] = useState("");

  const [netlifySiteId, setNetlifySiteId] = useState("");

  const [customIntegrations, setCustomIntegrations] = useState([]);

  const [modalOpen, setModalOpen] = useState(false);

  const [modalForm, setModalForm] = useState(EMPTY_FORM);

  const [modalError, setModalError] = useState("");

  const [command, setCommand] = useState("");

  const [stream, setStream] = useState([]);

  const [isRunning, setIsRunning] = useState(false);

  // Load user from localStorage on mount
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [showDevSettings, setShowDevSettings] = useState(false);
  const [mcpToken, setMcpToken] = useState("");
  const [toast, setToast] = useState(null);

  const streamRef = useRef(null);

  const entryCounter = useRef(0);



  const mode = useMemo(

    () => detectMode({ supabaseUrl, supabaseKey, netlifyToken, customIntegrations }),

    [supabaseUrl, supabaseKey, netlifyToken, customIntegrations]

  );



  useEffect(() => {

    if (streamRef.current) {

      streamRef.current.scrollTop = streamRef.current.scrollHeight;

    }

  }, [stream]);



  useEffect(() => {

    if (!customIntegrations.length) return;

    registerIntegrations(customIntegrations).catch(() => {

      /* vault sync is best-effort on load */

    });

  }, [customIntegrations]);



  const handleGenerateMCPToken = async () => {
    if (!user) return;
    
    try {
      const result = await generateMCPToken(user.id);
      setMcpToken(result.token);
    } catch (error) {
      setToast({ message: "Failed to generate MCP token. Please try again.", type: "error" });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setMcpToken("");
    setShowDevSettings(false);
    window.location.href = '/login';
  };



  const pushStream = useCallback((message, status = "done") => {

    entryCounter.current += 1;

    setStream((prev) => [

      ...prev,

      {

        id: entryCounter.current,

        message,

        status,

        time: formatTime(),

      },

    ]);

  }, []);



  const updateLastStream = useCallback((status, message) => {

    setStream((prev) => {

      if (prev.length === 0) return prev;

      const next = [...prev];

      const last = { ...next[next.length - 1], status };

      if (message) last.message = message;

      next[next.length - 1] = last;

      return next;

    });

  }, []);



  const waitStep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));



  const runSteps = useCallback(

    async (labels, action) => {

      for (let i = 0; i < labels.length; i += 1) {

        pushStream(labels[i], i === labels.length - 1 ? "running" : "done");

        if (i < labels.length - 1) {

          await waitStep(350);

        }

      }

      try {

        const result = await action();

        updateLastStream("done");

        return result;

      } catch (err) {

        updateLastStream("error", labels[labels.length - 1]);

        pushStream(err.message || "Something went wrong.", "error");

        throw err;

      }

    },

    [pushStream, updateLastStream]

  );



  const executeIntent = useCallback(

    async (intent) => {

      const vault = customIntegrations;

      const creds = {

        supabaseUrl,

        supabaseKey,

        netlifyToken,

        netlifySiteId,

        command: intent.command,

      };



      if (CUSTOM_INTENT_TYPES.has(intent.type)) {

        const integration = findIntegrationForIntent(intent, vault);

        if (!integration) {

          pushStream(

            `No active ${integrationTypeLabel(intent.integrationType || intent.type)} integration in vault. Add one first.`,

            "error"

          );

          return { success: false };

        }

        return runSteps(stepsForIntent(intent.type, intent), () =>

          executeIntegration({

            integration,

            prompt: creds.command,

            integrations: vault,

          })

        );

      }



      if (intent.type === "verify") {

        return runSteps(stepsForIntent("verify"), () =>

          verifySupabase(creds.supabaseUrl, creds.supabaseKey, vault)

        );

      }

      if (intent.type === "deploy") {

        return runSteps(stepsForIntent("deploy"), () =>

          deployNetlify({

            netlifyToken: creds.netlifyToken,

            siteId: creds.netlifySiteId,

            prompt: creds.command,

            integrations: vault,

          })

        );

      }

      if (intent.type === "table") {

        return runSteps(stepsForIntent("table"), () =>

          createDatabaseTable({

            supabaseUrl: creds.supabaseUrl,

            supabaseAnonKey: creds.supabaseKey,

            prompt: creds.command,

            integrations: vault,

          })

        );

      }

      if (intent.type === "pipeline") {

        const labels = stepsForIntent("pipeline");

        pushStream(labels[0], "done");

        await waitStep(300);

        pushStream(labels[1], "running");

        const verifyResult = await verifySupabase(creds.supabaseUrl, creds.supabaseKey, vault);

        updateLastStream("done");

        if (!verifyResult.success) {

          pushStream("Supabase verification failed. Fix credentials and retry.", "error");

          return verifyResult;

        }

        await waitStep(250);

        pushStream(labels[2], "running");

        const tableResult = await createDatabaseTable({

          supabaseUrl: creds.supabaseUrl,

          supabaseAnonKey: creds.supabaseKey,

          prompt: creds.command,

          integrations: vault,

        });

        updateLastStream("done");

        pushStream(humanizeOutcome("table", tableResult), tableResult.success ? "done" : "error");

        await waitStep(250);

        pushStream(labels[3], "running");

        const deployResult = await deployNetlify({

          netlifyToken: creds.netlifyToken,

          siteId: creds.netlifySiteId,

          prompt: creds.command,

          integrations: vault,

        });

        updateLastStream("done");

        return deployResult;

      }

      return null;

    },

    [

      supabaseUrl,

      supabaseKey,

      netlifyToken,

      netlifySiteId,

      customIntegrations,

      runSteps,

      pushStream,

      updateLastStream,

    ]

  );



  const handleRunCommand = async () => {

    const intent = parseCommand(command, customIntegrations);

    if (intent.type === "empty") return;



    setIsRunning(true);

    setStream([]);

    entryCounter.current = 0;



    pushStream(`Got it: "${intent.command}"`, "done");



    try {

      if (!(await checkHealth())) {

        setBackendOnline(false);

        pushStream("Backend is not reachable. Start the API on port 8080.", "error");

        return;

      }

      setBackendOnline(true);



      await registerIntegrations(customIntegrations).catch(() => null);



      const result = await executeIntent(intent);

      if (!result) return;



      if (intent.type === "pipeline") {

        pushStream(humanizeOutcome("deploy", result), result.success ? "done" : "error");

        pushStream("All requested steps finished.", "done");

        return;

      }



      if (CUSTOM_INTENT_TYPES.has(intent.type)) {

        pushStream(humanizeOutcome(intent.type, result, intent), result.success ? "done" : "error");

        return;

      }



      const summaryType =

        intent.type === "verify" ? "verify" : intent.type === "table" ? "table" : "deploy";

      pushStream(humanizeOutcome(summaryType, result), result.success ? "done" : "error");

    } catch {

      /* errors already logged in stream */

    } finally {

      setIsRunning(false);

    }

  };



  const openAddModal = () => {

    setModalForm(EMPTY_FORM);

    setModalError("");

    setModalOpen(true);

  };



  const closeModal = () => {

    setModalOpen(false);

    setModalError("");

  };



  const handleModalChange = (field, value) => {

    setModalForm((prev) => ({ ...prev, [field]: value }));

    setModalError("");

  };



  const handleSaveIntegration = async () => {

    if (!modalForm.name.trim()) {

      setModalError("Enter a service or key name.");

      return;

    }

    if (!modalForm.apiKey.trim()) {

      setModalError("Enter an API token or key.");

      return;

    }

    if (modalForm.type === "custom_webhook" && modalForm.endpointUrl.trim()) {

      try {

        new URL(modalForm.endpointUrl.trim());

      } catch {

        setModalError("Enter a valid endpoint URL.");

        return;

      }

    }



    const entry = {

      id: crypto.randomUUID(),

      type: modalForm.type,

      name: modalForm.name.trim(),

      apiKey: modalForm.apiKey.trim(),

      endpointUrl: modalForm.endpointUrl.trim(),

    };



    setCustomIntegrations((prev) => [...prev, entry]);

    closeModal();



    if (backendOnline) {

      try {

        await registerIntegrations([...customIntegrations, entry]);

      } catch {

        /* saved locally; backend sync on next command */

      }

    }

  };



  const removeIntegration = (id) => {

    setCustomIntegrations((prev) => prev.filter((item) => item.id !== id));

  };



  const fillDemoCredentials = () => {

    setSupabaseUrl("https://mock-project.supabase.co");

    setSupabaseKey("mock-anon-key-demo");

    setNetlifyToken("mock-netlify-token");

  };



  return (

    <div className="relative min-h-screen overflow-hidden">

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(251,146,60,0.08),transparent)]" />

      <div className="pointer-events-none absolute bottom-0 left-1/2 h-64 w-[36rem] -translate-x-1/2 rounded-full bg-orange-500/5 blur-3xl" />



      <header className="relative border-b border-white/[0.06] bg-surface-950/80 backdrop-blur-xl">

        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">

          <div>

            <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent/80">

              Zero-Terminal Orchestrator

            </p>

            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">

              Command your stack in plain language

            </h1>

            <p className="mt-1 text-sm text-slate-400">

              API target: <span className="font-mono text-slate-500">{API_BASE}</span>

            </p>

          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowDevSettings(!showDevSettings)}
              className="btn-primary text-xs"
            >
              Developer Settings
            </button>
          </div>

        </div>

      </header>



      <main className="relative mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-5">

        <section className="panel p-5 lg:col-span-2 lg:p-6">

          <div className="flex items-start justify-between gap-3">

            <div>

              <h2 className="font-display text-lg font-semibold text-white">Integration Vault</h2>

              <p className="mt-1 text-sm text-slate-400">

                Store keys once. The orchestrator picks the right integration per command.

              </p>

            </div>

            <button

              type="button"

              onClick={fillDemoCredentials}

              className="shrink-0 text-xs font-medium text-orange-400 hover:text-orange-300"

            >

              Demo keys

            </button>

          </div>



          <div className="mt-5 space-y-3">

            <article className="panel-muted p-4">

              <header className="mb-3">

                <h3 className="font-display text-sm font-semibold text-white">Supabase</h3>

                <p className="mt-0.5 text-xs text-slate-500">Database & auth</p>

              </header>

              <div className="space-y-3">

                <input

                  className="input-field"

                  placeholder="Project URL"

                  value={supabaseUrl}

                  onChange={(e) => setSupabaseUrl(e.target.value)}

                />

                <input

                  className="input-field font-mono text-xs"

                  type="password"

                  placeholder="Anon or service key"

                  value={supabaseKey}

                  onChange={(e) => setSupabaseKey(e.target.value)}

                />

              </div>

            </article>



            <article className="panel-muted p-4">

              <header className="mb-3">

                <h3 className="font-display text-sm font-semibold text-white">Netlify</h3>

                <p className="mt-0.5 text-xs text-slate-500">Deploy & hosting</p>

              </header>

              <div className="space-y-3">

                <input

                  className="input-field font-mono text-xs"

                  type="password"

                  placeholder="Personal access token"

                  value={netlifyToken}

                  onChange={(e) => setNetlifyToken(e.target.value)}

                />

                <input

                  className="input-field font-mono text-xs"

                  placeholder="Site ID (optional)"

                  value={netlifySiteId}

                  onChange={(e) => setNetlifySiteId(e.target.value)}

                />

              </div>

            </article>



            {customIntegrations.map((integration) => (

              <VaultIntegrationCard

                key={integration.id}

                integration={integration}

                onRemove={removeIntegration}

              />

            ))}



            <button type="button" className="btn-ghost w-full" onClick={openAddModal}>

              + Add New Integration API

            </button>

          </div>

        </section>



        <section className="flex flex-col gap-6 lg:col-span-3">

          <div className="panel p-5 sm:p-6">

            <h2 className="font-display text-lg font-semibold text-white">

              Natural Language Command

            </h2>

            <p className="mt-1 text-sm text-slate-400">

              Examples: &quot;Deploy to Vercel&quot; · &quot;Charge customer via Stripe&quot; ·

              &quot;Build APK with EAS&quot; · &quot;Create users table in Supabase&quot;

            </p>

            <textarea

              className="input-field mt-4 min-h-[120px] resize-y text-base"

              placeholder="Describe what you want to happen…"

              value={command}

              onChange={(e) => setCommand(e.target.value)}

              onKeyDown={(e) => {

                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {

                  e.preventDefault();

                  handleRunCommand();

                }

              }}

            />

            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

              <p className="text-xs text-slate-500">Press Ctrl+Enter to run</p>

              <button

                type="button"

                className="btn-primary sm:min-w-[160px]"

                disabled={isRunning || !command.trim()}

                onClick={handleRunCommand}

              >

                {isRunning ? "Orchestrating…" : "Run Command"}

              </button>

            </div>

          </div>



          <div className="panel flex flex-1 flex-col p-5 sm:p-6">

            <div className="mb-3 flex items-center justify-between">

              <h2 className="font-display text-lg font-semibold text-white">Action Stream</h2>

              {stream.length > 0 ? (

                <button

                  type="button"

                  className="text-xs text-slate-500 hover:text-slate-300"

                  onClick={() => setStream([])}

                >

                  Clear

                </button>

              ) : null}

            </div>

            <ActionStream entries={stream} streamRef={streamRef} />

          </div>

        </section>

      </main>



      <IntegrationModal

        open={modalOpen}

        form={modalForm}

        formError={modalError}

        onChange={handleModalChange}

        onClose={closeModal}

        onSave={handleSaveIntegration}

      />

      {/* Developer Settings Modal */}
      <Modal
        open={showDevSettings}
        onClose={() => setShowDevSettings(false)}
      >
        <div className="panel p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl font-semibold text-white">
              Developer Settings
            </h2>
            <button
              onClick={handleLogout}
              className="text-sm text-red-400 hover:text-red-300"
            >
              Logout
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <p className="text-sm text-slate-400 mb-2">
                User: <span className="text-slate-300">{user?.email}</span>
              </p>
              <p className="text-sm text-slate-400 mb-4">
                User ID: <span className="font-mono text-slate-500">{user?.id}</span>
              </p>
            </div>
            
            <div className="border-t border-slate-800 pt-4">
              <h3 className="font-display text-lg font-semibold text-white mb-3">
                System Health
              </h3>
              <button
                onClick={async () => {
                  try {
                    const isHealthy = await checkHealth();
                    setToast({ 
                      message: isHealthy ? "Backend is online and healthy" : "Backend is offline", 
                      type: isHealthy ? "success" : "error" 
                    });
                  } catch {
                    setToast({ message: "Unable to reach server. Please try again.", type: "error" });
                  }
                }}
                className="btn-primary w-full"
              >
                Check Backend Health
              </button>
            </div>
            
            <div className="border-t border-slate-800 pt-4">
              <h3 className="font-display text-lg font-semibold text-white mb-3">
                MCP Token
              </h3>
              <p className="text-sm text-slate-400 mb-3">
                Generate a personal MCP token for authenticated tool execution.
              </p>
              
              {mcpToken ? (
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                    <code className="text-xs text-orange-400 break-all">
                      {mcpToken}
                    </code>
                  </div>
                  <button
                    onClick={() => setMcpToken("")}
                    className="text-sm text-slate-500 hover:text-slate-300"
                  >
                    Clear Token
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleGenerateMCPToken}
                  className="btn-primary w-full"
                >
                  Generate Personal MCP Token
                </button>
              )}
            </div>
          </div>
        </div>
      </Modal>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

    </div>

  );

}

