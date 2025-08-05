#!/usr/bin/env python3
"""
Agent command for the Mantis CLI - generate command only.
"""

import json
from pathlib import Path
from typing import Optional

import rich_click as click
from rich.console import Console

from .core import cli, use_global_options

console = Console()


def display_agent_card_summary(agent_card, verbose: bool = False) -> None:
    """Display a rich summary of AgentCard information with persona extensions."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from ..agent.card import ensure_mantis_agent_card
    
    # Always ensure we have a MantisAgentCard for rich display
    mantis_card = ensure_mantis_agent_card(agent_card)
    
    # Header with persona title
    title = mantis_card.persona_title if mantis_card.persona_title else mantis_card.agent_card.name
    console.print(f"\n[bold magenta]✨ {title}[/bold magenta]")
    
    # Basic info panel
    basic_info = f"""
[bold]Version:[/bold] {mantis_card.agent_card.version}
[bold]Provider:[/bold] [yellow]{mantis_card.agent_card.provider.organization}[/yellow]
[bold]A2A URL:[/bold] {mantis_card.agent_card.url}
[bold]Protocol:[/bold] {mantis_card.agent_card.protocol_version} via {mantis_card.agent_card.preferred_transport}
"""
    console.print(Panel(basic_info.strip(), title="Agent Overview", border_style="blue"))
    
    # Persona Characteristics
    char = mantis_card.persona_characteristics
    
    # Core principles
    if char.core_principles:
        principles_text = "\n".join([f"• {p}" for p in char.core_principles])
        console.print(Panel(principles_text, title="🎯 Core Principles", border_style="cyan"))
    
    # Communication style and thinking patterns in columns
    panels = []
    if char.communication_style:
        panels.append(Panel(char.communication_style, title="💬 Communication Style", border_style="green"))
    if char.thinking_patterns:
        patterns_text = "\n".join([f"• {p}" for p in char.thinking_patterns])
        panels.append(Panel(patterns_text, title="🧠 Thinking Patterns", border_style="yellow"))
    
    if panels:
        console.print(Columns(panels, equal=True, expand=True))
    
    # Original persona prompt
    if char.original_content:
        from rich.syntax import Syntax
        syntax = Syntax(char.original_content, "markdown", theme="monokai", word_wrap=True)
        console.print(Panel(syntax, title="📜 Original Persona Prompt", border_style="dim", expand=True))
    
    # Competency Scores and Role Adaptation
    comp = mantis_card.competency_scores
    
    # Competency scores and role adaptation combined table
    if comp.competency_scores or comp.role_adaptation:
        comp_table = Table(title="📊 Competency & Role Scores", show_header=True, header_style="bold blue")
        comp_table.add_column("Competency", style="cyan", width=60)
        comp_table.add_column("Score", style="green", justify="right", width=7)
        comp_table.add_column("Bar", style="blue", width=22)
        
        # Add competency scores
        if comp.competency_scores:
            for comp_name, score in comp.competency_scores.items():
                # Create visual bar chart
                bar_length = 20
                filled_length = int(score * bar_length)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                
                # Clean up competency name for better display
                clean_name = comp_name.title().replace("_", " ")
                
                # Dynamic score color based on value
                if score >= 0.9:
                    score_color = "bright_green"
                elif score >= 0.8:
                    score_color = "green"
                elif score >= 0.7:
                    score_color = "yellow"
                elif score >= 0.5:
                    score_color = "orange3"
                else:
                    score_color = "red"
                
                comp_table.add_row(clean_name, f"[{score_color}]{score:.2f}[/{score_color}]", bar)
            
            # Add section break after competency scores
            if comp.role_adaptation and (comp.role_adaptation.leader_score or comp.role_adaptation.follower_score or comp.role_adaptation.narrator_score):
                comp_table.add_section()
        
        # Add role adaptation scores
        role = comp.role_adaptation
        if role.leader_score or role.follower_score or role.narrator_score:
            # Add section header
            comp_table.add_row("[bold magenta]Role Adaptation Scores[/bold magenta]", "[bold magenta]Score[/bold magenta]", "[bold magenta]Bar[/bold magenta]", style="bold magenta", end_section=True)
            
            roles = [
                ("• Leader Role", role.leader_score),
                ("• Follower Role", role.follower_score), 
                ("• Narrator Role", role.narrator_score)
            ]
            
            for role_name, score in roles:
                if score > 0:  # Only show roles with scores
                    # Create visual bar chart for roles
                    bar_length = 20
                    filled_length = int(score * bar_length)
                    bar = "█" * filled_length + "░" * (bar_length - filled_length)
                    
                    # Dynamic score color based on value
                    if score >= 0.8:
                        score_color = "bright_green"
                    elif score >= 0.6:
                        score_color = "green" 
                    elif score >= 0.4:
                        score_color = "yellow"
                    else:
                        score_color = "red"
                    
                    comp_table.add_row(role_name, f"[{score_color}]{score:.2f}[/{score_color}]", bar)
            
            if role.preferred_role:
                # Use the proper enum from protobuf
                from ..proto.mantis.v1.mantis_persona_pb2 import RolePreference
                role_names = {
                    RolePreference.ROLE_PREFERENCE_LEADER: "Leader",
                    RolePreference.ROLE_PREFERENCE_FOLLOWER: "Follower", 
                    RolePreference.ROLE_PREFERENCE_NARRATOR: "Narrator"
                }
                role_name = role_names.get(role.preferred_role, f"Role {role.preferred_role}")
                comp_table.add_row("• Preferred Role", f"[bold bright_cyan]{role_name}[/bold bright_cyan]", "✨ Primary")
            
        console.print(comp_table)
    
    # Domain expertise in separate 2-column table
    domain = mantis_card.domain_expertise
    if domain.primary_domains or domain.methodologies:
        domain_table = Table(title="🎯 Domain Expertise", show_header=True, header_style="bold cyan")
        domain_table.add_column("Primary Domains", style="red", width=60)
        domain_table.add_column("Methodologies", style="blue", width=60)
        
        # Get max length to align rows
        primary_count = len(domain.primary_domains) if domain.primary_domains else 0
        method_count = len(domain.methodologies) if domain.methodologies else 0
        max_rows = max(primary_count, method_count)
        
        for i in range(max_rows):
            primary_item = f"• {domain.primary_domains[i].strip()}" if i < primary_count else ""
            method_item = f"• {domain.methodologies[i].strip()}" if i < method_count else ""
            domain_table.add_row(primary_item, method_item)
        
        console.print(domain_table)
    
    # A2A Skills as bulleted list
    if mantis_card.agent_card.skills:
        skills_lines = []
        for skill in mantis_card.agent_card.skills:
            skills_lines.append(f"• [bold]{skill.name}[/bold] - {skill.description}")
            if skill.examples:
                for example in skill.examples:
                    skills_lines.append(f"    [dim]Example: {example}[/dim]")
        
        skills_text = "\n".join(skills_lines)
        console.print(Panel(skills_text, title=f"🎯 A2A Skills ({len(mantis_card.agent_card.skills)} total)", border_style="green"))
    
    # Extensions summary
    console.print(f"\n[bold magenta]Extensions:[/bold magenta] {len(mantis_card.agent_card.capabilities.extensions)} total")
    if mantis_card.agent_card.capabilities.extensions:
        for ext in mantis_card.agent_card.capabilities.extensions:
            console.print(f"  • [bold]{ext.uri}[/bold] - {ext.description}")
    
    if verbose:
        # Show full AgentCard as JSON
        console.print("\n[bold dim]Full AgentCard JSON:[/bold dim]")
        from rich.syntax import Syntax
        from google.protobuf.json_format import MessageToJson
        
        syntax = Syntax(
            MessageToJson(mantis_card.agent_card, preserving_proto_field_name=True, indent=2),
            "json",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        console.print(Panel(syntax, title=f"AgentCard: {mantis_card.agent_card.name}", border_style="dim", expand=False))


@cli.group()
@use_global_options(["verbose"])
def agent(verbose: bool):
    """
    Generate and work with agents.
    """
    pass


@agent.command()
@use_global_options(["verbose"])
@click.option("--source", "-s", type=click.Choice(["file", "registry", "agent"]), required=True, help="Source type for AgentCard")
@click.option("--registry", help="Custom registry URL (defaults to configured registry)")
@click.option("--format", "-f", type=click.Choice(["display", "json"]), default="display", help="Output format (display=rich format, json=raw JSON)")
@click.argument("identifier", required=True)
def inspect(
    source: str,
    registry: Optional[str],
    format: str,
    identifier: str,
    verbose: bool,
) -> int:
    """
    Inspect an AgentCard from various sources.

    IDENTIFIER is the path/URL/ID depending on source:
    - file: path to AgentCard JSON file
    - registry: agent URL identifier in registry
    - agent: direct agent URL

    Examples:
        mantis agent inspect --source file agents/cards/steve_jobs_persona.json
        mantis agent inspect --source file agents/cards/steve_jobs_persona.json --format json
        mantis agent inspect --source registry agent-123
        mantis agent inspect --source registry agent-123 --registry http://custom-registry:8080
        mantis agent inspect --source agent http://agent.example.com
    """

    # Handle different source types
    if source == "registry":
        # Use custom registry URL or default
        registry_url = registry
        if not registry_url:
            from ..config import DEFAULT_REGISTRY
            registry_url = DEFAULT_REGISTRY
        
        if verbose:
            console.print(f"[blue]🔍 Fetching agent from registry: {registry_url}[/blue]")
            console.print(f"[dim]Looking for agent: {identifier}[/dim]")

        try:
            import requests
            
            # Use JSON-RPC to list all agents
            jsonrpc_url = f"{registry_url}/jsonrpc"
            payload = {
                "jsonrpc": "2.0",
                "method": "list_agents",
                "params": {},
                "id": 1
            }
            
            if verbose:
                console.print(f"[dim]Connecting to JSON-RPC endpoint: {jsonrpc_url}[/dim]")
            
            response = requests.post(jsonrpc_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                console.print(f"[red]❌ Registry error: {result['error']['message']}[/red]")
                return 1
            
            agents = result.get("result", {}).get("agents", [])
            
            # Find agent by URL
            for agent_data in agents:
                if agent_data.get("url") == identifier:
                    from a2a.types import AgentCard
                    agent_card = AgentCard.model_validate(agent_data)
                    
                    if verbose:
                        console.print(f"[dim]✅ Agent found: {agent_card.name}[/dim]")
                    
                    if format == "json":
                        from google.protobuf.json_format import MessageToJson
                        print(MessageToJson(agent_card, preserving_proto_field_name=True, indent=2))
                    else:
                        display_agent_card_summary(agent_card, verbose)
                    return 0
            
            # Agent not found
            console.print(f"[red]❌ Agent not found: {identifier}[/red]")
            if verbose:
                available_urls = [agent.get("url", "unknown") for agent in agents]
                console.print(f"[dim]Available agents: {', '.join(available_urls)}[/dim]")
            return 1

        except Exception as e:
            console.print(f"[red]❌ Failed to fetch from registry: {e}[/red]")
            if verbose:
                console.print_exception()
            return 1

    elif source == "agent":
        console.print("[yellow]⚠️  Direct agent inspection not yet implemented[/yellow]")
        console.print(f"[dim]Would inspect agent at: {identifier}[/dim]")
        return 1

    elif source == "file":
        # Convert identifier to Path for file operations
        file_path = Path(identifier)
        
        if not file_path.exists():
            console.print(f"[red]❌ File not found: {identifier}[/red]")
            return 1
        
        if verbose:
            console.print(f"[blue]🔍 Loading AgentCard from: {file_path}[/blue]")

        try:
            # Load and validate AgentCard
            with open(file_path, 'r') as f:
                agent_data = json.load(f)

            # Load AgentCard from JSON (handles both formats)
            from ..agent.card import load_agent_card_from_json
            agent_card = load_agent_card_from_json(agent_data)

            if verbose:
                console.print(f"[dim]✅ Valid AgentCard loaded: {agent_card.agent_card.name}[/dim]")

            # Display or output the AgentCard
            if format == "json":
                from google.protobuf.json_format import MessageToJson
                print(MessageToJson(agent_card, preserving_proto_field_name=True, indent=2))
            else:
                display_agent_card_summary(agent_card, verbose)

            return 0

        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Invalid JSON in {identifier}: {e}[/red]")
            return 1
        except Exception as e:
            console.print(f"[red]❌ Failed to load AgentCard: {e}[/red]")
            if verbose:
                console.print_exception()
            return 1

    return 1


@agent.command()
@use_global_options(["input", "output", "model", "verbose"])
@click.option("--quiet", "-q", is_flag=True, help="Suppress display output, only show errors")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path), required=False)
def generate(
    input_file: Optional[Path],
    input: Optional[Path],
    output: Optional[Path],
    model: Optional[str],
    verbose: bool,
    quiet: bool,
) -> int:
    """
    Generate AgentCard from markdown file.

    Load and process a persona markdown file, converting it to A2A AgentCard format
    for direct use in the agent system.

    Examples:
        mantis agent generate persona.md
        mantis agent generate --input persona.md --output agent.json
        mantis agent generate persona.md --output ./cache/
    """
    # Handle input precedence: argument > --input option
    actual_input = input_file or input
    if not actual_input:
        console.print("[red]❌ No input file specified[/red]")
        console.print("[dim]Use: mantis agent generate <file> or --input <file>[/dim]")
        return 1

    if verbose:
        console.print(f"[blue]🔍 Loading persona from: {actual_input}[/blue]")

    try:
        # Generate AgentCard using new namespace
        from ..agent.card import generate

        # Generate AgentCard from markdown
        agent_card = generate(str(actual_input), model=model)

        if not quiet:
            # Get the name from the appropriate source
            agent_name = agent_card.agent_card.name if hasattr(agent_card, 'agent_card') else agent_card.name
            console.print(f"\n[bold green]✅ Successfully generated AgentCard: {agent_name}[/bold green]")

            # Display AgentCard information
            display_agent_card_summary(agent_card, verbose)

        # Save output if requested
        if output:
            if output.is_dir() or str(output).endswith("/"):
                # Directory output - create file based on persona name
                output_dir = output if output.is_dir() else Path(output)
                output_dir.mkdir(parents=True, exist_ok=True)
                # Get name from appropriate source
                persona_name = agent_card.agent_card.name if hasattr(agent_card, 'agent_card') else agent_card.name
                filename = f"{persona_name.lower().replace(' ', '_')}_persona.json"
                output_file = output_dir / filename
            else:
                # File output
                output_file = output
                if output_file.parent != Path("."):
                    output_file.parent.mkdir(parents=True, exist_ok=True)

            # Save AgentCard data (final A2A protocol format)
            from google.protobuf.json_format import MessageToJson
            with open(output_file, "w") as f:
                json_str = MessageToJson(agent_card, preserving_proto_field_name=True, indent=2)
                f.write(json_str)

            if not quiet:
                console.print(f"\n[bold green]✅ AgentCard saved to: {output_file}[/bold green]")

                if verbose:
                    # Get appropriate references for MantisAgentCard vs AgentCard
                    base_card = agent_card.agent_card if hasattr(agent_card, 'agent_card') else agent_card
                    skills_count = len(base_card.skills)
                    extensions_count = len(base_card.capabilities.extensions)
                    console.print(
                        f"[dim]Saved A2A AgentCard with {skills_count} skills and {extensions_count} extensions[/dim]"
                    )
                    console.print(f"[dim]A2A URL: {base_card.url}[/dim]")

        return 0

    except Exception as e:
        console.print(f"[red]❌ Failed to generate AgentCard: {e}[/red]")
        if verbose:
            console.print_exception()
        return 1