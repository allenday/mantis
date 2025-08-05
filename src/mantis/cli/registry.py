#!/usr/bin/env python3
"""
Registry command for the Mantis CLI - inspect and search agent registry.
"""

import json
from typing import Optional

import rich_click as click
from rich.console import Console
from rich.table import Table

from .core import cli, use_global_options

console = Console()


def display_registry_table(agents_data, verbose: bool = False) -> None:
    """Display a rich table of agents from the registry."""
    table = Table(title="🌐 Agent Registry", show_header=True, header_style="bold blue")
    table.add_column("Name", style="cyan", width=30)
    table.add_column("Provider", style="green", width=20)
    table.add_column("URL", style="blue", width=50)
    table.add_column("Skills", style="yellow", width=8, justify="center")
    table.add_column("Version", style="magenta", width=8)

    if not agents_data:
        table.add_row("No agents found", "", "", "", "")
    else:
        for agent in agents_data:
            name = agent.get("name", "Unknown")
            provider = agent.get("provider", {}).get("organization", "Unknown")
            url = agent.get("url", "")
            skills_count = str(len(agent.get("skills", [])))
            version = agent.get("version", "")

            # Truncate long URLs for display
            display_url = url if len(url) <= 47 else url[:44] + "..."

            table.add_row(name, provider, display_url, skills_count, version)

    console.print(table)

    if verbose and agents_data:
        console.print(f"\n[dim]Total agents: {len(agents_data)}[/dim]")


@cli.group()
@use_global_options(["verbose"])
def registry(verbose: bool):
    """
    Inspect and search the agent registry.
    """
    pass


@registry.command()
@use_global_options(["verbose"])
@click.option("--registry", help="Custom registry URL (defaults to configured registry)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table=rich table, json=raw JSON)",
)
@click.option("--query", "-q", help="Search query - WARNING: semantic search not supported by this registry")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of agents to display (filters locally)")
def list(
    registry: Optional[str],
    format: str,
    query: Optional[str],
    limit: int,
    verbose: bool,
) -> int:
    """
    List agents in the registry.

    Examples:
        mantis registry list
        mantis registry list --limit 5
        mantis registry list --format json
        mantis registry list --registry http://custom-registry:8080
    """

    # Use custom registry URL or default
    registry_url = registry
    if not registry_url:
        from ..config import DEFAULT_REGISTRY

        registry_url = DEFAULT_REGISTRY

    if verbose:
        console.print(f"[blue]🔍 Connecting to registry: {registry_url}[/blue]")
        if query:
            console.print(f"[dim]Search query: {query} (local text filtering)[/dim]")

    try:
        import requests

        # Use JSON-RPC to list all agents (only method available)
        jsonrpc_url = f"{registry_url}/jsonrpc"
        payload = {"jsonrpc": "2.0", "method": "list_agents", "params": {}, "id": 1}

        if verbose:
            console.print(f"[dim]Connecting to JSON-RPC endpoint: {jsonrpc_url}[/dim]")

        response = requests.post(jsonrpc_url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            console.print(f"[red]❌ Registry error: {result['error']['message']}[/red]")
            return 1

        # Extract agent data from response
        response_data = result.get("result", {})
        agents_data = response_data.get("agents", [])

        # Apply local filtering if query is provided
        if query:
            filtered_agents = []
            query_lower = query.lower()
            for agent in agents_data:
                # Search in name, description, and skills
                agent_text = (
                    agent.get("name", "").lower()
                    + " "
                    + agent.get("description", "").lower()
                    + " "
                    + " ".join(
                        [
                            skill.get("name", "") + " " + skill.get("description", "")
                            for skill in agent.get("skills", [])
                        ]
                    ).lower()
                )
                if query_lower in agent_text:
                    filtered_agents.append(agent)
            agents_data = filtered_agents

            if verbose:
                console.print(f"[dim]Found {len(agents_data)} agents matching query (local search)[/dim]")

        # Apply limit
        if len(agents_data) > limit:
            agents_data = agents_data[:limit]
            if verbose:
                console.print(f"[dim]Showing first {limit} agents (use --limit to change)[/dim]")

        if format == "json":
            # Output raw JSON
            print(json.dumps(agents_data, indent=2))
        else:
            # Display rich table
            display_registry_table(agents_data, verbose)

        return 0

    except requests.exceptions.RequestException as e:
        console.print(f"[red]❌ Failed to connect to registry: {e}[/red]")
        if verbose:
            console.print_exception()
        return 1
    except Exception as e:
        console.print(f"[red]❌ Registry inspection failed: {e}[/red]")
        if verbose:
            console.print_exception()
        return 1


# NOTE: registry ext and registry ping commands removed
# This registry implementation only supports list_agents method
