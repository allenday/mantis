"""
Simulation command for running multi-agent scenarios.
"""

from typing import Optional

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .core import cli, use_global_options, error_handler
from ..core import UserRequestBuilder, SimulationOrchestrator
from ..proto.mantis.v1 import mantis_core_pb2

console = Console()


@cli.command()
@click.argument("query", required=True)
@click.option("--context", "-c", help="Additional context for the simulation")
@click.option("--structured-data", "--data", help="Structured data as JSON string")
@click.option("--agents", "-a", help="Comma-separated agent specifications (e.g., 'leader:1:may,follower:2:must_not')")
@click.option("--max-depth", "-d", type=int, help="Maximum recursion depth (1-3, default: 3)")
@click.option("--strategy", type=click.Choice(["direct", "a2a"]), default="a2a", help="Execution strategy")
@click.option("--temperature", "-t", type=float, help="Model temperature (0.0-2.0)")
@click.option("--dry-run", is_flag=True, help="Show the UserRequest without executing")
@use_global_options(["model", "verbose"])
@error_handler
def simulate(
    query: str,
    context: Optional[str] = None,
    structured_data: Optional[str] = None,
    agents: Optional[str] = None,
    max_depth: Optional[int] = None,
    strategy: str = "a2a",
    temperature: Optional[float] = None,
    dry_run: bool = False,
    model: Optional[str] = None,
    verbose: bool = False,
):
    """
    Run a multi-agent simulation with the specified query.

    The simulation system orchestrates multiple AI agents to collaboratively
    solve complex problems through strategic interaction and recursive delegation.

    Examples:

      # Simple simulation with default agents
      mantis simulate "What is the best strategy for market expansion?"

      # Specify agent roles and policies
      mantis simulate "Design a product roadmap" --agents "strategist:1:may,analyst:2:must_not"

      # Add context and structured data
      mantis simulate "Analyze this data" --context "Q3 financial review" --data '{"revenue": 1000000}'

      # Control recursion and model parameters
      mantis simulate "Complex problem" --max-depth 3 --model claude-3-5-sonnet --temperature 0.8
    """
    if verbose:
        console.print(f"[dim]Building UserRequest for query: {query[:50]}{'...' if len(query) > 50 else ''}[/dim]")

    try:
        # Build UserRequest from CLI arguments
        user_request = UserRequestBuilder.from_cli_args(
            query=query,
            context=context,
            structured_data=structured_data,
            model=model,
            temperature=temperature,
            max_depth=max_depth,
            agents=agents,
        )

        if verbose:
            console.print("[green]✅ UserRequest built successfully[/green]")
            console.print(
                f"[dim]Agents: {len(user_request.agents)}, Max depth: {user_request.max_depth or 'default'}[/dim]"
            )

        if dry_run:
            _display_user_request(user_request, verbose)
            return

        # Execute the simulation using the orchestrator
        console.print("[blue]ℹ️  Starting simulation...[/blue]")

        orchestrator = SimulationOrchestrator()

        # Run the simulation (handle async)
        import asyncio

        try:
            simulation_output = asyncio.run(orchestrator.execute_simulation(user_request))

            # Display results
            _display_simulation_output(simulation_output, verbose)

            # Check for errors
            if simulation_output.execution_result.status == mantis_core_pb2.EXECUTION_STATUS_FAILED:
                console.print("[red]❌ Simulation completed with errors[/red]")
                return 1
            else:
                console.print("[green]✅ Simulation completed successfully[/green]")

        except Exception as e:
            console.print(f"[red]❌ Simulation execution failed: {e}[/red]")
            if verbose:
                console.print_exception()
            return 1

    except ValueError as e:
        console.print(f"[red]❌ Validation Error: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if verbose:
            console.print_exception()
        return 1


def _display_simulation_output(simulation_output: mantis_core_pb2.SimulationOutput, verbose: bool = False):
    """Display SimulationOutput in a formatted way."""
    # Display main response
    console.print(
        Panel(
            simulation_output.response.text_response,
            title="Simulation Result",
            border_style=(
                "green"
                if simulation_output.execution_result.status == mantis_core_pb2.EXECUTION_STATUS_SUCCESS
                else "red"
            ),
        )
    )

    # Display metadata
    status_name = mantis_core_pb2.ExecutionStatus.Name(simulation_output.execution_result.status)
    console.print("\n[bold]Execution Summary:[/bold]")
    console.print(f"  Status: {status_name.replace('EXECUTION_STATUS_', '')}")
    console.print(f"  Duration: {simulation_output.total_time:.2f}s")
    console.print(f"  Team Size: {simulation_output.team_size}")
    console.print(f"  Recursion Depth: {simulation_output.recursion_depth}")

    if simulation_output.execution_strategies:
        strategy_names = [
            mantis_core_pb2.ExecutionStrategy.Name(s).replace("EXECUTION_STRATEGY_", "")
            for s in simulation_output.execution_strategies
        ]
        console.print(f"  Strategies: {', '.join(strategy_names)}")

    # Display error info if present
    if simulation_output.execution_result.HasField("error_info"):
        error_info = simulation_output.execution_result.error_info
        error_type = mantis_core_pb2.ErrorType.Name(error_info.error_type).replace("ERROR_TYPE_", "")
        console.print("\n[red]Error Details:[/red]")
        console.print(f"  Type: {error_type}")
        console.print(f"  Message: {error_info.error_message}")

    if verbose and simulation_output.response.output_modes:
        console.print(f"\n[dim]Output Modes: {', '.join(simulation_output.response.output_modes)}[/dim]")


def _display_user_request(user_request: mantis_core_pb2.UserRequest, verbose: bool = False):
    """Display UserRequest in a formatted way."""
    console.print(
        Panel(
            f"[bold]Query:[/bold] {user_request.query}\n"
            + (f"[bold]Context:[/bold] {user_request.context}\n" if user_request.HasField("context") else "")
            + (
                f"[bold]Structured Data:[/bold] {user_request.structured_data}\n"
                if user_request.HasField("structured_data")
                else ""
            )
            + (
                f"[bold]Model:[/bold] {user_request.model_spec.model or 'default'}\n"
                if user_request.HasField("model_spec")
                else ""
            )
            + (
                f"[bold]Temperature:[/bold] {user_request.model_spec.temperature}\n"
                if user_request.HasField("model_spec") and user_request.model_spec.HasField("temperature")
                else ""
            )
            + (f"[bold]Max Depth:[/bold] {user_request.max_depth}\n" if user_request.HasField("max_depth") else "")
            + f"[bold]Agents:[/bold] {len(user_request.agents)}",
            title="UserRequest Summary",
            border_style="blue",
        )
    )

    if verbose and user_request.agents:
        console.print("\n[bold]Agent Specifications:[/bold]")
        for i, agent in enumerate(user_request.agents):
            policy_name = (
                mantis_core_pb2.RecursionPolicy.Name(agent.recursion_policy)
                if agent.HasField("recursion_policy")
                else "default"
            )
            console.print(
                f"  Agent {i + 1}: count={agent.count or 1}, policy={policy_name.replace('RECURSION_POLICY_', '').lower()}"
            )

    if verbose:
        # Show the full protobuf as JSON for debugging
        try:
            from google.protobuf.json_format import MessageToJson

            json_str = MessageToJson(user_request, indent=2)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            console.print(Panel(syntax, title="Full UserRequest (JSON)", border_style="dim"))
        except Exception as e:
            console.print(f"[dim]Could not display JSON format: {e}[/dim]")
