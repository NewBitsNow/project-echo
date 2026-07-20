"""Routing logger — delegates to the data layer backend.

Keeps the existing functional API for backward compatibility.
"""

from pathlib import Path

from echo_core.data.backends import FileRoutingRepository

_repo = FileRoutingRepository(
    Path("~/.echo-core/logs/routing-log.jsonl").expanduser()
)


def set_log_path(path: str):
    global _repo
    _repo = FileRoutingRepository(Path(path).expanduser().resolve())


def log_routing(task_id: str, task_description: str, tier: str,
                model: str, provider: str, complexity: float) -> dict:
    return _repo.log(task_id, task_description, tier, model, provider, complexity)


def summarize_routing(days: int = 7, json_output: bool = False) -> dict | str:
    summary = _repo.summarize(days)
    if json_output:
        return summary

    print(f"=== Routing Summary (last {days}d) ===")
    print(f"Total tasks: {summary['total_tasks']}")
    print()
    if summary["total_tasks"] == 0:
        print("No routing events in this period.")
        return

    for tier, count in summary["tier_breakdown"].items():
        pct = count / summary["total_tasks"] * 100
        print(f"  {tier}: {count} ({pct:.0f}%)")
    print()
    print(f"  Free tier usage:  {summary['free_tier_count']} tasks ($0.0000)")
    print(f"  Paid tier usage:  {summary['paid_tier_count']} tasks")
    print(f"  Escalations:      {summary['escalation_count']} tasks")
    if summary["total_tasks"] > 0:
        print(f"  Offload rate:     {summary['free_tier_count'] / summary['total_tasks'] * 100:.0f}%")