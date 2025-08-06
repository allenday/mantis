#!/usr/bin/env python3
"""
Core CLI framework with global options and smart masking.

This module provides the foundation for the modern Mantis CLI including:
- Global options that can be selectively applied to commands
- Smart masking to hide irrelevant options per command
- Rich formatting and consistent UX patterns
"""

import functools
from typing import List, Optional, Callable, Any
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel

# Configure rich-click for better UX
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the command with the '--help' flag for more information."

console = Console()

# Global options registry - maps option names to click decorators
GLOBAL_OPTIONS = {
    "input": click.option(
        "--input", "-i", type=click.Path(exists=True, path_type=Path), help="Input file or directory"
    ),
    "output": click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file or directory"),
    "model": click.option(
        "--model", "-m", help="Explicit pydantic-ai model string (use 'mantis models' to see available models)"
    ),
    "recursive": click.option("--recursive", "-r", is_flag=True, help="Process recursively"),
    "verbose": click.option("--verbose", "-v", is_flag=True, help="Verbose output"),
    "dry_run": click.option("--dry-run", is_flag=True, help="Show what would happen without executing"),
}


def use_global_options(option_names: List[str]) -> Callable:
    """
    Decorator to apply selected global options to a command.

    Args:
        option_names: List of global option names to apply

    Returns:
        Decorator function that applies the selected options

    Example:
        @use_global_options(['model', 'output', 'verbose'])
        def simulate():
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Apply options in reverse order so they appear in correct order in help
        for option_name in reversed(option_names):
            if option_name in GLOBAL_OPTIONS:
                func = GLOBAL_OPTIONS[option_name](func)
            else:
                console.print(f"[red]Warning: Unknown global option '{option_name}'[/red]")
        return func

    return decorator


def validate_model_string(ctx: click.Context, param: click.Parameter, value: Optional[str]) -> Optional[str]:
    """
    Validate model string against available models from ModelManager.

    This provides early validation and helpful error messages when invalid
    models are specified.
    """
    if value is None:
        return value

    try:
        from ..models import get_model_manager

        manager = get_model_manager()
        model = manager.find_model(value)

        if model is None:
            # Get available models for suggestion
            available_models = manager.get_all_models()
            model_names = [m.full_name for m in available_models]

            console.print(f"[red]Error: Model '{value}' not found[/red]")
            console.print("\n[yellow]Available models:[/yellow]")
            for name in model_names[:10]:  # Show first 10
                console.print(f"  • {name}")
            if len(model_names) > 10:
                console.print(f"  ... and {len(model_names) - 10} more")
            console.print("\n[dim]Use 'mantis models --list-models' to see all available models[/dim]")

            raise click.BadParameter(f"Model '{value}' not found. Use 'mantis models' to see available models.")

        return value

    except ImportError:
        # ModelManager not available, skip validation
        return value
    except Exception as e:
        console.print(f"[yellow]Warning: Could not validate model '{value}': {e}[/yellow]")
        return value


class ModelParameter(click.ParamType):
    """Custom click parameter type for model validation."""

    name = "model"

    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Any:
        if value is None:
            return value
        if ctx is None or param is None:
            return str(value)  # Skip validation if context is missing
        return validate_model_string(ctx, param, str(value))


# Enhanced global options with validation
GLOBAL_OPTIONS["model"] = click.option(
    "--model",
    "-m",
    type=ModelParameter(),
    help="Explicit pydantic-ai model string (use 'mantis models' to see available models)",
)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version information")
@click.pass_context
def cli(ctx: click.Context, version: bool):
    """
    Mantis - Multi-agent AI framework for strategic divination

    A sophisticated CLI for multi-agent AI simulation and strategic analysis.
    """
    if ctx.invoked_subcommand is None:
        if version:
            from .. import __version__

            console.print(f"[bold green]Mantis[/bold green] version [green]{__version__}[/green]")
            console.print("Multi-agent AI framework for strategic divination")
        else:
            console.print(
                Panel.fit(
                    "[bold green]Mantis CLI[/bold green]\n\n"
                    "Available commands:\n"
                    "• [cyan]agent[/cyan]     - Generate, inspect, and serve agents\n"
                    "• [cyan]registry[/cyan]  - Inspect and search agent registry\n"
                    "• [cyan]models[/cyan]    - List and inspect available AI models\n"
                    "• [cyan]simulate[/cyan]  - Run A2A agent simulation or tournament\n\n"
                    "[dim]Use 'mantis <command> --help' for detailed help on any command[/dim]",
                    title="Welcome to Mantis",
                    border_style="green",
                )
            )


def error_handler(func: Callable) -> Callable:
    """Decorator to provide consistent error handling across commands."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            return 1
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if kwargs.get("verbose"):
                console.print_exception()
            return 1

    return wrapper


def success_message(message: str) -> None:
    """Display a success message with consistent formatting."""
    console.print(f"[green]✅ {message}[/green]")


def warning_message(message: str) -> None:
    """Display a warning message with consistent formatting."""
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def info_message(message: str) -> None:
    """Display an info message with consistent formatting."""
    console.print(f"[blue]ℹ️  {message}[/blue]")


def error_message(message: str) -> None:
    """Display an error message with consistent formatting."""
    console.print(f"[red]❌ {message}[/red]")
