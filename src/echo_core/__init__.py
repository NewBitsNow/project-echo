"""
echo_core — Project Echo Core Infrastructure.

Lightweight digital twin framework for autonomous multi-agent systems.

Data layer (architecturally separate):
    DataLayer       — Facade over all data stores (state, log, consent, routing, financial, graph)
    open_repository — One-call convenience to get a configured Repository

    dl = DataLayer(backend="file", base_path="~/.echo-core")
    dl.state.read()
    dl.log.append({"agent": "framehead", "action": "generate"})
    dl.consent.check("code")

Application layer (backward-compatible functional API):
    classify_task, build_packet, read_consent, read_state, log_agent, ...
"""

from echo_core.data import DataLayer, open_repository, Repository

from echo_core.core.classify_task import classify_task
from echo_core.core.packet_builder import build_packet, packet_to_delegation
from echo_core.core.routing_logger import log_routing, summarize_routing
from echo_core.core.consent import (
    read_consent,
    check_consent,
    is_consent_valid,
    load_contract,
    consent_status,
)
from echo_core.core.state import (
    read_state,
    update_state,
    increment_cycle,
    system_status,
    init_state,
)
from echo_core.core.log import (
    log_agent,
    get_latest_logs,
    count_cycles,
    log_entry,
    get_logger,
)
from echo_core.core.module_loader import (
    discover_modules,
    load_module_manifest,
    module_status,
    validate_module,
    list_available_modules,
)

__version__ = "1.1.0"
__all__ = [
    # Data layer
    "DataLayer",
    "open_repository",
    "Repository",
    # Application layer
    "classify_task",
    "build_packet",
    "packet_to_delegation",
    "log_routing",
    "summarize_routing",
    "read_consent",
    "check_consent",
    "is_consent_valid",
    "load_contract",
    "consent_status",
    "read_state",
    "update_state",
    "increment_cycle",
    "system_status",
    "init_state",
    "log_agent",
    "get_latest_logs",
    "count_cycles",
    "log_entry",
    "get_logger",
    "discover_modules",
    "load_module_manifest",
    "module_status",
    "validate_module",
    "list_available_modules",
]