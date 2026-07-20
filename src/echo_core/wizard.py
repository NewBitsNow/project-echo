"""Project Echo — Setup Wizard

Interactive TUI that guides the user through:
1. System check (Python, Hermes, Ollama, tools)
2. Module selection
3. Core configuration
4. Per-module configuration
5. Review & install

Uses questionary if available, falls back to plain input().
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Optional TUI dependencies
try:
    import questionary
    from questionary import Choice, confirm, select, text, password, checkbox
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False
    questionary = None
    print("Tip: pip install echo-core[wizard] for a nicer setup experience")
    print()

# Core paths
TWIN_OUTPUT = Path("~/.echo-core").expanduser()
STATE_DIR = TWIN_OUTPUT / "state"
SCRIPTS_DIR = TWIN_OUTPUT / "scripts"
LOGS_DIR = TWIN_OUTPUT / "logs"
CONFIG_DIR = TWIN_OUTPUT / "config"
CONTENT_DIR = TWIN_OUTPUT / "content"

# ── Module definitions (built-in) ──
# These are the modules that ship with echo_core.
# Third-party modules are discovered via module_loader.

BUILTIN_MODULES = {
    "code": {
        "name": "code",
        "version": "1.0.0",
        "description": "Repo health checks, git status, PR monitoring",
        "size_mb": 1,
        "tools_required": [{"command": "git", "check": "git --version"}],
        "python_deps": [],
        "consent_domain": "code",
        "config_fields": [],
    },
    "framehead": {
        "name": "framehead",
        "version": "1.0.0",
        "description": "Framehead voice content, image generation, YouTube Shorts pipeline",
        "size_mb": 2500,
        "tools_required": [
            {"command": "ollama", "install": "curl -fsSL https://ollama.ai/install.sh | sh",
             "check": "ollama --version", "optional": False},
            {"command": "ffmpeg", "install": "brew install ffmpeg",
             "check": "ffmpeg -version", "optional": False},
            {"command": "comfy", "install": "git clone https://github.com/comfyanonymous/ComfyUI ~/ComfyUI",
             "check": "ls ~/ComfyUI/main.py", "optional": True},
        ],
        "python_deps": ["requests>=2.31", "pillow>=10.0"],
        "consent_domain": "content",
        "config_fields": [
            {"name": "default_voice", "prompt": "Default TTS voice",
             "default": "lessac", "choices": ["lessac", "amy", "libritts", "alan"]},
            {"name": "content_modes", "prompt": "Content modes to generate",
             "default": "observation, one-liner", "type": "text"},
            {"name": "shorts_per_day", "prompt": "Shorts to generate per day",
             "default": "5", "type": "int"},
        ],
    },
    "content": {
        "name": "content",
        "version": "1.0.0",
        "description": "YouTube summaries, blog posts, threads from transcripts",
        "size_mb": 1,
        "tools_required": [],
        "python_deps": ["youtube-transcript-api>=0.6"],
        "consent_domain": "content",
        "config_fields": [],
    },
    "monitor": {
        "name": "monitor",
        "version": "1.0.0",
        "description": "Disk usage, git drift, file change monitoring",
        "size_mb": 1,
        "tools_required": [{"command": "df", "check": "df -h"}],
        "python_deps": [],
        "consent_domain": "monitoring",
        "config_fields": [],
    },
    "research": {
        "name": "research",
        "version": "1.0.0",
        "description": "arXiv paper search, blog monitoring, web research",
        "size_mb": 1,
        "tools_required": [],
        "python_deps": ["requests>=2.31"],
        "consent_domain": "research",
        "config_fields": [],
    },
    "archiver": {
        "name": "archiver",
        "version": "1.0.0",
        "description": "Cache cleanup, temp file removal, compression",
        "size_mb": 1,
        "tools_required": [],
        "python_deps": [],
        "consent_domain": "code",
        "config_fields": [],
    },
    "discord": {
        "name": "discord",
        "version": "1.0.0",
        "description": "Framehead Discord bot — chat with Framehead in your server",
        "size_mb": 50,
        "tools_required": [],
        "python_deps": ["discord.py>=2.3", "httpx>=0.27"],
        "consent_domain": "communications",
        "config_fields": [
            {"name": "bot_token", "prompt": "Discord bot token",
             "default": "", "type": "password"},
            {"name": "channel_whitelist", "prompt": "Channel names (comma-separated)",
             "default": "framehead, bot-testing", "type": "text"},
            {"name": "default_mode", "prompt": "Default Framehead mode",
             "default": "helper", "choices": ["helper", "creative", "blogger", "critic"]},
        ],
    },
    "graphs": {
        "name": "graphs",
        "version": "1.0.0",
        "description": "Knowledge graphs (intent, decision, evidence, operational, trust)",
        "size_mb": 1,
        "tools_required": [],
        "python_deps": [],
        "consent_domain": "code",
        "config_fields": [],
    },
}


# ── Wizard steps ──


def step_system_check() -> dict:
    """Step 1: Check system prerequisites."""
    print("=" * 60)
    print("  Step 1: System Check")
    print("=" * 60)

    checks = {
        "python": {"label": "Python 3.11+", "passed": sys.version_info >= (3, 11)},
        "hermes": {"label": "Hermes Agent", "passed": shutil.which("hermes") is not None},
        "git": {"label": "git", "passed": shutil.which("git") is not None},
        "ffmpeg": {"label": "ffmpeg", "passed": shutil.which("ffmpeg") is not None},
        "ollama": {"label": "Ollama", "passed": shutil.which("ollama") is not None},
        "pyyaml": {"label": "PyYAML", "passed": yaml is not None},
    }

    for name, check in checks.items():
        icon = check["passed"]
        if icon:
            print(f"  ✓ {check['label']}")
        else:
            print(f"  ⚠ {check['label']} — not found (optional for some modules)")

    print()
    return checks


def step_select_modules(checks: dict) -> list[str]:
    """Step 2: Let the user choose which modules to install."""
    print("=" * 60)
    print("  Step 2: Choose Modules")
    print("  (Core is always included)")
    print("=" * 60)
    print()

    # Check which modules are viable
    module_choices = []
    for name, mod in BUILTIN_MODULES.items():
        mod_checks = []
        for tool in mod.get("tools_required", []):
            cmd = tool["command"].split()[0]
            if not checks.get(cmd, {}).get("passed", shutil.which(cmd) is not None):
                mod_checks.append(f"missing: {cmd}")

        label = f"{mod['description']}"
        if mod_checks:
            label += f" (⚠ {', '.join(mod_checks)})"
        if mod["size_mb"] > 100:
            label += f" [~{mod['size_mb'] // 1000}GB]"

        module_choices.append({
            "name": name,
            "label": label,
            "size_mb": mod["size_mb"],
        })

    if HAS_QUESTIONARY:
        selected = questionary.checkbox(
            "Select modules to install (space to toggle, enter to confirm):",
            choices=[
                Choice(f"{m['label']}", value=m["name"], checked=False)
                for m in module_choices
            ],
        ).ask() or []
    else:
        print("Available modules:")
        for i, m in enumerate(module_choices, 1):
            print(f"  [{i}] {m['label']}")
        print()
        raw = input("Enter numbers (comma-separated, e.g. 1,3,5): ").strip()
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(module_choices):
                    selected.append(module_choices[idx]["name"])
        if not selected:
            print("  (none selected — core only)")

    print(f"  Selected: {', '.join(selected) if selected else 'core only'}")
    print()
    return selected


def step_configure_core() -> dict:
    """Step 3: Configure core settings."""
    print("=" * 60)
    print("  Step 3: Configure Core")
    print("=" * 60)

    if HAS_QUESTIONARY:
        config = {
            "twin_id": text("Twin ID:", default="echo-twin-v1").ask(),
            "twin_name": text("Twin name:", default="Project Echo Twin").ask(),
            "schedule": select("Wake schedule:", choices=[
                "every 30m", "every 60m", "every 2h", "every 6h", "every 12h", "daily"
            ], default="every 60m").ask(),
            "data_dir": text("Data directory:", default=str(TWIN_OUTPUT)).ask(),
        }
    else:
        config = {
            "twin_id": input(f"  Twin ID [{'echo-twin-v1'}]: ").strip() or "echo-twin-v1",
            "twin_name": input(f"  Twin name [{'Project Echo Twin'}]: ").strip() or "Project Echo Twin",
            "schedule": input(f"  Wake schedule [{'every 60m'}]: ").strip() or "every 60m",
            "data_dir": input(f"  Data directory [{str(TWIN_OUTPUT)}]: ").strip() or str(TWIN_OUTPUT),
        }

    print()
    return config


def step_configure_modules(modules: list[str]) -> dict:
    """Step 4: Configure each selected module."""
    configs = {}

    for name in modules:
        mod = BUILTIN_MODULES.get(name)
        if not mod:
            continue

        fields = mod.get("config_fields", [])
        if not fields:
            continue

        print("=" * 60)
        print(f"  Configure Module: {name}")
        print("=" * 60)

        module_config = {}
        for field in fields:
            fname = field["name"]
            prompt = field.get("prompt", fname)
            default = field.get("default", "")
            ftype = field.get("type", "text")
            choices = field.get("choices")

            if HAS_QUESTIONARY:
                if ftype == "password":
                    value = password(prompt).ask()
                elif choices:
                    value = select(prompt, choices=choices, default=default).ask()
                else:
                    value = text(prompt, default=default).ask()
            else:
                if choices:
                    print(f"  {prompt} [{default}]: ", end="")
                    value = input().strip() or default
                elif ftype == "password":
                    print(f"  {prompt}: ", end="")
                    value = input().strip()
                else:
                    value = input(f"  {prompt} [{default}]: ").strip() or default

            if ftype == "int" and value:
                try:
                    value = int(value)
                except ValueError:
                    value = default

            module_config[fname] = value

        configs[name] = module_config
        print()

    return configs


def generate_consent_contract(modules: list[str], config: dict) -> str:
    """Generate a consent contract YAML based on selected modules."""
    domain_map = {
        "code": "code",
        "content": "content",
        "framehead": "content",
        "monitor": "monitoring",
        "research": "research",
        "archiver": "code",
        "discord": "communications",
        "graphs": "code",
    }

    domains = {}
    for module in modules:
        mod = BUILTIN_MODULES.get(module, {})
        domain_name = mod.get("consent_domain", module)
        if domain_name not in domains:
            domains[domain_name] = {
                "enabled": True,
                "label": f"{module.capitalize()} Agent",
                "tools": ["terminal", "file"],
                "write_paths": [
                    str(SCRIPTS_DIR / "**"),
                    str(LOGS_DIR / "**"),
                ],
                "restrictions": [],
            }

    contract = {
        "twin_id": config.get("twin_id", "echo-twin-v1"),
        "subject": config.get("twin_name", "Project Echo Twin"),
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "version": 1,
        "human_contact": {
            "primary": None,
            "backup": None,
            "cooldown_seconds": 3600,
        },
        "domains": domains,
        "global_restrictions": [
            "spending money or authorizing payments of any kind",
            "sending messages, emails, or communications to third parties",
            "modifying system configuration (hostname, network, security settings)",
            "deleting files outside the project or echo-core directories",
            "accessing financial accounts, credentials, or secrets",
            "modifying the consent contract itself",
            "modifying the Hermes configuration or profile settings",
            "installing system-level software without human approval",
            "committing or pushing to git without a review cycle",
            "modifying or deleting logs",
        ],
        "write_whitelist": [
            str(SCRIPTS_DIR / "**"),
            str(LOGS_DIR / "**"),
            str(STATE_DIR / "**"),
            str(CONFIG_DIR / "**"),
            str(CONTENT_DIR / "**"),
        ],
        "escalation": {
            "cooldown_seconds": 3600,
            "on_boundary_hit": "pause_domain",
            "on_revocation": "halt_all",
        },
        "expiry": {
            "duration_days": None,
            "auto_renew": False,
            "on_expiry": "halt_and_report",
        },
    }

    return yaml.dump(contract, default_flow_style=False) if yaml else str(contract)


def generate_state_file(config: dict) -> dict:
    """Generate the initial system state."""
    return {
        "twin_id": config.get("twin_id", "echo-twin-v1"),
        "twin_name": config.get("twin_name", "Project Echo Twin"),
        "status": "active",
        "current_cycle": 0,
        "last_wake": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
        "last_report_sent": None,
        "active_domains": [],
        "pending_escalations": [],
        "consent_contract_hash": None,
    }


def install(
    modules: list[str],
    core_config: dict,
    module_configs: dict,
) -> dict:
    """Perform the actual installation."""
    results = {"status": "ok", "steps": []}

    # 1. Create directory structure
    for d in [STATE_DIR, SCRIPTS_DIR, LOGS_DIR, CONFIG_DIR, CONTENT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    results["steps"].append({"action": "directories", "status": "created"})

    # 2. Write consent contract
    contract_yaml = generate_consent_contract(modules, core_config)
    contract_path = STATE_DIR / "consent-contract.yaml"
    contract_path.write_text(contract_yaml)
    results["steps"].append({"action": "consent_contract", "path": str(contract_path)})

    # 3. Write state file
    state = generate_state_file(core_config)
    state_path = STATE_DIR / "system-state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
    results["steps"].append({"action": "state_file", "path": str(state_path)})

    # 4. Write module configs
    for module, cfg in module_configs.items():
        if cfg:
            cfg_path = CONFIG_DIR / f"{module}-config.json"
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            results["steps"].append({"action": f"config_{module}", "path": str(cfg_path)})

    # 5. Write config for each module
    for module in modules:
        mod = BUILTIN_MODULES.get(module, {})
        # Create module config directory
        mod_dir = Path(f"~/.echo-core/modules/{module}").expanduser()
        mod_dir.mkdir(parents=True, exist_ok=True)
        # Write .installed marker
        (mod_dir / ".installed").write_text(json.dumps({
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "version": mod.get("version", "1.0.0"),
        }))
        results["steps"].append({"action": f"module_{module}", "status": "installed"})

    # 6. Create cron job
    try:
        skills = ["autonomous-ai-agents/echo-twin-orchestrator"]
        if "code" in modules:
            skills.append("autonomous-ai-agents/echo-twin-code-agent")
        # Add more skills based on modules

        result = subprocess.run(
            ["hermes", "cron", "create",
             "--name", "echo-twin-heartbeat",
             "--schedule", core_config.get("schedule", "every 60m"),
             "--skills", ",".join(skills),
             "--deliver", "local",
             "--prompt", "You are the Project Echo Twin — Orchestrator Cycle."],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            results["steps"].append({"action": "cron_job", "status": "created"})
        else:
            results["steps"].append({"action": "cron_job", "status": "skipped",
                                     "note": result.stderr.strip()[:200]})
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        results["steps"].append({"action": "cron_job", "status": "skipped",
                                 "note": str(e)[:200]})

    results["status"] = "ok"
    return results


def print_summary(modules: list[str], core_config: dict, install_result: dict):
    """Print a summary of what was installed."""
    total_size = 0
    for name in modules:
        total_size += BUILTIN_MODULES.get(name, {}).get("size_mb", 0)

    print()
    print("=" * 60)
    print("  INSTALLATION COMPLETE")
    print("=" * 60)
    print()
    print(f"  Modules: {', '.join(modules) if modules else 'core only'}")
    print(f"  Estimated disk: {total_size} MB")
    print(f"  Data directory: {core_config.get('data_dir', TWIN_OUTPUT)}")
    print(f"  Schedule: {core_config.get('schedule', 'every 60m')}")
    print()
    print("  Files created:")
    for step in install_result.get("steps", []):
        path = step.get("path", step.get("status", ""))
        print(f"    • {step['action']}: {path}")
    print()
    print("  Next steps:")
    print("    1. Edit the consent contract:")
    print(f"       {STATE_DIR / 'consent-contract.yaml'}")
    print("    2. Verify the cron job:")
    print("       hermes cron list")
    print("    3. Watch the first cycle:")
    print(f"       tail -f {LOGS_DIR / 'agent-log.jsonl'}")
    print()
    print("  Framehead is watching. 👁️")


def main():
    """Run the full setup wizard."""
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║      Project Echo — Setup Wizard                            ║")
    print("  ║      Your digital twin, one module at a time                ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()

    checks = step_system_check()
    modules = step_select_modules(checks)
    core_config = step_configure_core()
    module_configs = step_configure_modules(modules)

    # Summary
    print("=" * 60)
    print("  Review & Install")
    print("=" * 60)
    print()
    print(f"  Modules: {', '.join(modules) if modules else 'core only'}")
    print(f"  Schedule: {core_config.get('schedule', 'every 60m')}")
    print(f"  Directory: {core_config.get('data_dir', str(TWIN_OUTPUT))}")
    print()

    if HAS_QUESTIONARY:
        proceed = confirm("Proceed with installation?", default=True).ask()
    else:
        proceed = input("  Proceed with installation? [Y/n]: ").strip().lower() != "n"

    if not proceed:
        print("  Installation cancelled.")
        return

    # Install
    result = install(modules, core_config, module_configs)
    print_summary(modules, core_config, result)


if __name__ == "__main__":
    main()