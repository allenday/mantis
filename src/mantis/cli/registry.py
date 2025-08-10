#!/usr/bin/env python3
"""
Registry command for the Mantis CLI - inspect and search agent registry.
"""

import json
from typing import Optional, Any, List

import rich_click as click
from rich.console import Console
from rich.table import Table

from .core import cli, use_global_options

console = Console()


def display_registry_table(agents_data: List[Any], verbose: bool = False, show_scores: bool = False) -> None:
    """Display a rich table of agents from the registry."""
    table = Table(title="🌐 Agent Registry", show_header=True, header_style="bold blue")

    if show_scores:
        # Narrower columns when showing scores to fit all 6 columns
        table.add_column("Name", style="cyan", width=18)
        table.add_column("Provider", style="green", width=12)
        table.add_column("URL", style="blue", width=25)
        table.add_column("Extensions", style="yellow", width=8, justify="center")
        table.add_column("Version", style="magenta", width=8)
        table.add_column("Score", style="bright_green", width=8, justify="right")
    else:
        # Wider columns when not showing scores
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Provider", style="green", width=15)
        table.add_column("URL", style="blue", width=30)
        table.add_column("Extensions", style="yellow", width=8, justify="center")
        table.add_column("Version", style="magenta", width=8)

    if not agents_data:
        if show_scores:
            table.add_row("No agents found", "", "", "", "", "")
        else:
            table.add_row("No agents found", "", "", "", "")
    else:
        for agent in agents_data:
            name = agent.get("name", "Unknown")
            provider = agent.get("provider", {}).get("organization", "Unknown")
            url = agent.get("url", "")
            extensions_count = str(len(agent.get("capabilities", {}).get("extensions", [])))
            version = agent.get("version", "")

            # Truncate long URLs for display based on column width
            url_width = 25 if show_scores else 30
            max_url_len = url_width - 3  # Leave room for "..."
            display_url = url if len(url) <= max_url_len else url[: max_url_len - 3] + "..."

            if show_scores:
                score = agent.get("similarity_score", "N/A")
                if isinstance(score, float):
                    score_str = f"{score:.3f}"
                else:
                    score_str = str(score)
                table.add_row(name, provider, display_url, extensions_count, version, score_str)
            else:
                table.add_row(name, provider, display_url, extensions_count, version)

    console.print(table)

    if verbose and agents_data:
        console.print(f"\n[dim]Total agents: {len(agents_data)}[/dim]")


@cli.group()
@use_global_options(["verbose"])
def registry(verbose: bool) -> None:
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
@click.option("--query", "-q", help="Search query for semantic/vector search")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of agents to display")
@click.option(
    "--similarity-threshold",
    "-t",
    type=float,
    default=0.0,
    help="Similarity threshold for vector search (0.0-1.0, default: 0.0)",
)
def list(
    registry: Optional[str],
    format: str,
    query: Optional[str],
    limit: int,
    similarity_threshold: float,
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
            console.print(f"[dim]Search query: {query} (vector search, threshold: {similarity_threshold})[/dim]")

    try:
        import requests

        jsonrpc_url = f"{registry_url}/jsonrpc"

        if query:
            # Use search_agents method for semantic search
            payload = {
                "jsonrpc": "2.0",
                "method": "search_agents",
                "params": {
                    "query": query,
                    "search_mode": "SEARCH_MODE_VECTOR",
                    "similarity_threshold": similarity_threshold,
                    "max_results": limit,
                },
                "id": 1,
            }
        else:
            # Use list_agents method for listing all agents
            payload = {"jsonrpc": "2.0", "method": "list_agents", "params": {}, "id": 1}

        if verbose:
            method = "search_agents" if query else "list_agents"
            console.print(f"[dim]Calling {method} on: {jsonrpc_url}[/dim]")

        response = requests.post(jsonrpc_url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()

        if "error" in result:
            console.print(f"[red]❌ Registry error: {result['error']['message']}[/red]")
            return 1

        # Extract agent data from response
        response_data = result.get("result", {})
        agents_data = response_data.get("agents", [])
        similarity_scores = response_data.get("similarity_scores", [])

        # Add similarity scores to agent data if available and sort by score descending
        if query and similarity_scores:
            for i, agent in enumerate(agents_data):
                if i < len(similarity_scores):
                    agent["similarity_score"] = similarity_scores[i]

            # Sort by similarity score descending (highest scores first)
            agents_data.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        # No local fallbacks - fail clearly if search returns no results
        if query and not agents_data and verbose:
            console.print(
                f"[yellow]⚠️  Vector search returned no results for '{query}' with threshold {similarity_threshold}[/yellow]"
            )
            console.print("[dim]Try lowering the similarity threshold with --similarity-threshold 0.3[/dim]")

        # Apply limit after sorting
        if len(agents_data) > limit:
            agents_data = agents_data[:limit]
            if verbose:
                console.print(f"[dim]Showing first {limit} agents (use --limit to change)[/dim]")

        if format == "json":
            # Output raw JSON
            print(json.dumps(agents_data, indent=2))
        else:
            # Display rich table with scores if query was used
            display_registry_table(agents_data, verbose, show_scores=bool(query))

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
