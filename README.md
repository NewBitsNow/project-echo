# Project Echo

> Lightweight digital twin infrastructure for autonomous multi-agent systems.

Project Echo is an open-source framework for building persistent, policy-governed autonomous agents — a "digital twin" that works alongside you. It provides model routing, structured delegation, consent management, and a modular agent system — all designed to run locally with zero recurring cost.

## Quick Start

```bash
# Install from source
pip install -e .

# Launch the setup wizard
python -m echo_core.wizard

# Or use the CLI
python -m echo_core
```

## Architecture

```
Runtime (cron) ←→ Orchestrator — delegates → Domain Agents
                       │
                       ├── Core Infrastructure
                       │   ├── classify_task()     — model routing (5 tiers)
                       │   ├── build_packet()      — structured delegation
                       │   ├── read_consent()      — policy enforcement
                       │   ├── read_state()        — cycle tracking
                       │   └── log_agent()         — audit trail
                       │
                       ├── Inference Engine
                       │   ├── llama.cpp / llama-server  — GGUF local inference
                       │   ├── Ornith-1.0-9b           — primary reasoning model
                       │   └── DSpark (optional)        — 2x speculative decoding
                       │
                       ├── Domain Agents
                       │   ├── code_agent          — repo health, git checks
                       │   ├── content_agent       — YouTube summaries, blogs
                       │   ├── monitor_agent       — disk, files, drift
                       │   ├── research_agent      — arXiv, web research
                       │   ├── framehead_agent     — digital consciousness content
                       │   ├── archiver_agent      — cleanup, compression
                       │   ├── night_shift         — monetization drive
                       │   ├── offscreen_content   — batch content generation
                       │   └── shorts_pipeline     — YouTube Shorts production
                       │
                       └── Consent Contract (YAML)
                           └── policy file governs every action
```

## Inference Model: Ornith-1.0-9b

Echo runs on a local **Ornith-1.0-9b** model (Q4_K_M, 5.6GB, 8.95B params) served via `llama-server`. Key characteristics:

| Property | Value |
|----------|-------|
| Architecture | 8.95B params, 4096 embd, 248K vocab |
| Quantization | Q4_K_M (4-bit, 5.6GB file) |
| Runtime context | 32,768 tokens |
| Generation speed | ~21 tok/s on Apple Silicon (Metal GPU) |
| Reasoning | Built-in chain-of-thought — outputs "Thinking Process:" before every answer |
| Chat template | Requires `--reasoning-preserve` flag to separate reasoning from content |
| Concurrent slots | 4 (queues excess requests gracefully) |

### Reasoning Model Behavior

Ornith is a **thinking/reasoning model** — it always outputs a chain-of-thought reasoning process before every answer. This is baked into the model architecture and cannot be suppressed. Key implications:

- **100-1,000+ tokens** of reasoning per query are consumed before content appears
- System prompts to suppress reasoning are **ignored** by the model
- The `--reasoning-preserve` flag correctly separates `reasoning_content` (thinking) from `content` (answer)
- **max_tokens must be set 2-3x higher** than expected output to account for reasoning overhead
- The model is best suited for analysis, planning, and evaluation tasks

### DSpark Speculative Decoding (Optional, 2x Speedup)

DSpark is a speculative decoding framework that doubles inference speed with **zero quality loss**:

- Uses a tiny draft model (~2B) to predict 5-7 tokens in parallel
- Target model verifies predictions in a single forward pass
- **Ornith-1.0-9B: 2.1-2.4x speedup** (21 → ~61 tok/s)
- Native Apple Silicon port: `mlx-dspark` (github.com/ARahim3/mlx-dspark)
- Exposes OpenAI-compatible API — drop-in replacement for llama-server
- Requires ~13GB peak RAM on 8-bit target (recommended for 32GB+ machines)

See `docs/dspark-research.md` and `docs/ornith-stress-test-report.md` for detailed analysis.

## Core API

```python
from echo_core import (
    classify_task,      # Task complexity → cheapest adequate model
    build_packet,       # Structured delegation packets
    read_consent,       # Consent contract reader
    read_state,         # System state file reader
    increment_cycle,    # Cycle counter for recurring work
    log_agent,          # Append-only agent audit log
    discover_modules,   # Module discovery and validation
)

# Route a task to the cheapest adequate model
result = classify_task("fix a typo in the README")
# → {"tier": "free", "model": "qwen/qwen3-coder:free", "complexity": 0.05}

# Build a structured delegation packet
packet = build_packet(
    mission="Add rate limiting to the API gateway",
    scope=["src/api/**"],
    verification_commands=["pytest tests/api/ -q"],
)

# Check the consent policy before acting
status = read_consent()
if status["status"] == "active":
    print("System is active — proceeding")

# Track cycles for recurring work
state = increment_cycle()
print(f"Cycle {state['current_cycle']}")

# Log every action for the audit trail
log_agent("orchestrator", "cycle_complete",
          {"summary": "All checks passed", "status": "completed"})
```

## Design Principles

1. **Consent-first** — Every agent checks a YAML policy file before acting. No action is taken without explicit permission.
2. **Cost-optimized** — Tasks are routed to the cheapest adequate model. Local models preferred over API calls.
3. **Auditable** — Every decision is logged to an append-only JSONL file. Nothing is hidden.
4. **Modular** — Domain agents are independent. Enable/disable them via the consent contract.
5. **Local-first** — Designed to run entirely on your machine. Zero cloud dependency for routine operations.

## Model Routing

Tasks are classified by complexity (0.0–1.0) and routed to the cheapest adequate tier:

| Tier | Cost | When | Model |
|------|------|------|-------|
| free | $0 | Simple edits, read-only queries | qwen3-coder:free |
| cheap-local | $0 | Small tasks, tests, code review | Local Ornith-9B / Ollama |
| paid-cheap | ~$0.0001/K | Medium tasks, docs | qwen3-coder |
| paid-premium | ~$0.015/K | Architecture, complex tasks | claude-sonnet-4 |
| escalation | — | Can't handle | Human operator |

Configure tiers in `src/echo_core/config/model-tiers.yaml`.

## Configuration

All configuration is done through:
1. **Consent contract** — YAML policy file defining domain permissions and global restrictions
2. **System state** — JSON file tracking cycle number, status, and escalation flags
3. **Model tiers** — YAML file defining routing tiers and model endpoints

Default paths are relative to `~/.echo-core/`. Override any path at runtime using the `set_*_path()` functions.

## Testing

```bash
cd echo-core/src
python -m pytest ../tests/ -v
```

## Project Structure

```
echo-core/
├── pyproject.toml           # Package metadata
├── LICENSE                  # MIT license
├── README.md                # This file
├── install.sh               # One-command installer
├── src/
│   └── echo_core/
│       ├── __init__.py      # Public API
│       ├── __main__.py      # CLI entry point
│       ├── wizard.py        # Setup wizard
│       ├── core/
│       │   ├── classify_task.py    # Model routing
│       │   ├── packet_builder.py   # Delegation packets
│       │   ├── routing_logger.py   # Cost tracking
│       │   ├── consent.py          # Contract reader
│       │   ├── state.py            # State file CRUD
│       │   ├── log.py              # Agent log writer
│       │   └── module_loader.py    # Module discovery
│       └── config/
│           └── model-tiers.yaml    # 5-tier model config
├── agents/                  # Domain agent scripts
├── tests/                   # Test suite (40+ tests)
├── examples/                # Example config files
└── docs/                    # Documentation
    ├── echo-architecture.md           # Full architecture spec
    ├── echo-brand-guide.md            # Brand identity
    ├── echo-user-guide.md             # Comprehensive user guide
    ├── echo-modularization-analysis.md # Module system design
    ├── dspark-research.md             # DSpark spec decoding analysis
    └── ornith-stress-test-report.md   # Model benchmark results
```

## Documentation

- `docs/echo-architecture.md` — Full system architecture and component design
- `docs/echo-user-guide.md` — Complete user guide for operating Project Echo
- `docs/echo-brand-guide.md` — Brand identity, voice, and visual system
- `docs/dspark-research.md` — DSpark speculative decoding research
- `docs/ornith-stress-test-report.md` — Ornith model benchmark and context windowing analysis
- `examples/consent-contract.yaml` — Example consent policy
- `examples/system-state.json` — Example system state

## License

MIT — see LICENSE for details.
