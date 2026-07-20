"""Consent contract — delegates to the data layer backend.

Keeps the existing functional API for backward compatibility.
"""

from pathlib import Path

from echo_core.data.backends import FileConsentRepository

_repo = FileConsentRepository(
    Path("~/.echo-core/state/consent-contract.yaml").expanduser()
)


def set_contract_path(path: str):
    global _repo
    _repo = FileConsentRepository(Path(path).expanduser().resolve())


def load_contract(path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileConsentRepository(Path(path).expanduser().resolve())
    return repo.load()


def is_consent_valid(contract: dict = None) -> bool:
    if contract is not None:
        from datetime import datetime, timedelta, timezone
        expiry = contract.get("expiry", {})
        duration_days = expiry.get("duration_days")
        if duration_days is None:
            return True
        created_str = contract.get("created")
        if not created_str:
            return True
        try:
            created = datetime.fromisoformat(created_str)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) < created + timedelta(days=duration_days)
        except (ValueError, TypeError):
            return True
    return _repo.status() == "active"


def check_consent(domain: str, contract: dict = None) -> dict:
    if contract is not None:
        dcfg = contract.get("domains", {}).get(domain, {})
        if not dcfg:
            return {"enabled": False, "domain": domain, "error": "domain_not_configured"}
        return {
            "enabled": dcfg.get("enabled", False), "domain": domain,
            "label": dcfg.get("label", domain), "tools": dcfg.get("tools", []),
            "write_paths": dcfg.get("write_paths", []),
            "restrictions": dcfg.get("restrictions", []),
        }
    return _repo.check(domain)


def read_consent(path: str = None) -> dict:
    repo = _repo
    if path:
        repo = FileConsentRepository(Path(path).expanduser().resolve())
    try:
        contract = repo.load()
    except FileNotFoundError:
        return {"status": "not_found", "error": "Consent contract not found"}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}

    if not is_consent_valid(contract):
        return {"status": "expired", "twin_id": contract.get("twin_id"),
                "subject": contract.get("subject"),
                "error": "Consent contract has expired"}

    enabled = {}
    for domain, cfg in contract.get("domains", {}).items():
        if cfg.get("enabled", False):
            enabled[domain] = {"label": cfg.get("label", domain),
                               "tools": cfg.get("tools", [])}

    return {
        "status": "active", "twin_id": contract.get("twin_id"),
        "subject": contract.get("subject"), "created": contract.get("created"),
        "enabled_domains": enabled,
        "global_restrictions": contract.get("global_restrictions", []),
        "write_whitelist": contract.get("write_whitelist", []),
    }


def consent_status(path: str = None) -> str:
    repo = _repo
    if path:
        repo = FileConsentRepository(Path(path).expanduser().resolve())
    return repo.status()