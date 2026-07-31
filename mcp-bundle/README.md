# Zero Orchestrator MCP Server

Zero Orchestrator provides an MCP (Model Context Protocol) server that allows Claude Desktop and VS Code to interact with your development stack programmatically.

## Available Tools

- `verify_supabase_connection` - Verify Supabase credentials and connection
- `deploy_to_netlify` - Trigger a Netlify deployment
- `create_supabase_table` - Create a database table in Supabase based on natural language
- `register_integration` - Register a new integration in the vault
- `execute_vault_integration` - Execute an action using a registered vault integration
- `execute_local_command` - Execute a local terminal command via the zero-cli subprocess bridge

## Setup

### Prerequisites

1. Generate an API key from the Zero Orchestrator Developer page at `/developer`
2. Your API key will have the format `zo_live_<random_string>`

### Claude Desktop Setup

1. Open Claude Desktop settings
2. Navigate to "MCP Servers"
3. Add a new server with the following configuration:

```json
{
  "mcpServers": {
    "zero-orchestrator": {
      "command": "uvicorn",
      "args": ["main:app", "--host", "0.0.0.0", "--port", "8080"],
      "env": {
        "API_URL": "https://zero-orchestrator-api.onrender.com",
        "API_KEY": "your_zo_live_api_key_here"
      }
    }
  }
}
```

### VS Code Setup

1. Install the Claude for VS Code extension
2. Add the MCP server configuration to your VS Code settings:

```json
{
  "claude.mcpServers": {
    "zero-orchestrator": {
      "command": "uvicorn",
      "args": ["main:app", "--host", "0.0.0.0", "--port", "8080"],
      "env": {
        "API_URL": "https://zero-orchestrator-api.onrender.com",
        "API_KEY": "your_zo_live_api_key_here"
      }
    }
  }
}
```

### Remote Server Configuration

For remote MCP server access, configure the endpoint:

```json
{
  "mcpServers": {
    "zero-orchestrator": {
      "url": "https://zero-orchestrator-api.onrender.com/mcp",
      "headers": {
        "X-API-Key": "your_zo_live_api_key_here"
      }
    }
  }
}
```

## Authentication

All MCP tools require authentication via the `X-API-Key` header. Your API key is generated from the Developer page and is returned only once.

## Usage Examples

### Verify Supabase Connection

```
Please verify my Supabase connection with URL: https://myproject.supabase.co and anon key: my_anon_key
```

### Deploy to Netlify

```
Deploy my project to Netlify using token: my_netlify_token
```

### Create Supabase Table

```
Create a users table in Supabase with fields for name, email, and created_at
```

## Security

- API keys are hashed before storage in the database
- All MCP requests are authenticated via `X-API-Key` header
- API keys update `last_used_at` timestamp on each use
- Revoke API keys from the Developer page if compromised

## Troubleshooting

If you encounter authentication errors:
1. Verify your API key is active and has the correct format `zo_live_...`
2. Check that the API key hasn't been revoked
3. Ensure the MCP server endpoint is accessible

For cold start issues with Render free-tier:
- The first request may take up to 45 seconds
- Subsequent requests will be faster
- The frontend includes warm-up pings to mitigate this
