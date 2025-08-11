#!/usr/bin/env python3
"""
Agent command for the Mantis CLI - generate command only.
"""

import json
from pathlib import Path
from typing import Optional, Any

import rich_click as click
from rich.console import Console

from .core import cli, use_global_options

console = Console()


def display_agent_card_summary(agent_card: Any, verbose: bool = False) -> None:
    """Display a rich summary of AgentCard information with persona extensions."""
    from rich.panel import Panel
    from rich.table import Table
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

    # We'll show extension data after the base AgentCard information

    # A2A Skills as bulleted list
    if mantis_card.agent_card.skills:
        skills_lines = []
        for skill in mantis_card.agent_card.skills:
            skills_lines.append(f"• [bold]{skill.name}[/bold] - {skill.description}")
            if skill.examples:
                for example in skill.examples:
                    skills_lines.append(f"    [dim]Example: {example}[/dim]")

        skills_text = "\n".join(skills_lines)
        console.print(
            Panel(
                skills_text, title=f"🎯 A2A Skills ({len(mantis_card.agent_card.skills)} total)", border_style="green"
            )
        )

    # Extension Data section (removed redundant Extensions listing)
    if mantis_card.agent_card.capabilities.extensions:
        console.print(
            f"\n[bold cyan]📋 Extension Data ({len(mantis_card.agent_card.capabilities.extensions)} extensions):[/bold cyan]"
        )

        # Persona Characteristics from extension
        char = mantis_card.persona_characteristics
        if char.core_principles or char.communication_style or char.thinking_patterns:
            # Find the persona-characteristics extension for header info
            persona_ext = None
            for ext in mantis_card.agent_card.capabilities.extensions:
                if ext.uri == "https://mantis.ai/extensions/persona-characteristics/v1":
                    persona_ext = ext
                    break

            if persona_ext:
                console.print(f"\n• [bold]{persona_ext.description}:[/bold]")
                console.print(f"  [dim]AgentExtension URI:[/dim] {persona_ext.uri}")
                console.print(f"  [dim]Required:[/dim] {persona_ext.required}")
                console.print("")  # Empty line before data

            # Original persona prompt as part of persona-characteristics extension
            if char.original_content:
                console.print("  [dim]↳ Original source content from persona-characteristics extension:[/dim]")
                from rich.syntax import Syntax

                syntax = Syntax(char.original_content, "markdown", theme="monokai", word_wrap=True)
                console.print(Panel(syntax, title="📜 Original Persona Prompt", border_style="dim", expand=True))
                console.print("")  # Empty line before table

            # Create a single consolidated persona characteristics table
            persona_table = Table(
                title="🎭 Persona Characteristics", show_header=True, header_style="bold magenta", show_lines=True
            )
            persona_table.add_column("Attribute", style="cyan", width=25)
            persona_table.add_column("Details", style="white", width=95)

            # Add core principles
            if char.core_principles:
                principles_text = "\n".join([f"• {p}" for p in char.core_principles])
                persona_table.add_row("Core Principles", principles_text)

            # Add communication style
            if char.communication_style:
                persona_table.add_row("Communication Style", char.communication_style)

            # Add thinking patterns
            if char.thinking_patterns:
                patterns_text = "\n".join([f"• {p}" for p in char.thinking_patterns])
                persona_table.add_row("Thinking Patterns", patterns_text)

            # Add characteristic phrases
            if char.characteristic_phrases:
                phrases_text = "\n".join([f'• "{p}"' for p in char.characteristic_phrases])
                persona_table.add_row("Characteristic Phrases", phrases_text)

            # Add behavioral tendencies
            if char.behavioral_tendencies:
                tendencies_text = "\n".join([f"• {t}" for t in char.behavioral_tendencies])
                persona_table.add_row("Behavioral Tendencies", tendencies_text)

            # Add decision framework
            if char.decision_framework:
                persona_table.add_row("Decision Framework", char.decision_framework)

            console.print(persona_table)

        # Competency Scores from extension
        comp = mantis_card.competency_scores

        if comp.competency_scores or comp.role_adaptation:
            # Find the competency-scores extension for header info
            competency_ext = None
            for ext in mantis_card.agent_card.capabilities.extensions:
                if ext.uri == "https://mantis.ai/extensions/competency-scores/v1":
                    competency_ext = ext
                    break

            if competency_ext:
                console.print(f"\n• [bold]{competency_ext.description}:[/bold]")
                console.print(f"  [dim]AgentExtension URI:[/dim] {competency_ext.uri}")
                console.print(f"  [dim]Required:[/dim] {competency_ext.required}")
                console.print("")  # Empty line before data

            # Create separate tables for competency scores and role adaptation

            # Competency Scores Table
            if comp.competency_scores:
                try:
                    comp_table = Table(title="📊 Competency Scores", show_header=True, header_style="bold blue")
                    comp_table.add_column("Competency", style="cyan", width=60)
                    comp_table.add_column("Score", style="green", justify="right", width=7)
                    comp_table.add_column("Bar", style="blue", width=22)

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

                    console.print(comp_table)

                except Exception as e:
                    console.print(f"[red]❌ Error creating competency scores table: {e}[/red]")
                    if verbose:
                        console.print_exception()

            # Role Adaptation Table
            role = comp.role_adaptation
            if role.leader_score or role.follower_score or role.narrator_score or role.preferred_role:
                role_table = Table(title="🎭 Role Adaptation", show_header=True, header_style="bold magenta")
                role_table.add_column("Role Aspect", style="cyan", width=60)
                role_table.add_column("Score/Value", style="green", justify="right", width=7)
                role_table.add_column("Indicator", style="magenta", width=22)

                # Add role scores
                roles = [
                    ("Leader Score", role.leader_score),
                    ("Follower Score", role.follower_score),
                    ("Narrator Score", role.narrator_score),
                ]

                for role_name, score in roles:
                    if score is not None:  # Show all roles with defined scores (including 0.0)
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

                        role_table.add_row(role_name, f"[{score_color}]{score:.2f}[/{score_color}]", bar)

                # Add preferred role if exists
                if role.preferred_role:
                    # Use the proper enum from protobuf
                    from ..proto.mantis.v1.mantis_persona_pb2 import RolePreference

                    role_names = {
                        RolePreference.ROLE_PREFERENCE_LEADER: "Leader",
                        RolePreference.ROLE_PREFERENCE_FOLLOWER: "Follower",
                        RolePreference.ROLE_PREFERENCE_NARRATOR: "Narrator",
                    }
                    preferred_role_name = role_names.get(role.preferred_role, f"Role {role.preferred_role}")
                    role_table.add_row(
                        "Preferred Role", f"[bold bright_cyan]{preferred_role_name}[/bold bright_cyan]", "✨ Primary"
                    )

                console.print(role_table)

        # Domain Expertise from extension
        domain = mantis_card.domain_expertise
        if domain.primary_domains or domain.methodologies or domain.secondary_domains or domain.tools_and_frameworks:
            # Find the domain-expertise extension for header info
            domain_ext = None
            for ext in mantis_card.agent_card.capabilities.extensions:
                if ext.uri == "https://mantis.ai/extensions/domain-expertise/v1":
                    domain_ext = ext
                    break

            if domain_ext:
                console.print(f"\n• [bold]{domain_ext.description}:[/bold]")
                console.print(f"  [dim]AgentExtension URI:[/dim] {domain_ext.uri}")
                console.print(f"  [dim]Required:[/dim] {domain_ext.required}")
                console.print("")  # Empty line before data

            # Create a single 2x2 table for all domain expertise data
            domain_table = Table(title="🎯 Domain Expertise", show_header=True, header_style="bold cyan")
            domain_table.add_column("Primary Domains", style="red", width=60)
            domain_table.add_column("Secondary Domains", style="blue", width=60)

            # Get max length to align rows for domains section
            primary_count = len(domain.primary_domains) if domain.primary_domains else 0
            secondary_count = len(domain.secondary_domains) if domain.secondary_domains else 0
            max_domain_rows = max(primary_count, secondary_count)

            # Add domain rows
            for i in range(max_domain_rows):
                primary_item = f"• {domain.primary_domains[i].strip()}" if i < primary_count else ""
                secondary_item = f"• {domain.secondary_domains[i].strip()}" if i < secondary_count else ""
                domain_table.add_row(primary_item, secondary_item)

            # Add section break if we have both domains and methodologies/tools
            if (domain.primary_domains or domain.secondary_domains) and (
                domain.methodologies or domain.tools_and_frameworks
            ):
                domain_table.add_section()

            # Add section header for methodologies and tools
            if domain.methodologies or domain.tools_and_frameworks:
                domain_table.add_row(
                    "[bold cyan]Methodologies[/bold cyan]",
                    "[bold cyan]Tools & Frameworks[/bold cyan]",
                    style="bold cyan",
                    end_section=True,
                )

                # Get max length for methodologies and tools section
                method_count = len(domain.methodologies) if domain.methodologies else 0
                tools_count = len(domain.tools_and_frameworks) if domain.tools_and_frameworks else 0
                max_method_rows = max(method_count, tools_count)

                # Add methodology and tools rows
                for i in range(max_method_rows):
                    method_item = f"• {domain.methodologies[i].strip()}" if i < method_count else ""
                    tools_item = f"• {domain.tools_and_frameworks[i].strip()}" if i < tools_count else ""
                    domain_table.add_row(method_item, tools_item)

            console.print(domain_table)

        # Skills Summary from extension
        skills = mantis_card.skills_summary
        if (
            skills.primary_skill_tags
            or skills.secondary_skill_tags
            or skills.skill_overview
            or skills.signature_abilities
        ):
            # Find the skills-summary extension for header info
            skills_ext = None
            for ext in mantis_card.agent_card.capabilities.extensions:
                if ext.uri == "https://mantis.ai/extensions/skills-summary/v1":
                    skills_ext = ext
                    break

            if skills_ext:
                console.print(f"\n• [bold]{skills_ext.description}:[/bold]")
                console.print(f"  [dim]AgentExtension URI:[/dim] {skills_ext.uri}")
                console.print(f"  [dim]Required:[/dim] {skills_ext.required}")
                console.print("")  # Empty line before data

            # Create skills summary table
            skills_table = Table(title="🛠️ Skills Summary", show_header=True, header_style="bold magenta")
            skills_table.add_column("Primary Skills", style="green", width=50)
            skills_table.add_column("Secondary Skills", style="blue", width=50)

            # Add skill tags rows
            primary_count = len(skills.primary_skill_tags) if skills.primary_skill_tags else 0
            secondary_count = len(skills.secondary_skill_tags) if skills.secondary_skill_tags else 0
            max_skill_rows = max(primary_count, secondary_count)

            for i in range(max_skill_rows):
                primary_item = f"• {skills.primary_skill_tags[i]}" if i < primary_count else ""
                secondary_item = f"• {skills.secondary_skill_tags[i]}" if i < secondary_count else ""
                skills_table.add_row(primary_item, secondary_item)

            console.print(skills_table)

            # Skills overview
            if skills.skill_overview:
                overview_panel = Panel(
                    skills.skill_overview, title="📋 Skills Overview", border_style="magenta", padding=(1, 2)
                )
                console.print(overview_panel)

            # Signature abilities
            if skills.signature_abilities:
                abilities_text = "\n".join([f"• {ability}" for ability in skills.signature_abilities])
                abilities_panel = Panel(
                    abilities_text, title="⭐ Signature Abilities", border_style="bright_magenta", padding=(1, 2)
                )
                console.print(abilities_panel)

    else:
        console.print("\n[bold cyan]📋 Extension Data (0 extensions):[/bold cyan]")
        console.print("[dim]No extensions defined[/dim]")

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
        console.print(
            Panel(syntax, title=f"AgentCard: {mantis_card.agent_card.name}", border_style="dim", expand=False)
        )


@cli.group()
@use_global_options(["verbose"])
def agent(verbose: bool) -> None:
    """
    Generate and work with agents.
    """
    pass


@agent.command()
@use_global_options(["verbose"])
@click.option(
    "--source", "-s", type=click.Choice(["file", "registry", "agent"]), required=True, help="Source type for AgentCard"
)
@click.option("--registry", help="Custom registry URL (defaults to configured registry)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["display", "json"]),
    default="display",
    help="Output format (display=rich format, json=raw JSON)",
)
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
            payload = {"jsonrpc": "2.0", "method": "list_agents", "params": {}, "id": 1}

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
                    try:
                        # Use the same loading function as file inspect to get full MantisAgentCard
                        from ..agent.card import load_agent_card_from_json

                        agent_card = load_agent_card_from_json(agent_data)

                        if verbose:
                            agent_name = (
                                agent_card.agent_card.name if hasattr(agent_card, "agent_card") else agent_card.name
                            )
                            console.print(f"[dim]✅ Agent found: {agent_name}[/dim]")

                        if format == "json":
                            from google.protobuf.json_format import MessageToJson

                            print(MessageToJson(agent_card, preserving_proto_field_name=True, indent=2))
                        else:
                            display_agent_card_summary(agent_card, verbose)
                        return 0
                    except Exception as e:
                        console.print(f"[red]❌ Failed to parse agent data: {e}[/red]")
                        if verbose:
                            console.print_exception()
                        return 1

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
            with open(file_path, "r") as f:
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
            agent_name = agent_card.agent_card.name if hasattr(agent_card, "agent_card") else agent_card.name
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
                persona_name = agent_card.agent_card.name if hasattr(agent_card, "agent_card") else agent_card.name
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
                    base_card = agent_card.agent_card if hasattr(agent_card, "agent_card") else agent_card
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


@agent.command()
@use_global_options(["model", "verbose"])
@click.option("--port", "-p", type=int, default=9001, help="Server port (default: 9001)")
@click.option("--host", "-h", default="localhost", help="Server host (default: localhost)")
@click.option("--registry-url", "-r", default="http://localhost:8080", help="A2A registry URL")
@click.option(
    "--system-prompt-file", type=click.Path(exists=True, path_type=Path), help="Override system prompt from file"
)
@click.option(
    "--agent-card-file", type=click.Path(exists=True, path_type=Path), help="Explicit agent card file (persona JSON)"
)
@click.argument("persona_file", type=click.Path(exists=True, path_type=Path), required=False)
def serve_single(
    persona_file: Optional[Path],
    model: Optional[str],
    verbose: bool,
    port: int,
    host: str,
    registry_url: str,
    system_prompt_file: Optional[Path],
    agent_card_file: Optional[Path],
) -> int:
    """
    Serve a single AgentCard as an A2A agent server.

    Takes an AgentCard JSON file and boots it up as a live A2A agent server that:
    1. Registers with the A2A registry
    2. Handles A2A protocol requests
    3. Provides the agent's capabilities as live services

    Examples:
        mantis agent serve-single agents/cards/steve_jobs.json
        mantis agent serve-single --port 9002 --agent-card-file steve_jobs.json
        mantis agent serve-single persona.json --system-prompt-file custom_prompt.md
    """
    # Handle input precedence: argument > --agent-card-file
    actual_input = persona_file or agent_card_file
    if not actual_input:
        console.print("[red]❌ No AgentCard file specified[/red]")
        console.print("[dim]Use: mantis agent serve-single <file> or --agent-card-file <file>[/dim]")
        return 1

    if verbose:
        console.print(f"[blue]🚀 Starting agent server from: {actual_input}[/blue]")
        console.print(f"[dim]Server will run on {host}:{port}[/dim]")
        console.print(f"[dim]Registry URL: {registry_url}[/dim]")

    try:
        # Load AgentCard data
        with open(actual_input, "r") as f:
            agent_data = json.load(f)

        # Load AgentCard from JSON (handles both formats)
        from ..agent.card import load_agent_card_from_json

        agent_card = load_agent_card_from_json(agent_data)

        if verbose:
            agent_name = agent_card.agent_card.name if hasattr(agent_card, "agent_card") else agent_card.name
            console.print(f"[dim]Loaded agent: {agent_name}[/dim]")

        # Load custom system prompt if provided (not yet implemented for single serve)
        if system_prompt_file and verbose:
            console.print(f"[dim]Custom system prompt file provided: {system_prompt_file}[/dim]")
            console.print("[dim]Note: Custom system prompts not yet implemented for single serve[/dim]")

        # Get agent card reference
        base_card = agent_card.agent_card if hasattr(agent_card, "agent_card") else agent_card

        console.print(f"\n[bold green]🌟 Starting {base_card.name} A2A Agent Server[/bold green]")
        console.print(f"[cyan]💡 Serving {len(base_card.skills)} skills:[/cyan]")
        for skill in base_card.skills:
            console.print(f"  • {skill.name}")

        console.print(f"\n[yellow]🌐 Server starting on http://{host}:{port}[/yellow]")
        console.print(f"[yellow]📋 Will register with A2A registry at: {registry_url}[/yellow]")
        console.print("\n[dim]Press Ctrl+C to stop the server[/dim]")

        # Get model specification
        from ..config import DEFAULT_MODEL

        model_spec = model or DEFAULT_MODEL

        if verbose:
            console.print(f"[dim]Using model: {model_spec}[/dim]")

        # Create single agent server
        from fasta2a import FastA2A, Skill
        from fasta2a.storage import InMemoryStorage
        from fasta2a.broker import InMemoryBroker
        import asyncio
        import aiohttp
        import uvicorn

        # Convert AgentCard skills to FastA2A skills
        fasta2a_skills = []
        for skill in base_card.skills:
            # Create system prompt for this skill
            system_prompt = f"You are {base_card.name}.\n\n{base_card.description}\n\nYou are specifically being asked to help with: {skill.name}\n{skill.description}"

            fasta2a_skill = Skill(
                name=skill.name.lower().replace(" ", "_"),
                description=skill.description,
                system_prompt=system_prompt,
                model=model_spec,
            )
            fasta2a_skills.append(fasta2a_skill)

        # Update agent card URL
        base_card.url = f"http://{host}:{port}"

        app = FastA2A(
            storage=InMemoryStorage(),
            broker=InMemoryBroker(),
            name=base_card.name,
            url=base_card.url,
            version=base_card.version,
            description=base_card.description,
            provider=base_card.provider,
            skills=fasta2a_skills,
            debug=verbose,
        )

        async def register_agent() -> None:
            """Register agent with the A2A registry using JSON-RPC."""
            try:
                # Convert protobuf AgentCard to dict
                from google.protobuf.json_format import MessageToDict

                agent_card_data = MessageToDict(base_card, preserving_proto_field_name=True)

                # JSON-RPC 2.0 call to register agent
                payload = {
                    "jsonrpc": "2.0",
                    "method": "register_agent",
                    "params": {"agent_card": agent_card_data},
                    "id": 1,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{registry_url}/jsonrpc", json=payload, headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if "error" in result:
                                console.print(
                                    f"[red]❌ Registry error for {base_card.name}: {result['error']['message']}[/red]"
                                )
                            elif "result" in result and result["result"].get("success"):
                                console.print(
                                    f"[green]✅ Successfully registered {base_card.name} with registry[/green]"
                                )
                            else:
                                console.print(f"[yellow]⚠️ Unexpected registry response: {result}[/yellow]")
                        else:
                            response_text = await response.text()
                            console.print(
                                f"[yellow]⚠️ Registry registration returned HTTP {response.status} - {response_text[:200]}[/yellow]"
                            )
            except Exception as e:
                console.print(f"[yellow]⚠️ Failed to register with registry: {e}[/yellow]")
                console.print("[dim]Server will start anyway, but may not be discoverable[/dim]")

        if verbose:
            console.print(f"[dim]Registering with A2A registry at {registry_url}[/dim]")

        asyncio.run(register_agent())

        # Run the server (this blocks)
        uvicorn.run(app, host=host, port=port)
        return 0

    except FileNotFoundError:
        console.print(f"[red]❌ File not found: {actual_input}[/red]")
        return 1
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Invalid JSON in {actual_input}: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]❌ Failed to start agent server: {e}[/red]")
        if verbose:
            console.print_exception()
        return 1


@agent.command()
@use_global_options(["model", "verbose"])
@click.option(
    "--agents-dir",
    "-a",
    type=click.Path(exists=True),
    default="agents",
    help="Directory containing agent JSON files (default: agents/)",
)
@click.option("--base-port", "-p", type=int, default=9001, help="Base port for agent servers (default: 9001)")
@click.option("--host", "-h", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
@click.option("--registry-url", "-r", default="http://localhost:8080", help="A2A registry URL")
@click.option("--enable-adk", is_flag=True, help="Enable ADK backend for Chief of Staff agent (experimental)")
def serve_all(
    agents_dir: str, model: Optional[str], verbose: bool, base_port: int, host: str, registry_url: str, enable_adk: bool
) -> int:
    """
    Serve all agents through individual A2A servers.

    This creates individual servers for each agent found in the agents directory,
    assigning each agent a unique port starting from the base port. When --enable-adk
    is specified, the Chief of Staff agent will be automatically enhanced with Google's
    ADK backend for advanced orchestration capabilities.

    Examples:
        mantis agent serve-all
        mantis agent serve-all --enable-adk
        mantis agent serve-all --base-port 9000 --agents-dir ./my-agents
        mantis agent serve-all --registry-url http://registry:8080 --enable-adk
    """
    try:
        import os
        import asyncio
        import aiohttp
        import uvicorn

        agents_path = Path(agents_dir)

        # Find all JSON files recursively in the agents directory
        agent_files = []
        if agents_path.exists():
            for root, dirs, files in os.walk(agents_path):
                for file in files:
                    if file.endswith(".json"):
                        agent_files.append(Path(root) / file)

        if not agent_files:
            console.print(f"[yellow]⚠️  No agent files found in {agents_path}[/yellow]")
            console.print("[dim]Looking for files matching pattern: *.json[/dim]")
            return 0

        console.print("[bold green]🎭 Starting Multi-Agent Server Farm[/bold green]")
        console.print(f"[cyan]Agents directory: {agents_path}[/cyan]")
        console.print(f"[cyan]Registry: {registry_url}[/cyan]")
        if enable_adk:
            console.print("[cyan]ADK Enhancement: [bold green]ENABLED[/bold green] for Chief of Staff (experimental)[/cyan]")
        console.print()

        # Load and validate AgentCard objects
        agent_cards = {}
        port_assignments = {}
        for i, agent_file in enumerate(agent_files):
            try:
                with open(agent_file, "r") as f:
                    agent_data = json.load(f)

                # Load AgentCard from JSON (handles both formats)
                from ..agent.card import load_agent_card_from_json

                agent_card = load_agent_card_from_json(agent_data)

                # Get base card reference
                base_card = agent_card.agent_card if hasattr(agent_card, "agent_card") else agent_card

                agent_key = base_card.name.lower().replace(" ", "-")
                assigned_port = base_port + i

                # Update agent URL
                base_card.url = f"http://{host}:{assigned_port}"

                agent_cards[agent_key] = agent_card
                port_assignments[agent_key] = assigned_port

                # Check if this will be ADK-enhanced
                is_chief_of_staff = "chief of staff" in base_card.name.lower()
                if is_chief_of_staff and enable_adk:
                    console.print(f"  ✓ [cyan]{base_card.name}[/cyan] ({len(base_card.skills)} skills) [magenta]→ ADK-Enhanced[/magenta]")
                else:
                    console.print(f"  ✓ [cyan]{base_card.name}[/cyan] ({len(base_card.skills)} skills)")
                
                if verbose:
                    console.print(f"    [dim]File: {agent_file}[/dim]")
                    console.print(f"    [dim]URL: {base_card.url}[/dim]")
                    if is_chief_of_staff and enable_adk:
                        console.print(f"    [dim]Backend: Will use ADK (Google Agent Development Kit)[/dim]")
            except Exception as e:
                console.print(f"[red]❌ Failed to load {agent_file.name}: {e}[/red]")
                continue

        if not agent_cards:
            console.print("[red]❌ No valid agent cards found[/red]")
            return 1

        console.print(
            f"\n[bold yellow]🚀 Starting {len(agent_cards)} agent servers on ports {base_port}-{base_port + len(agent_cards) - 1}...[/bold yellow]"
        )
        console.print(f"[yellow]📋 Will register each agent with A2A registry at: {registry_url}[/yellow]")
        console.print("\n[dim]Press Ctrl+C to stop all servers[/dim]")

        # Get model specification
        from ..config import DEFAULT_MODEL

        model_spec = model or DEFAULT_MODEL

        # Create server tasks
        from fasta2a import FastA2A, Skill
        from fasta2a.storage import InMemoryStorage
        from fasta2a.broker import InMemoryBroker

        async def register_agent_with_registry(agent_card: Any, registry_url: str) -> bool:
            """Register an agent card with the A2A registry using JSON-RPC."""
            try:
                # Get base card reference
                base_card = agent_card.agent_card if hasattr(agent_card, "agent_card") else agent_card

                # Convert protobuf AgentCard to dict with proper field naming
                from google.protobuf.json_format import MessageToDict

                agent_card_data = MessageToDict(base_card, preserving_proto_field_name=True)

                # JSON-RPC 2.0 call to register agent
                payload = {
                    "jsonrpc": "2.0",
                    "method": "register_agent",
                    "params": {"agent_card": agent_card_data},
                    "id": 1,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{registry_url}/jsonrpc", json=payload, headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if "error" in result:
                                console.print(
                                    f"[red]❌ Registry error for {base_card.name}: {result['error']['message']}[/red]"
                                )
                                return False
                            elif "result" in result and result["result"].get("success"):
                                if verbose:
                                    console.print(
                                        f"[green]✅ Successfully registered {base_card.name} with registry[/green]"
                                    )
                                return True
                            else:
                                console.print(f"[yellow]⚠️ Unexpected response for {base_card.name}: {result}[/yellow]")
                                return False
                        else:
                            response_text = await response.text()
                            console.print(
                                f"[yellow]⚠️ Failed to register {base_card.name}: HTTP {response.status} - {response_text[:200]}[/yellow]"
                            )
                            return False
            except Exception as e:
                console.print(f"[yellow]⚠️ Error registering {base_card.name} with registry: {e}[/yellow]")
                return False

        async def run_server(app: Any, port: int, name: str) -> None:
            """Run a single FastA2A server"""
            try:
                config = uvicorn.Config(app, host=host, port=port, log_level="info" if verbose else "warning")
                server = uvicorn.Server(config)
                if verbose:
                    console.print(f"[dim]Starting {name} server on http://{host}:{port}[/dim]")
                await server.serve()
            except Exception as e:
                console.print(f"[red]❌ ERROR starting server for {name} on port {port}: {e}[/red]")
                raise

        async def run_all_servers() -> None:
            # Create FastA2A apps for each agent
            servers = []
            registration_tasks = []

            for agent_key, agent_card in agent_cards.items():
                port = port_assignments[agent_key]

                # Get base card reference
                base_card = agent_card.agent_card if hasattr(agent_card, "agent_card") else agent_card

                if verbose:
                    console.print(f"[dim]Creating server for {base_card.name} on port {port}[/dim]")

                # Convert AgentCard skills to FastA2A skills
                fasta2a_skills = []
                for skill in base_card.skills:
                    system_prompt = f"You are {base_card.name}.\n\n{base_card.description}\n\nYou are specifically being asked to help with: {skill.name}\n{skill.description}"

                    fasta2a_skill = Skill(
                        name=skill.name.lower().replace(" ", "_"),
                        description=skill.description,
                        system_prompt=system_prompt,
                        model=model_spec,
                    )
                    fasta2a_skills.append(fasta2a_skill)

                # Create FastA2A app
                app = FastA2A(
                    storage=InMemoryStorage(),
                    broker=InMemoryBroker(),
                    name=base_card.name,
                    url=base_card.url,
                    version=base_card.version,
                    description=base_card.description,
                    provider=base_card.provider,
                    skills=fasta2a_skills,
                    debug=verbose,
                )

                # Check if this is Chief of Staff and ADK is enabled
                is_chief_of_staff = "chief of staff" in base_card.name.lower()
                if is_chief_of_staff and enable_adk:
                    try:
                        # Create ADK-enhanced server for Chief of Staff
                        from ..adk.router import ChiefOfStaffRouter
                        from ..adk.server import create_adk_router_app
                        
                        adk_router = ChiefOfStaffRouter()
                        adk_app = create_adk_router_app(adk_router, f"ADK {base_card.name}")
                        
                        servers.append((adk_app, port, f"{base_card.name} (ADK-Enhanced)"))
                        console.print(f"  ✓ [magenta]{base_card.name}[/magenta] (ADK-Enhanced with Gemini 2.0)")
                        if verbose:
                            console.print(f"    [dim]URL: {base_card.url}[/dim]")
                            console.print(f"    [dim]Backend: ADK with Google's Agent Development Kit[/dim]")
                    except Exception as e:
                        console.print(f"[yellow]⚠️ ADK enhancement failed for {base_card.name}: {e}[/yellow]")
                        console.print("[dim]Falling back to FastA2A backend[/dim]")
                        # Fall back to regular FastA2A server
                        servers.append((app, port, base_card.name))
                else:
                    # Regular FastA2A server
                    servers.append((app, port, base_card.name))

                registration_tasks.append(register_agent_with_registry(agent_card, registry_url))

            # Register agents in batches to avoid thundering herd
            if verbose:
                console.print(f"[dim]Registering {len(registration_tasks)} agents with registry in batches[/dim]")

            batch_size = 10  # Register 10 agents at a time
            batch_delay = 2.0  # Wait 2 seconds between batches
            successful_registrations = 0

            for i in range(0, len(registration_tasks), batch_size):
                batch = registration_tasks[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(registration_tasks) + batch_size - 1) // batch_size

                if verbose:
                    console.print(f"[dim]Registering batch {batch_num}/{total_batches} ({len(batch)} agents)[/dim]")

                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                batch_success = sum(1 for result in batch_results if result is True)
                successful_registrations += batch_success

                if verbose:
                    console.print(f"[dim]Batch {batch_num} complete: {batch_success}/{len(batch)} successful[/dim]")

                # Wait before next batch (except for the last batch)
                if i + batch_size < len(registration_tasks):
                    if verbose:
                        console.print(f"[dim]Waiting {batch_delay}s before next batch...[/dim]")
                    await asyncio.sleep(batch_delay)

            console.print(
                f"[green]✅ Successfully registered {successful_registrations}/{len(agent_cards)} agents[/green]"
            )

            # Start all servers
            console.print(f"[dim]Starting {len(servers)} servers...[/dim]")
            server_tasks = []
            for app, port, name in servers:
                task = asyncio.create_task(run_server(app, port, name))
                server_tasks.append(task)

            # Wait for all servers
            await asyncio.gather(*server_tasks)

        # Run all servers
        asyncio.run(run_all_servers())
        return 0

    except FileNotFoundError:
        console.print(f"[red]❌ Agents directory not found: {agents_dir}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]❌ Failed to start multi-agent server: {e}[/red]")
        if verbose:
            console.print_exception()
        return 1
