"""
File-based data backend — JSON/YAML/JSONL on the local filesystem.

Zero dependencies beyond the Python stdlib. This is the default backend
and the reference implementation for the repository interfaces.
"""

import json
import csv
import io
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from echo_core.data.interfaces import (
    StateRepository,
    LogRepository,
    ConsentRepository,
    RoutingRepository,
    FinancialRepository,
    KnowledgeGraphRepository,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict):
    _ensure_dir(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _append_jsonl(path: Path, entry: dict):
    _ensure_dir(path)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────
# StateRepository — file backend
# ──────────────────────────────────────────────

class FileStateRepository(StateRepository):
    """System state stored as a single JSON file."""

    def __init__(self, path: Path):
        self._path = path

    def read(self) -> dict:
        return _read_json(self._path) or {
            "twin_id": "unknown",
            "status": "uninitialized",
            "current_cycle": 0,
        }

    def update(self, updates: dict) -> dict:
        state = self.read()
        state.update(updates)
        state["last_updated"] = _now_iso()
        _write_json(self._path, state)
        return state

    def increment_cycle(self) -> dict:
        state = self.read()
        return self.update({
            "current_cycle": state.get("current_cycle", 0) + 1,
            "last_wake": _now_iso(),
        })

    def init(self, twin_id: str = "echo-twin-v1",
             twin_name: str = "Project Echo Twin") -> dict:
        state = {
            "twin_id": twin_id,
            "twin_name": twin_name,
            "status": "active",
            "current_cycle": 0,
            "last_wake": None,
            "created_at": _now_iso(),
            "expires_at": None,
            "last_report_sent": None,
            "active_domains": [],
            "agent_count": 0,
            "pending_escalations": [],
            "consent_contract_hash": None,
            "last_updated": _now_iso(),
        }
        _write_json(self._path, state)
        return state


# ──────────────────────────────────────────────
# LogRepository — file backend
# ──────────────────────────────────────────────

class FileLogRepository(LogRepository):
    """Agent log stored as an append-only JSONL file."""

    def __init__(self, path: Path):
        self._path = path

    def append(self, entry: dict) -> dict:
        entry.setdefault("timestamp", _now_iso())
        _append_jsonl(self._path, entry)
        return entry

    def get_latest(self, n: int = 10) -> list[dict]:
        entries = _read_jsonl(self._path)
        return entries[-n:][::-1]

    def count_cycles(self, agent: str = "orchestrator") -> int:
        return sum(
            1 for e in _read_jsonl(self._path)
            if e.get("agent") == agent and e.get("action") == "cycle_complete"
        )

    def query(self, agent=None, action=None, since=None, until=None,
              limit=100) -> list[dict]:
        results = []
        for e in _read_jsonl(self._path):
            if agent and e.get("agent") != agent:
                continue
            if action and e.get("action") != action:
                continue
            if since:
                ts = e.get("timestamp", "")
                if ts < since.isoformat():
                    continue
            if until:
                ts = e.get("timestamp", "")
                if ts > until.isoformat():
                    continue
            results.append(e)
            if len(results) >= limit:
                break
        return results[::-1]


# ──────────────────────────────────────────────
# ConsentRepository — file backend
# ──────────────────────────────────────────────

class FileConsentRepository(ConsentRepository):
    """Consent contract stored as a YAML file."""

    def __init__(self, path: Path):
        self._path = path

    def load(self) -> dict:
        if not self._path.exists():
            raise FileNotFoundError(f"Consent contract not found: {self._path}")
        with open(self._path) as f:
            return yaml.safe_load(f)

    def check(self, domain: str) -> dict:
        try:
            contract = self.load()
        except FileNotFoundError:
            return {"enabled": False, "domain": domain, "error": "contract_not_found"}

        domain_config = contract.get("domains", {}).get(domain, {})
        if not domain_config:
            return {"enabled": False, "domain": domain, "error": "domain_not_configured"}

        return {
            "enabled": domain_config.get("enabled", False),
            "domain": domain,
            "label": domain_config.get("label", domain),
            "tools": domain_config.get("tools", []),
            "write_paths": domain_config.get("write_paths", []),
            "restrictions": domain_config.get("restrictions", []),
        }

    def status(self) -> str:
        try:
            contract = self.load()
        except FileNotFoundError:
            return "not_found"
        except yaml.YAMLError:
            return "invalid"

        expiry = contract.get("expiry", {})
        duration_days = expiry.get("duration_days")
        if duration_days is None:
            return "active"

        created_str = contract.get("created")
        if not created_str:
            return "active"

        try:
            created = datetime.fromisoformat(created_str)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            expiry_date = created + timedelta(days=duration_days)
            return "active" if datetime.now(timezone.utc) < expiry_date else "expired"
        except (ValueError, TypeError):
            return "active"


# ──────────────────────────────────────────────
# RoutingRepository — file backend
# ──────────────────────────────────────────────

class FileRoutingRepository(RoutingRepository):
    """Routing decisions stored as an append-only JSONL file."""

    def __init__(self, path: Path):
        self._path = path

    def log(self, task_id, task_description, tier, model, provider, complexity) -> dict:
        entry = {
            "timestamp": _now_iso(),
            "task_id": task_id,
            "task_description": task_description[:100],
            "tier": tier,
            "model": model,
            "provider": provider,
            "complexity": complexity,
        }
        _append_jsonl(self._path, entry)
        return entry

    def summarize(self, days: int = 7) -> dict:
        entries = _read_jsonl(self._path)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        tiers = Counter()
        models = Counter()
        total = 0

        for e in entries:
            ts_str = e.get("timestamp", "")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    continue
            tiers[e.get("tier", "unknown")] += 1
            models[e.get("model", "none")] += 1
            total += 1

        return {
            "status": "ok",
            "total_tasks": total,
            "tier_breakdown": dict(tiers.most_common()),
            "model_breakdown": dict(models.most_common()),
            "free_tier_count": tiers.get("free", 0) + tiers.get("cheap-local", 0),
            "paid_tier_count": tiers.get("paid-cheap", 0) + tiers.get("paid-premium", 0),
            "escalation_count": tiers.get("escalation", 0),
        }


# ──────────────────────────────────────────────
# FinancialRepository — file backend
# ──────────────────────────────────────────────

class FileFinancialRepository(FinancialRepository):
    """Financial records stored as a CSV file."""

    def __init__(self, path: Path):
        self._path = path
        self._fieldnames = ["timestamp", "tx_type", "amount", "category", "description"]

    def record_transaction(self, tx_type, amount, category, description="") -> dict:
        entry = {
            "timestamp": _now_iso(),
            "tx_type": tx_type,
            "amount": amount,
            "category": category,
            "description": description,
        }
        _ensure_dir(self._path)
        write_header = not self._path.exists()
        with open(self._path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(entry)
        return entry

    def get_balance(self) -> dict:
        revenue = 0.0
        expenses = 0.0
        for tx in self.get_transactions():
            if tx["tx_type"] == "revenue":
                revenue += float(tx.get("amount", 0))
            elif tx["tx_type"] == "expense":
                expenses += float(tx.get("amount", 0))
        return {"total_revenue": revenue, "total_expenses": expenses, "net": revenue - expenses}

    def get_transactions(self, tx_type=None, since=None, limit=100) -> list[dict]:
        if not self._path.exists():
            return []
        results = []
        with open(self._path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if tx_type and row.get("tx_type") != tx_type:
                    continue
                if since:
                    ts = row.get("timestamp", "")
                    if ts < since.isoformat():
                        continue
                results.append(row)
                if len(results) >= limit:
                    break
        return results[::-1]


# ──────────────────────────────────────────────
# KnowledgeGraphRepository — file backend
# ──────────────────────────────────────────────

class FileKnowledgeGraphRepository(KnowledgeGraphRepository):
    """Knowledge graph stored as a JSONL file of directed edges."""

    def __init__(self, path: Path):
        self._path = path

    def add_edge(self, subject, predicate, obj, weight=1.0, evidence="") -> dict:
        entry = {
            "timestamp": _now_iso(),
            "subject": subject,
            "predicate": predicate,
            "obj": obj,
            "weight": weight,
            "evidence": evidence,
        }
        _append_jsonl(self._path, entry)
        return entry

    def query_edges(self, subject=None, predicate=None, obj=None,
                    min_weight=0.0) -> list[dict]:
        results = []
        for e in _read_jsonl(self._path):
            if subject and e.get("subject") != subject:
                continue
            if predicate and e.get("predicate") != predicate:
                continue
            if obj and e.get("obj") != obj:
                continue
            if e.get("weight", 0) < min_weight:
                continue
            results.append(e)
        return results

    def get_trust_score(self, entity: str) -> float:
        score = 0.0
        for e in _read_jsonl(self._path):
            if e.get("subject") == entity and e.get("predicate") == "trust":
                score += e.get("weight", 0)
            if e.get("obj") == entity and e.get("predicate") == "trust":
                score += e.get("weight", 0)
        return score