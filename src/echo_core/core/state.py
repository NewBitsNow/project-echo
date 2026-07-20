"""
System state — delegates to the data layer.

Keeps the existing functional API for backward compatibility.
"""

from pathlib import Path

from echo_core.data.backends import FileStateRepository

_repo = FileStateRepository(Path("~/.echo-core/state/system-state.json").expanduser())


def set_state_path(path: str):
    global _repo
    _repo = FileStateRepository(Path(path).expanduser().resolve())


def read_state(path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileStateRepository(Path(path).expanduser().resolve(), direct=True)
    return repo.read()


def update_state(updates: dict, path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileStateRepository(Path(path).expanduser().resolve(), direct=True)
    return repo.update(updates)


def increment_cycle(path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileStateRepository(Path(path).expanduser().resolve(), direct=True)
    return repo.increment_cycle()


def system_status(path: str = None) -> str:
    return read_state(path).get("status", "unknown")


def init_state(twin_id: str = "echo-twin-v1",
               twin_name: str = "Project Echo Twin",
               path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileStateRepository(Path(path).expanduser().resolve(), direct=True)
    return repo.init(twin_id=twin_id, twin_name=twin_name)