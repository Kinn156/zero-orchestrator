export const INTEGRATION_TYPES = [
  { id: "vercel", label: "Vercel", subtitle: "Deploy & hosting" },
  { id: "firebase", label: "Firebase", subtitle: "Backend & auth" },
  { id: "stripe", label: "Stripe", subtitle: "Payments" },
  { id: "expo_eas", label: "Expo EAS", subtitle: "Mobile builds" },
  { id: "custom_webhook", label: "Custom Webhook/API", subtitle: "Any HTTP endpoint" },
];

const DEPLOY_HINTS = /\b(deploy|publish|launch|ship|landing|site|host)\b/i;
const NETLIFY_HINTS = /\bnetlify\b/i;
const VERCEL_HINTS = /\bvercel\b/i;
const TABLE_HINTS = /\b(table|database|schema|supabase|sql|users?|records?|rows?)\b/i;
const VERIFY_HINTS = /\b(verify|validate|check|connect|test)\b.*\b(supabase|credentials|integration)\b/i;
const STRIPE_HINTS = /\b(stripe|charge|payment|invoice|billing|customer|checkout)\b/i;
const FIREBASE_HINTS = /\b(firebase|firestore|cloud functions?|realtime database)\b/i;
const EAS_HINTS = /\b(eas|expo|apk|aab|mobile build|app store|play store)\b/i;
const WEBHOOK_HINTS = /\b(webhook|hook|callback|trigger api|call api)\b/i;

export function integrationTypeLabel(typeId) {
  return INTEGRATION_TYPES.find((t) => t.id === typeId)?.label ?? typeId;
}

export function isIntegrationActive(integration) {
  return Boolean(integration?.apiKey?.trim());
}

export function findIntegrationForIntent(intent, integrations) {
  if (!integrations?.length) return null;

  if (intent.integrationId) {
    return integrations.find((i) => i.id === intent.integrationId) ?? null;
  }

  const typeMap = {
    vercel_deploy: "vercel",
    firebase_action: "firebase",
    stripe_charge: "stripe",
    expo_build: "expo_eas",
    custom_integration: "custom_webhook",
  };

  const type = typeMap[intent.type];
  if (!type) return null;

  return integrations.find((i) => i.type === type && isIntegrationActive(i)) ?? null;
}

export function matchCustomByName(command, integrations) {
  const lower = command.toLowerCase();
  return (
    integrations.find(
      (i) => i.name?.trim() && lower.includes(i.name.trim().toLowerCase())
    ) ?? null
  );
}

export function parseCommand(text, integrations = []) {
  const command = text.trim();
  if (!command) return { type: "empty", command };

  const named = matchCustomByName(command, integrations);
  const wantsDeploy = DEPLOY_HINTS.test(command);
  const wantsTable = TABLE_HINTS.test(command);
  const wantsVerify = VERIFY_HINTS.test(command);
  const wantsVercel = VERCEL_HINTS.test(command);
  const wantsNetlify = NETLIFY_HINTS.test(command);
  const wantsStripe = STRIPE_HINTS.test(command);
  const wantsFirebase = FIREBASE_HINTS.test(command);
  const wantsEas = EAS_HINTS.test(command);
  const wantsWebhook = WEBHOOK_HINTS.test(command);

  if (named && !wantsTable && !wantsVerify) {
    return {
      type: "custom_integration",
      command,
      integrationId: named.id,
      integrationType: named.type,
    };
  }

  if (wantsVerify && !wantsDeploy && !wantsTable && !wantsStripe && !wantsEas) {
    return { type: "verify", command };
  }

  if (wantsStripe && !wantsDeploy && !wantsTable) {
    return { type: "stripe_charge", command };
  }

  if (wantsEas && !wantsTable) {
    return { type: "expo_build", command };
  }

  if (wantsFirebase && !wantsDeploy && !wantsTable) {
    return { type: "firebase_action", command };
  }

  if (wantsVercel && wantsDeploy) {
    return { type: "vercel_deploy", command };
  }

  if (wantsVercel && !wantsNetlify) {
    return { type: "vercel_deploy", command };
  }

  if (wantsWebhook || integrations.some((i) => i.type === "custom_webhook" && isIntegrationActive(i))) {
    const custom = integrations.find((i) => i.type === "custom_webhook" && isIntegrationActive(i));
    if (custom && (wantsWebhook || wantsDeploy)) {
      return {
        type: "custom_integration",
        command,
        integrationId: custom.id,
        integrationType: "custom_webhook",
      };
    }
  }

  if (wantsDeploy && wantsTable) {
    return { type: "pipeline", command };
  }

  if (wantsDeploy && wantsNetlify) {
    return { type: "deploy", command };
  }

  if (wantsDeploy && !wantsVercel) {
    return { type: "deploy", command };
  }

  if (wantsTable) {
    return { type: "table", command };
  }

  if (integrations.some((i) => isIntegrationActive(i))) {
    const first = integrations.find((i) => isIntegrationActive(i));
    return {
      type: "custom_integration",
      command,
      integrationId: first.id,
      integrationType: first.type,
    };
  }

  return { type: "deploy", command };
}

function isMockCredential(value) {
  if (!value?.trim()) return true;
  return value.trim().toLowerCase().startsWith("mock");
}

export function detectMode({ supabaseUrl, supabaseKey, netlifyToken, customIntegrations = [] }) {
  const flags = [];

  flags.push(
    !supabaseUrl?.trim() ||
      !supabaseKey?.trim() ||
      isMockCredential(supabaseUrl) ||
      isMockCredential(supabaseKey)
  );
  flags.push(!netlifyToken?.trim() || isMockCredential(netlifyToken));

  for (const integration of customIntegrations) {
    flags.push(!isIntegrationActive(integration) || isMockCredential(integration.apiKey));
  }

  if (flags.every(Boolean)) return "mock";
  if (flags.some(Boolean)) return "mixed";
  return "live";
}

export function humanizeOutcome(type, result, intent = null) {
  if (!result) return "Finished without a response.";

  const data = result.data || {};
  const label = intent?.integrationType
    ? integrationTypeLabel(intent.integrationType)
    : null;

  if (type === "verify") {
    return result.success
      ? "Supabase connection looks good. You're ready to run database actions."
      : "Supabase connection could not be confirmed. Double-check your URL and key.";
  }
  if (type === "deploy") {
    const url = data.deploy_url;
    return result.success
      ? url
        ? `Deployment started. Your site will be available at ${url}.`
        : "Deployment started successfully."
      : "Deployment did not complete. Review your Netlify token and try again.";
  }
  if (type === "table") {
    const name = data.table_name;
    return result.success
      ? name
        ? `Table plan ready for "${name}". Apply the generated SQL in Supabase when prompted.`
        : "Database table plan is ready."
      : "Could not prepare the table. Check Supabase credentials first.";
  }
  if (type === "vercel_deploy") {
    return result.success
      ? data.deploy_url
        ? `Vercel deployment queued. Preview at ${data.deploy_url}.`
        : "Vercel deployment started successfully."
      : "Vercel deployment did not complete. Check your token in the vault.";
  }
  if (type === "stripe_charge") {
    return result.success
      ? data.charge_id
        ? `Payment action recorded (${data.charge_id}).`
        : "Stripe action completed successfully."
      : "Stripe action failed. Verify your secret key.";
  }
  if (type === "firebase_action") {
    return result.success
      ? data.resource_id
        ? `Firebase update applied to ${data.resource_id}.`
        : "Firebase action completed."
      : "Firebase action could not be completed.";
  }
  if (type === "expo_build") {
    return result.success
      ? data.build_url
        ? `EAS build started. Track progress at ${data.build_url}.`
        : "Mobile build queued on Expo EAS."
      : "EAS build could not be started.";
  }
  if (type === "custom_integration") {
    return result.success
      ? result.message || `${label ?? "Integration"} responded successfully.`
      : `${label ?? "Custom integration"} did not complete. Check vault credentials.`;
  }
  return result.message || "Action completed.";
}

export function stepsForIntent(type, intent = null) {
  const name = intent?.integrationType
    ? integrationTypeLabel(intent.integrationType)
    : null;

  switch (type) {
    case "verify":
      return [
        "Reading your command",
        "Loading Supabase integration",
        "Verifying connection",
        "Wrapping up",
      ];
    case "deploy":
      return [
        "Reading your command",
        "Loading Netlify integration",
        "Starting deployment",
        "Wrapping up",
      ];
    case "table":
      return [
        "Reading your command",
        "Loading Supabase integration",
        "Designing table from your request",
        "Wrapping up",
      ];
    case "pipeline":
      return [
        "Reading your command",
        "Verifying Supabase",
        "Preparing database table",
        "Starting Netlify deployment",
        "Wrapping up",
      ];
    case "vercel_deploy":
      return [
        "Reading your command",
        "Loading Vercel from Integration Vault",
        "Preparing deployment",
        "Publishing to Vercel",
        "Wrapping up",
      ];
    case "stripe_charge":
      return [
        "Reading your command",
        "Loading Stripe from Integration Vault",
        "Validating payment details",
        "Processing charge",
        "Wrapping up",
      ];
    case "firebase_action":
      return [
        "Reading your command",
        "Loading Firebase from Integration Vault",
        "Applying backend changes",
        "Confirming update",
        "Wrapping up",
      ];
    case "expo_build":
      return [
        "Reading your command",
        "Loading Expo EAS from Integration Vault",
        "Queueing mobile build",
        "Waiting for build slot",
        "Wrapping up",
      ];
    case "custom_integration":
      return [
        "Reading your command",
        `Loading ${name ?? "custom integration"} from vault`,
        "Sending request to endpoint",
        "Processing response",
        "Wrapping up",
      ];
    default:
      return ["Reading your command"];
  }
}

export function serializeIntegrations(integrations) {
  return integrations.map((item) => ({
    id: item.id,
    type: item.type,
    name: item.name,
    api_key: item.apiKey,
    endpoint_url: item.endpointUrl?.trim() || null,
  }));
}
