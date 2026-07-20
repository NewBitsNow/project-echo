"""
echo_core.data — Project Echo Data Layer.

Architecturally distinct from the application layer. Provides a clean
repository interface backed by swappable storage engines:

    from echo_core.data import DataLayer, Repository

    dl = DataLayer(backend="file", base_path="~/.echo-core")
    state = dl.state.read()
    dl.log.append(entry)
    consent = dl.consent.check("code")

Backends:
    "file"     — JSON/YAML/JSONL on filesystem (default, zero deps)
    "sqlite"   — SQLite via sqlite3 stdlib (better queries, transactions)
    "postgres" — PostgreSQL via asyncpg (multi-machine, analytics)

The application layer (echo_core.core.*) should never import backends
directly. Always go through the Repository interface.
"""

from echo_core.data.interfaces import (
    StateRepository,
    LogRepository,
    ConsentRepository,
    RoutingRepository,
    FinancialRepository,
    KnowledgeGraphRepository,
    Repository,
)
from echo_core.data.models import (
    SystemState,
    LogEntry,
    RoutingEntry,
    ConsentContract,
    FinancialTransaction,
    GraphEdge,
)
from echo_core.data.repository import DataLayer, open_repository

__all__ = [
    "DataLayer",
    "open_repository",
    "Repository",
    "StateRepository",
    "LogRepository",
    "ConsentRepository",
    "RoutingRepository",
    "FinancialRepository",
    "KnowledgeGraphRepository",
    "SystemState",
    "LogEntry",
    "RoutingEntry",
    "ConsentContract",
    "FinancialTransaction",
    "GraphEdge",
]