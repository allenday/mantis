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
def agent(verbose: bool):
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
