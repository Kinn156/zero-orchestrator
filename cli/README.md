# Zero-Terminal CLI

A local command-line interface for the Zero-Terminal Orchestrator that enables safe execution of terminal commands with human-in-the-loop approval and safety guardrails.

## Features

- **Safe Command Execution**: Blocks dangerous commands by default
- **Human-in-the-Loop Approval**: Requires explicit confirmation for risky operations
- **Backend Integration**: Connects to the Zero-Terminal Orchestrator backend
- **Subprocess Bridge**: MCP tool integration for AI agent command execution
- **Rich Terminal Output**: Beautiful formatted output using Rich library

## Installation

### From Source

```bash
cd cli
pip install -e .
```

### Dependencies

The CLI requires Python 3.8+ and the following packages:
- `typer` - CLI framework
- `requests` - HTTP client for backend communication
- `rich` - Terminal formatting

## Configuration

### Initialize CLI

Connect the CLI to your backend server:

```bash
zero init --backend-url http://localhost:8080
```

This will:
1. Test the backend connection
2. Save configuration to `~/.zero/config.json`
3. Display connection status

### View Configuration

```bash
zero config --show
```

### Reset Configuration

```bash
zero config --reset
```

## Usage

### Execute Commands

Execute local terminal commands with safety checks:

```bash
zero exec "git status"
zero exec "npm install"
zero exec "docker ps"
```

### Auto-Approve Commands

Skip confirmation prompts (use with caution):

```bash
zero exec "npm run build" --yes
```

### Check Status

View CLI configuration and backend connection status:

```bash
zero status
```

## Safety Guardrails

### Blocked Commands

The following dangerous command patterns are automatically blocked:

- `rm -rf /` - System destruction
- `sudo rm` - Privileged deletion
- `mkfs` - Filesystem formatting
- `dd if=` - Disk writing
- `chmod 777 /` - Permission escalation
- `shutdown`, `reboot` - System control
- Fork bombs and other destructive patterns

### Requires Approval

These commands require explicit user confirmation:

- File operations: `rm`, `del`, `rmdir`, `mv`, `cp`
- Permission changes: `chmod`, `chown`
- Privileged commands: `sudo`
- Docker destructive operations: `docker rm`, `docker rmi`
- Kubernetes deletions: `kubectl delete`
- Infrastructure destruction: `terraform destroy`

### Confirmation Prompt

When executing commands that require approval:

```bash
$ zero exec "rm -rf node_modules"

Command requires approval: rm -rf node_modules
Run this command? [y/N]: y
✓ Command executed successfully
```

## Backend Integration

### HTTP Endpoint

The backend provides a subprocess bridge endpoint:

```bash
POST /api/subprocess
Content-Type: application/json

{
  "command": "git status",
  "auto_approve": false
}
```

### MCP Tool

The `execute_local_command` MCP tool allows AI agents to request command execution:

```python
await mcp.call_tool(
    "execute_local_command",
    {
        "command": "npm install",
        "auto_approve": false
    }
)
```

**Note**: The MCP tool validates commands but actual execution must be performed by the local CLI for security reasons.

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   AI Agent  │         │   Backend    │         │   Local CLI │
│             │         │              │         │             │
│  MCP Tools  │───────▶│  Validation  │◀────────│  Execution  │
│             │         │  Logging     │         │  Safety     │
└─────────────┘         └──────────────┘         └─────────────┘
```

1. AI Agent requests command execution via MCP
2. Backend validates command and logs request
3. Local CLI receives command with safety checks
4. User approves if required
5. Command executes with subprocess
6. Results returned to backend

## Development

### Run in Development Mode

```bash
cd cli
python -m zero_cli.main --help
```

### Test Commands

```bash
# Test safe command
zero exec "echo 'Hello World'"

# Test approval required
zero exec "rm -rf test_dir"

# Test blocked command
zero exec "rm -rf /"
```

## Configuration File

The CLI stores configuration in `~/.zero/config.json`:

```json
{
  "backend_url": "http://localhost:8080",
  "version": "0.1.0"
}
```

## Security Considerations

1. **Local Execution Only**: Commands execute on the local machine where CLI is installed
2. **No Remote Execution**: Backend validates but does not execute commands
3. **User Approval**: Risky commands require explicit confirmation
4. **Pattern Blocking**: Dangerous patterns are blocked entirely
5. **Audit Logging**: All command requests are logged in backend
6. **Timeout Protection**: Commands timeout after 5 minutes

## Troubleshooting

### Backend Connection Failed

```bash
# Check backend is running
curl http://localhost:8080/health

# Reinitialize with correct URL
zero init --backend-url http://localhost:8080
```

### Command Blocked

If a command is blocked, review the safety guardrails. If you need to execute a blocked command, run it directly in your terminal (not through zero-cli).

### Permission Denied

Ensure the CLI has necessary permissions to execute commands. Some operations may require elevated privileges.

## License

MIT License - See LICENSE file for details.
