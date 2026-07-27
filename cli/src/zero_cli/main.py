"""Zero-Terminal Orchestrator CLI main entry point."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests
import typer
from rich.console import Console
from rich.prompt import Confirm

app = typer.Typer(
    name="zero",
    help="Zero-Terminal Orchestrator CLI - Local command execution with safety guardrails",
    add_completion=False,
)
console = Console()

# Dangerous command patterns to block
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "sudo rm",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "chmod 777 /",
    "chown -R",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "format",
    "del /f /s /q",
    "rmdir /s /q",
]

# Commands that require explicit approval
REQUIRES_APPROVAL = [
    "rm",
    "del",
    "rmdir",
    "mv",
    "cp",
    "chmod",
    "chown",
    "sudo",
    "docker rm",
    "docker rmi",
    "kubectl delete",
    "terraform destroy",
]


def get_config_path() -> Path:
    """Get the path to the zero-cli config file."""
    config_dir = Path.home() / ".zero"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def load_config() -> dict:
    """Load the zero-cli configuration."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save the zero-cli configuration."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def is_dangerous(command: str) -> tuple[bool, str]:
    """Check if a command is dangerous."""
    command_lower = command.lower()
    
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in command_lower:
            return True, f"Contains dangerous pattern: {pattern}"
    
    return False, ""


def requires_approval(command: str) -> bool:
    """Check if a command requires explicit user approval."""
    command_lower = command.lower()
    for pattern in REQUIRES_APPROVAL:
        if pattern.lower() in command_lower:
            return True
    return False


def execute_command(command: str, auto_approve: bool = False) -> dict:
    """Execute a local terminal command with safety checks."""
    # Check for dangerous commands
    is_danger, reason = is_dangerous(command)
    if is_danger:
        return {
            "success": False,
            "error": f"Command blocked: {reason}",
            "command": command,
        }
    
    # Check if approval is required
    needs_approval = requires_approval(command)
    if needs_approval and not auto_approve:
        console.print(f"\n[bold yellow]Command requires approval:[/bold yellow] {command}")
        if not Confirm.ask("Run this command?", default=False):
            return {
                "success": False,
                "error": "Command cancelled by user",
                "command": command,
            }
    
    try:
        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 5 minutes",
            "command": command,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command,
        }


@app.command()
def init(
    backend_url: str = typer.Option(
        "http://localhost:8080",
        "--backend-url",
        "-u",
        help="Backend server URL"
    )
) -> None:
    """Initialize zero-cli and connect to the backend server."""
    console.print("[bold blue]Initializing Zero-Terminal CLI...[/bold blue]\n")
    
    # Test backend connection
    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        if response.status_code == 200:
            console.print(f"[green][OK][/green] Backend server reachable at {backend_url}")
        else:
            console.print(f"[red][FAIL][/red] Backend server returned status {response.status_code}")
            raise typer.Exit(1)
    except requests.RequestException as e:
        console.print(f"[red][FAIL][/red] Failed to connect to backend: {e}")
        raise typer.Exit(1)
    
    # Save configuration
    config = {
        "backend_url": backend_url,
        "version": "0.1.0",
    }
    save_config(config)
    
    console.print(f"[green][OK][/green] Configuration saved to {get_config_path()}")
    console.print("\n[bold green]Zero-Terminal CLI initialized successfully![/bold green]")
    console.print(f"Backend URL: {backend_url}")


@app.command()
def exec(
    command: str = typer.Argument(..., help="Command to execute"),
    auto_approve: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-approve without confirmation"
    )
) -> None:
    """Execute a local terminal command with safety guardrails."""
    console.print(f"[bold blue]Executing:[/bold blue] {command}\n")
    
    result = execute_command(command, auto_approve=auto_approve)
    
    if result["success"]:
        console.print("[green][OK][/green] Command executed successfully")
        if result.get("stdout"):
            console.print(f"\n[bold]Output:[/bold]\n{result['stdout']}")
        if result.get("stderr"):
            console.print(f"\n[bold red]Errors:[/bold red]\n{result['stderr']}")
    else:
        console.print(f"[red][FAIL][/red] {result.get('error', 'Command failed')}")
        if result.get("stderr"):
            console.print(f"\n[bold red]Errors:[/bold red]\n{result['stderr']}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show zero-cli configuration and connection status."""
    config = load_config()
    
    if not config:
        console.print("[yellow]Zero-Terminal CLI not initialized. Run 'zero init' first.[/yellow]")
        raise typer.Exit(1)
    
    console.print("[bold blue]Zero-Terminal CLI Status[/bold blue]\n")
    console.print(f"Backend URL: {config.get('backend_url', 'Not configured')}")
    console.print(f"Version: {config.get('version', 'Unknown')}")
    console.print(f"Config: {get_config_path()}")
    
    # Test connection
    try:
        response = requests.get(f"{config['backend_url']}/health", timeout=5)
        if response.status_code == 200:
            console.print(f"\n[green][OK][/green] Backend connection: [green]Online[/green]")
        else:
            console.print(f"\n[red][FAIL][/red] Backend connection: [red]Offline[/red] (HTTP {response.status_code})")
    except requests.RequestException:
        console.print(f"\n[red][FAIL][/red] Backend connection: [red]Offline[/red]")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    reset: bool = typer.Option(False, "--reset", help="Reset configuration"),
) -> None:
    """Manage zero-cli configuration."""
    if reset:
        config_path = get_config_path()
        if config_path.exists():
            config_path.unlink()
            console.print(f"[green][OK][/green] Configuration reset")
        else:
            console.print("[yellow]No configuration to reset[/yellow]")
        return
    
    if show:
        config = load_config()
        if config:
            console.print(json.dumps(config, indent=2))
        else:
            console.print("[yellow]No configuration found[/yellow]")
        return
    
    console.print("Use 'zero config --show' to view configuration")
    console.print("Use 'zero config --reset' to reset configuration")


if __name__ == "__main__":
    app()
