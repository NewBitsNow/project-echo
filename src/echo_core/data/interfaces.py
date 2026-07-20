"""
Data layer interfaces — abstract base classes defining the repository contract.

Every storage backend must implement these interfaces. The application layer
never imports backends directly — only these interfaces.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional


class StateRepository(ABC):
    """System state — singleton document tracking cycle, status, and flags."""

    @abstractmethod
    def read(self) -> dict[str, Any]:
        """Return the current system state dict."""

    @abstractmethod
    def update(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Apply partial updates to the state and persist."""

    @abstractmethod
    def increment_cycle(self) -> dict[str, Any]:
        """Advance the cycle counter and record wake time."""

    @abstractmethod
    def init(self, twin_id: str = "echo-twin-v1",
             twin_name: str = "Project Echo Twin") -> dict[str, Any]:
        """Create a fresh state document."""


class LogRepository(ABC):
    """Append-only agent action log with query support."""

    @abstractmethod
    def append(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Write one log entry. Returns the entry with auto-added timestamp."""

    @abstractmethod
    def get_latest(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the N most recent entries, newest first."""

    @abstractmethod
    def count_cycles(self, agent: str = "orchestrator") -> int:
        """Count cycle_complete actions for a given agent."""

    @abstractmethod
    def query(
        self,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Filtered log query. All filters are optional."""


class ConsentRepository(ABC):
    """Consent contract — policy document read with validation."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Parse and return the full consent contract."""

    @abstractmethod
    def check(self, domain: str) -> dict[str, Any]:
        """Check if a domain agent is enabled. Returns {enabled, tools, ...}."""

    @abstractmethod
    def status(self) -> str:
        """One-line status: 'active', 'expired', 'not_found', 'invalid'."""


class RoutingRepository(ABC):
    """Model routing decisions — append-only log with aggregation."""

    @abstractmethod
    def log(self, task_id: str, task_description: str, tier: str,
            model: str, provider: str, complexity: float) -> dict[str, Any]:
        """Record one routing decision."""

    @abstractmethod
    def summarize(self, days: int = 7) -> dict[str, Any]:
        """Return aggregated stats: tasks per tier, model, free vs paid."""


class FinancialRepository(ABC):
    """Financial tracking — expenses and revenue records."""

    @abstractmethod
    def record_transaction(
        self,
        tx_type: str,       # "expense" | "revenue"
        amount: float,
        category: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Record a financial transaction."""

    @abstractmethod
    def get_balance(self) -> dict[str, float]:
        """Return {total_revenue, total_expenses, net}."""

    @abstractmethod
    def get_transactions(
        self,
        tx_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query transactions with optional filters."""


class KnowledgeGraphRepository(ABC):
    """Knowledge graph — directed edges between entities with evidential weight."""

    @abstractmethod
    def add_edge(self, subject: str, predicate: str, obj: str,
                 weight: float = 1.0, evidence: str = "") -> dict[str, Any]:
        """Record a directed edge: subject --predicate--> object."""

    @abstractmethod
    def query_edges(self, subject: Optional[str] = None,
                    predicate: Optional[str] = None,
                    obj: Optional[str] = None,
                    min_weight: float = 0.0) -> list[dict[str, Any]]:
        """Query edges by any combination of subject/predicate/object."""

    @abstractmethod
    def get_trust_score(self, entity: str) -> float:
        """Aggregate trust score for an entity based on evidence edges."""


class Repository:
    """Facade over all data stores. Provides a single entry point.

    Usage:
        repo = Repository(state=..., log=..., consent=..., ...)
        repo.state.read()
        repo.log.append(entry)
    """

    def __init__(
        self,
        state: StateRepository,
        log: LogRepository,
        consent: ConsentRepository,
        routing: RoutingRepository,
        financial: FinancialRepository,
        graph: KnowledgeGraphRepository,
    ):
        self.state = state
        self.log = log
        self.consent = consent
        self.routing = routing
        self.financial = financial
        self.graph = graph