"""Content Creation Factory CLI package entry point.

Modular Typer subcommands for topics, pipeline generation, planning, and observability.
"""

import logging
import sys
from typing import Optional, Sequence

import typer
from dotenv import load_dotenv

from content_creation import __version__
from content_creation.cli.observability import register_observability_commands
from content_creation.cli.pipeline import register_pipeline_commands
from content_creation.cli.planning import register_planning_commands
from content_creation.cli.topics import register_topics_commands
from content_creation.storage.local import LocalStorage
from content_creation.utils.logging import setup_logging

load_dotenv()

app = typer.Typer(
    name="content-creation",
    help="Content Creation Factory CLI - A source-grounded content pipeline for ML/AI students.",
    no_args_is_help=True,
    add_completion=False,
)

# Register all domain commands
register_topics_commands(app)
register_pipeline_commands(app)
register_planning_commands(app)
register_observability_commands(app)

__all__ = [
    "app",
    "main",
    "LocalStorage",
    "setup_logging",
    "__version__",
]


def _print_help() -> None:
    """Print top-level command help."""
    click_cmd = typer.main.get_command(app)
    ctx = click_cmd.make_context("content-creation", [], resilient_parsing=True)
    print(click_cmd.get_help(ctx))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point wrapping Typer execution.

    Args:
        argv: Optional command-line argument sequence (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    if argv is None:
        raw_args = list(sys.argv[1:])
    else:
        raw_args = list(argv)

    # 1. Handle --version flag directly for parity
    if "--version" in raw_args:
        print(f"content-creation {__version__}")
        raise SystemExit(0)

    # 2. Handle root help directly when requested
    if "--help" in raw_args or "-h" in raw_args:
        if len(raw_args) == 1:
            _print_help()
            raise SystemExit(0)

    # 3. Handle verbose flag extraction
    verbose = False
    args: list[str] = []
    for arg in raw_args:
        if arg in ("-v", "--verbose"):
            verbose = True
        else:
            args.append(arg)

    # 4. Handle no arguments passed
    if not args:
        _print_help()
        return 0

    # 5. Initialize logging
    log_level = logging.DEBUG if verbose else logging.INFO
    try:
        setup_logging(level=log_level)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1

    # 6. Execute Typer application with standalone_mode=False
    try:
        result = app(args=args, standalone_mode=False)
        return int(result) if isinstance(result, int) else 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 0
    except Exception as e:
        # Check if Click exception with exit_code
        exit_code = getattr(e, "exit_code", None)
        if exit_code is not None and isinstance(exit_code, int):
            show = getattr(e, "show", None)
            if callable(show):
                show()
            else:
                print(f"Error: {e}", file=sys.stderr)
            return exit_code

        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
