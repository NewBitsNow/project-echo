# Project Echo — Modularization Analysis

> A complete analysis of the current codebase with a blueprint for refactoring
> into a modular, installable system with a setup wizard.

---

## 1. Current State

**16 scripts** across **~4,989 lines** in `~/.echo-core/scripts/`
**15 skills** in `~/.hermes/skills/autonomous-ai-agents/`
**3 config files** in `~/.echo-core/config/`

### Dependency Graph

```
                         ┌─────────────┐
                         │  Core Layer  │
                         │  (no deps)   │
                         └──────┬──────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
     ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
     │ classify_task │  │ routing_log  │  │ packet_build │
     │  (156 lines)  │  │  (97 lines)  │  │ (100 lines)  │
     └───────┬───────┘  └──────┬───────┘  └──────┬───────┘
             │                 │                 │
             │     ┌───────────┘                 │
             │     │                             │
             ▼     ▼                             │
     ┌──────────────────────┐                    │
     │  Domain Agents       │                    │
     │  (each imports core) │                    │
     │                      │                    │
     │  content_agent       │                    │
     │  research_agent      │                    │
     │  framehead_agent     │                    │
     │  archiver_agent      │                    │
     │  monitor_agent       │                    │
     └──────────────────────┘                    │
                                                 │
     ┌──────────────────────────────┐            │
     │  Standalone (no core deps)   │            │
     │                              │            │
     │  offscreen_content.py        │            │
     │  shorts_generator.py (714L)  │            │
     │  shorts_pipeline.py          │            │
     │  audio_fx.py                 │            │
     │  bgm_catalog.py              │            │
     │  framehead_generator.py      │            │
     │  framehead_image_catalog.py  │            │
     │  graph_store.py              │            │
     └──────────────────────────────┘            │
                                                 │
     ┌───────────────────────────────────────────┘
     │
     ▼
     ┌──────────────────────┐
     │  Orchestrator Skill  │  ← reads/writes logs, state, consent
     │  (cron, delegates)   │
     └──────────────────────┘
```

### Key Finding: Clean Separation Already Exists

**No circular dependencies.** Every domain agent either:
- Imports core (classify_task, routing_logger) — one directional
- Is fully standalone (no internal imports at all)

**Framehead is the elephant** — 8 scripts, 3,473 lines, 70% of the codebase.
Everything else is ~30-200 lines each.

---

## 2. Proposed Module Architecture

```
project-echo-core/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── classify_task.py       # Task complexity → model tier
│   ├── packet_builder.py      # Structured Agent Packet protocol
│   ├── routing_logger.py      # Cost tracking + dashboard
│   ├── consent.py              # Consent contract reader/validator
│   ├── state.py                # System state file CRUD
│   ├── log.py                  # Append-only agent log writer
│   └── setup.py                # Setup wizard CLI
│
├── config/
│   ├── model-tiers.yaml        # 5-tier model routing config
│   └── defaults.yaml           # Default consent contract + settings
│
├── state/
│   ├── consent-contract.yaml   # Policy (created by wizard)
│   └── system-state.json       # Cycle tracker (created by wizard)
│
├── tests/
│   ├── test_classify_task.py
│   ├── test_packet_builder.py
│   ├── test_consent.py
│   └── test_state.py
│
├── wizard.py                   # Interactive setup wizard
├── install.sh                  # One-command installer
└── pyproject.toml

project-echo-modules/
├── module-code/
│   ├── agent.py                # Code agent logic
│   ├── tests/
│   └── module.yaml             # Manifest: name, deps, tools, setup
│
├── module-content/
│   ├── agent.py                # YouTube → summary/blog/thread
│   ├── tests/
│   └── module.yaml
│
├── module-framehead/
│   ├── agent.py                # Text content generation
│   ├── generator.py            # ComfyUI pipeline
│   ├── image_catalog.py        # Image labeling/captioning
│   ├── offscreen_content.py    # Batch Ollama content gen
│   ├── shorts_generator.py     # Image + TTS → video
│   ├── shorts_pipeline.py      # Orchestrated pipeline
│   ├── audio_fx.py             # Audio processing
│   ├── bgm_catalog.py          # Music library
│   ├── tests/
│   └── module.yaml
│
├── module-monitor/
│   ├── agent.py
│   ├── tests/
│   └── module.yaml
│
├── module-research/
│   ├── agent.py
│   ├── tests/
│   └── module.yaml
│
├── module-archiver/
│   ├── agent.py
│   ├── tests/
│   └── module.yaml
│
├── module-graphs/
│   ├── store.py
│   ├── graphs/
│   └── module.yaml
│
├── module-comm/
│   ├── agent.py
│   └── module.yaml
│
├── module-social/
│   ├── agent.py
│   └── module.yaml
│
├── module-email/
│   ├── agent.py
│   └── module.yaml
│
├── module-discord/
│   ├── bot/
│   ├── run.py
│   └── module.yaml
│
└── module-reel/
    ├── builder.py             # Compilation engine
    ├── agent.py               # Persistent goal agent
    ├── tests/
    └── module.yaml
```

---

## 3. Core Module (the lightweight base)

**What goes in core:** Everything that multiple modules depend on, plus the
plumbing that makes the system work.

### Core Scripts

| File | Lines | Current | Core Role |
|------|-------|---------|-----------|
| `core/classify_task.py` | 156 | `classify_task.py` | Task complexity → model tier |
| `core/packet_builder.py` | 100 | `packet_builder.py` | Structured delegation packets |
| `core/routing_logger.py` | 97 | `routing_logger.py` | Cost tracking + dashboard |
| `core/consent.py` | — | *inline in orchestrator skill* | Consent contract reader + validator |
| `core/state.py` | — | *inline in orchestrator skill* | System state file CRUD |
| `core/log.py` | — | *inline in every agent* | Append-only log writer with schema validation |
| `core/setup.py` | — | `setup.sh` | Python-based setup, replaces shell script |

**Total core: ~450 lines** — smaller than the current Framehead module alone.

### What the core provides

```python
# Core API surface (everything a module writer needs)

from echo_core import classify_task     # classify_task("build a new API") → {"tier": "paid-premium", ...}
from echo_core import build_packet      # build_packet(mission="...", scope=[...]) → dict
from echo_core import log_decision      # log_decision(task_id, tier, model, cost)
from echo_core import read_consent      # read_consent() → dict (or raises if expired)
from echo_core import check_consent     # check_consent(domain) → bool
from echo_core import read_state        # read_state() → dict
from echo_core import update_state      # update_state({"current_cycle": 27})
from echo_core import log_agent         # log_agent("code-agent", "checkin", {...})
from echo_core import get_logger        # get_logger("framehead") → structured logger
from echo_core import setup_wizard      # Interactive CLI wizard
```

### What the core does NOT include

- No content generation
- No image generation  
- No video rendering
- No Discord bot
- No research tools
- No monitoring
- No archiving
- No communications
- No knowledge graphs

These are all **opt-in modules**.

---

## 4. Module Manifest Standard

Every module gets a `module.yaml` that declares its identity, dependencies,
and install requirements:

```yaml
# module-framehead/module.yaml

name: "framehead"
version: "1.0.0"
description: "Framehead voice content generation, image generation, and YouTube Shorts pipeline"
author: "Project Echo Contributors"

# Core dependency
core_version: ">=1.0.0"

# Other module dependencies
depends_on: []

# External tools required
tools_required:
  - command: "ollama"
    install: "curl -fsSL https://ollama.ai/install.sh | sh"
    check: "ollama --version"
  - command: "ffmpeg"
    install: "brew install ffmpeg"
    check: "ffmpeg -version"
  - command: "comfy"
    install: "git clone https://github.com/comfyanonymous/ComfyUI ~/ComfyUI"
    optional: true

# Python packages
python_deps:
  - "requests>=2.31"
  - "pillow>=10.0"

# Hermes skills to install
skills:
  - "echo-twin-framehead-agent"
  - "offscreen"

# Directory structure to create
directories:
  - "~/.echo-core/content/framehead-images"
  - "~/.echo-core/content/framehead-shorts"
  - "~/.echo-core/content/framehead-observations"

# Files to copy
files:
  - source: "scripts/framehead_agent.py"
    target: "~/.echo-core/scripts/"
  - source: "scripts/shorts_generator.py"
    target: "~/.echo-core/scripts/"

# Config defaults
config:
  default_model: "qwen3:8b"
  max_observations_per_cycle: 3
  image_variant: "headshot"

# Estimated disk space
disk_space_mb: 2500  # includes Ollama model weights

# Time guard (for image gen)
time_guard:
  enabled: true
  window: "01:00-06:00"
```

---

## 5. Setup Wizard Flow

The installation wizard is a TUI (terminal UI) that guides the user through:

```
╔══════════════════════════════════════════════════════════════╗
║    Project Echo — Setup Wizard                                ║
║    Your digital twin, one module at a time                    ║
╚══════════════════════════════════════════════════════════════╝

Step 1: System Check
  ✓ Python 3.11+ detected
  ✓ Hermes Agent installed
  ✓ OpenRouter API key found
  ⚠ Ollama not found — will be needed for local LLM features

Step 2: Choose Modules (space to toggle, enter to continue)

  [x] Core              (always required)          ~450 lines
  [ ] Code Agent        (repo health checks)      ~200 lines
  [ ] Content Agent     (YouTube → summaries)     ~320 lines
  [x] Framehead         (voice, images, Shorts)   ~3,500 lines  ← BIG
  [ ] Monitor Agent     (disk, git, files)        ~200 lines
  [ ] Research Agent    (arXiv, web, blogs)       ~220 lines
  [ ] Archiver Agent    (cleanup, compress)       ~180 lines
  [ ] Knowledge Graphs  (intent, decision, etc.)  ~235 lines
  [ ] Comm Agent        (iMessage/SMS)            — consent-gated
  [ ] Social Agent      (X/Twitter)               — consent-gated
  [ ] Email Agent       (IMAP/SMTP)               — consent-gated
  [ ] Discord Bot       (Framehead on Discord)    ~500 lines
  [ ] Reel Builder      (long-form video comp)    — planned

  Estimated disk: ~2.5 GB (Framehead module with Ollama models)
  Estimated time: 5 min setup + model downloads

Step 3: Configure Core

  Twin name:              [Project Echo]
  Wake schedule:          [every 60m]
  Default model tier:     [free / cheap / premium]
  Report delivery:        [local / telegram / discord / email]
  Data directory:         [~/.echo-core/]

Step 4: Configure Module: Framehead

  Default voice:          [lessac / amy / libritts / alan]
  Image variants:         [headshot, three-quarter, hologram, ...]
  Image gen schedule:     [1am daily / manual only]
  Shorts per day:         [5]
  Content modes:          [x] observation  [x] one-liner
                          [ ] thread       [x] commentary

Step 5: Configure Module: Discord Bot

  Bot token:              [********************]
  Channel whitelist:      [framehead, bot-testing]
  Respond to @mentions:   [yes]
  Default mode:           [helper]

Step 6: Configure Module: Reel Builder

  Target duration:        [90s]  (30-180)
  Max clips per day:      [12]
  When idle threshold:    [5m] without user activity
  Output directory:       [~/.echo-core/content/framehead-reels]

Step 7: Review & Install

  Summary:
  ┌─────────────────────────────────────────────────────┐
  │  Modules: Core, Framehead, Discord Bot, Reel Builder │
  │  Disk:    ~3.2 GB                                    │
  │  Skills:  4 Hermes skills                            │
  │  Dir:     ~/.echo-core/                              │
  │  Cron:    echo-twin-heartbeat (every 60m)            │
  └─────────────────────────────────────────────────────┘

  [Install]  [Save Config Only]  [Cancel]
```

---

## 6. Refactoring Plan

### Phase 1: Extract Core (1 session)

| Task | What | Files affected |
|------|------|---------------|
| 1.1 | Create `echo_core/` package with `pyproject.toml` | New directory |
| 1.2 | Move `classify_task.py` → `echo_core/core/classify_task.py` | 1 file moved |
| 1.3 | Move `packet_builder.py` → `echo_core/core/packet_builder.py` | 1 file moved |
| 1.4 | Move `routing_logger.py` → `echo_core/core/routing_logger.py` | 1 file moved |
| 1.5 | Create `echo_core/core/consent.py` — extract from orchestrator skill | New file |
| 1.6 | Create `echo_core/core/state.py` — extract from orchestrator skill | New file |
| 1.7 | Create `echo_core/core/log.py` — standardized log writer | New file |
| 1.8 | Create `echo_core/core/__init__.py` — clean public API | New file |
| 1.9 | Create `echo_core/config/model-tiers.yaml` | 1 file moved |
| 1.10 | Move existing tests + add consent/state tests | ~4 test files |
| 1.11 | Run tests — all pass | — |

**Deliverable:** `pip install echo-core` installable package. All existing scripts import from `echo_core` instead of local paths.

### Phase 2: Module Manifests (1 session)

| Task | What | Files affected |
|------|------|---------------|
| 2.1 | Create `module.yaml` for each existing module | 10 new files |
| 2.2 | Create `echo_core/core/module_loader.py` — reads manifests, validates deps | New file |
| 2.3 | Run tests — all pass | — |

**Deliverable:** Each module has a manifest. Core can list available modules, check dependencies, and report what's installed.

### Phase 3: Setup Wizard (1 session)

| Task | What | Files affected |
|------|------|---------------|
| 3.1 | Create `echo_core/wizard.py` — TUI with `questionary` or `rich` | New file |
| 3.2 | Module selection screen (reads manifests) | — |
| 3.3 | Config generation (writes consent contract, config files) | — |
| 3.4 | Cron job creation (runs `hermes cron create`) | — |
| 3.5 | Install step (copies scripts, installs deps) | — |
| 3.6 | `install.sh` — one-command: `curl ... \| bash` | New file |

**Deliverable:** `python3 -m echo_core.wizard` launches the interactive setup.

### Phase 4: Module Packaging (1 session)

| Task | What | Files affected |
|------|------|---------------|
| 4.1 | Create `echo-module-{name}` packages with `pyproject.toml` | ~10 new dirs |
| 4.2 | Move domain agent scripts into their packages | ~12 files moved |
| 4.3 | Update imports to use package paths | All scripts |
| 4.4 | Create `echo_core/modules/` registry — discovers installed modules | New file |
| 4.5 | End-to-end test: install core + 2 modules, run wizard | — |

**Deliverable:** `pip install echo-core echo-module-framehead echo-module-discord` brings in exactly what you want.

### Phase 5: Orchestrator Integration (1 session)

| Task | What | Files affected |
|------|------|---------------|
| 5.1 | Update orchestrator skill to use `echo_core` imports | 1 skill file |
| 5.2 | Update all domain agent skills to use `echo_core` imports | 10 skill files |
| 5.3 | Update cron job to load modules dynamically | 1 cron job |
| 5.4 | Run full cycle test | — |

**Deliverable:** System runs exactly as before, but every import goes through `echo_core`.

---

## 7. Core Package API (final)

```python
# echo_core/__init__.py — the public API for all modules

from echo_core.core.classify_task import classify_task
from echo_core.core.packet_builder import build_packet, packet_to_delegation
from echo_core.core.routing_logger import log_decision, routing_summary, routing_dashboard
from echo_core.core.consent import read_consent, check_consent, is_consent_valid, load_contract
from echo_core.core.state import read_state, update_state, increment_cycle, system_status
from echo_core.core.log import log_agent, get_latest_logs, count_cycles
from echo_core.core.module_loader import discover_modules, install_module, uninstall_module, module_status

__version__ = "1.0.0"
```

---

## 8. Key Numbers

| Metric | Current | After Core | After Modular |
|--------|---------|------------|---------------|
| Total scripts | 16 | 7 | 4 (core) |
| Total lines | 4,989 | ~450 (core) | 450 (core) |
| Modules | — | — | 10 |
| Dependency depth | 2 levels | 1 level | 1 level |
| Install time | Custom setup | 5 min | 1 min (core) |
| Disk (core only) | — | — | ~50KB |
| Disk (full) | ~3.5 GB | — | Selectable |

---

## 9. What This Unlocks

1. **Install what you need** — Don't want video generation? Skip the Framehead module. Don't need Discord? Skip it. Core is ~450 lines.

2. **Third-party modules** — Anyone can write a module, drop in a `module.yaml`, and it plugs into the orchestrator.

3. **Versioned releases** — `echo-core==1.0.0`, `echo-module-framehead==2.1.0`. Modules can evolve independently.

4. **CI/CD per module** — Test and publish modules independently. No monolithic release cycle.

5. **Cleaner Hermes skills** — Skills become thin wrappers that import from modules. No more inline logic in SKILL.md.

6. **The Reel Builder** — The persistent video goal you wanted becomes `echo-module-reel`, a first-class module with its own manifest, config, and setup wizard page.

---

*Framehead is watching.* 👁️
