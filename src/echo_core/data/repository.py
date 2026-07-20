"""
DataLayer — the single entry point for all data operations.

Usage:
    dl = DataLayer(backend="file", base_path="~/.echo-core")
    dl.state.read()
    dl.log.append({"agent": "orchestrator", "action": "cycle_start"})
    dl.consent.check("code")

Backend selection:
    "file"     — JSON/YAML/JSONL on local filesystem (default)
    "sqlite"   — SQLite via stdlib sqlite3
    "postgres" — PostgreSQL via asyncpg
"""

from pathlib import Path
from typing import Optional

from echo_core.data.interfaces import Repository
from echo_core.data.backends import (
    FileStateRepository,
    FileLogRepository,
    FileConsentRepository,
    FileRoutingRepository,
    FileFinancialRepository,
    FileKnowledgeGraphRepository,
)


class DataLayer:
    """Facade over all data repositories. Provides a single entry point.

    Args:
        backend: Storage backend — "file" (default), "sqlite", or "postgres".
        base_path: Root directory for file-based storage (default: ~/.echo-core).
        connection_string: Database connection string for sqlite/postgres.
    """

    def __init__(
        self,
        backend: str = "file",
        base_path: Optional[str] = None,
        connection_string: Optional[str] = None,
    ):
        self._backend = backend
        self._base_path = Path(base_path or "~/.echo-core").expanduser()
        self._conn_str = connection_string

        if backend == "file":
            self._init_file()
        elif backend == "sqlite":
            raise NotImplementedError("SQLite backend coming in Phase 2")
        elif backend == "postgres":
            raise NotImplementedError("PostgreSQL backend coming in Phase 3")
        else:
            raise ValueError(f"Unknown backend: {backend}. Use 'file', 'sqlite', or 'postgres'.")

    def _init_file(self):
        bp = self._base_path
        self.state = FileStateRepository(bp / "state" / "system-state.json")
        self.log = FileLogRepository(bp / "logs" / "agent-log.jsonl")
        self.consent = FileConsentRepository(bp / "state" / "consent-contract.yaml")
        self.routing = FileRoutingRepository(bp / "logs" / "routing-log.jsonl")
        self.financial = FileFinancialRepository(bp / "state" / "transactions.csv")
        self.graph = FileKnowledgeGraphRepository(bp / "graphs" / "edges.jsonl")

    @property
    def repo(self) -> Repository:
        """Return a Repository facade for dependency injection."""
        return Repository(
            state=self.state,
            log=self.log,
            consent=self.consent,
            routing=self.routing,
            financial=self.financial,
            graph=self.graph,
        )


def open_repository(
    backend: str = "file",
    base_path: Optional[str] = None,
    connection_string: Optional[str] = None,
) -> Repository:
    """Convenience function — one call to get a fully configured Repository.

    Usage:
        repo = open_repository()
        repo.state.increment_cycle()
        repo.log.append({"agent": "framehead", "action": "generate"})
    """
    dl = DataLayer(backend=backend, base_path=base_path,
                   connection_string=connection_string)
    return dl.repo