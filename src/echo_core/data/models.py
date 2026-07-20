"""
Data models — typed records for the data layer.

These are lightweight dataclass-like dicts, not ORM models.
Backends map to/from these shapes before handing up to the application layer.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class SystemState:
    twin_id: str = "echo-twin-v1"
    twin_name: str = "Project Echo Twin"
    status: str = "active"                # active | paused | revoked | corrupted
    current_cycle: int = 0
    last_wake: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    last_report_sent: Optional[str] = None
    active_domains: list[str] = field(default_factory=list)
    agent_count: int = 0
    pending_escalations: list[dict] = field(default_factory=list)
    consent_contract_hash: Optional[str] = None
    last_updated: Optional[str] = None
    monetization_phase: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SystemState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class LogEntry:
    timestamp: str = ""
    agent: str = ""
    action: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        base = {"timestamp": self.timestamp, "agent": self.agent, "action": self.action}
        base.update(self.details)
        return base

    @classmethod
    def from_dict(cls, d: dict) -> "LogEntry":
        return cls(
            timestamp=d.get("timestamp", ""),
            agent=d.get("agent", ""),
            action=d.get("action", ""),
            details={k: v for k, v in d.items() if k not in ("timestamp", "agent", "action")},
        )


@dataclass
class RoutingEntry:
    timestamp: str = ""
    task_id: str = ""
    task_description: str = ""
    tier: str = ""
    model: str = ""
    provider: str = ""
    complexity: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RoutingEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ConsentContract:
    twin_id: str = ""
    subject: str = ""
    status: str = "active"
    created: str = ""
    expiry_duration_days: Optional[int] = None
    enabled_domains: dict = field(default_factory=dict)
    global_restrictions: list[str] = field(default_factory=list)
    write_whitelist: list[str] = field(default_factory=list)


@dataclass
class FinancialTransaction:
    timestamp: str = ""
    tx_type: str = ""        # "expense" | "revenue"
    amount: float = 0.0
    category: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FinancialTransaction":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GraphEdge:
    subject: str = ""
    predicate: str = ""
    obj: str = ""
    weight: float = 1.0
    evidence: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GraphEdge":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})