"""Agent log — delegates to the data layer backend.

Keeps the existing functional API for backward compatibility.
"""

import logging
from pathlib import Path

from echo_core.data.backends import FileLogRepository

_repo = FileLogRepository(Path("~/.echo-core/logs/agent-log.jsonl").expanduser())
logger = logging.getLogger("echo_core")


def set_agent_log_path(path: str):
    global _repo
    _repo = FileLogRepository(Path(path).expanduser().resolve())


def log_agent(agent_name: str, action: str, details: dict = None,
              path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileLogRepository(Path(path).expanduser().resolve())
    entry = {"agent": agent_name, "action": action, **(details or {})}
    return repo.append(entry)


def log_entry(entry: dict, path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileLogRepository(Path(path).expanduser().resolve())
    return repo.append(entry)


def get_latest_logs(n: int = 10, path: str = None) -> list[dict]:
    repo = _repo
    if path:
        repo = FileLogRepository(Path(path).expanduser().resolve())
    return repo.get_latest(n)


def count_cycles(agent: str = "orchestrator", path: str = None) -> int:
    repo = _repo
    if path:
        repo = FileLogRepository(Path(path).expanduser().resolve())
    return repo.count_cycles(agent)


def get_logger(name: str = None) -> logging.Logger:
    log = logging.getLogger(f"echo_core.{name}" if name else "echo_core")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log