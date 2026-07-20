"""echo_core CLI entry point."""

import sys


def main():
    """Print help and exit."""
    print("echo_core v1.0.0 — Project Echo Core Infrastructure")
    print()
    print("Usage:")
    print("  python -m echo_core              Show this help")
    print("  python -m echo_core.wizard        Launch setup wizard")
    print()
    print("Core API:")
    print("  from echo_core import classify_task")
    print("  from echo_core import build_packet")
    print("  from echo_core import read_consent")
    print("  from echo_core import read_state, increment_cycle")
    print("  from echo_core import log_agent")
    print("  from echo_core import discover_modules")
    print()
    print("Documentation: docs/project-echo-user-guide.md")
    print("Repository: echo-core/")


if __name__ == "__main__":
    main()