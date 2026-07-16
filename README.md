# Project Echo

A multi-agent digital twin system. 10 domain agents, consent-first architecture, model router, knowledge graphs. Built on [Hermes Agent](https://hermes-agent.nousresearch.com).

## Architecture

```
Orchestrator (cron every 60m)
  ├── Code Agent      — FrameHead repo evolution
  ├── Content Agent   — YouTube → 5 formats
  ├── Monitor Agent   — git status, files, disk
  ├── Research Agent  — arXiv, blogs, web
  ├── Comm Agent      — iMessage/SMS (consent-gated)
  ├── Social Agent    — X/Twitter (consent-gated)
  ├── Email Agent     — IMAP/SMTP (consent-gated)
  ├── Archiver Agent  — cleanup, compress
  ├── Framehead Agent — persona content generation
  └── Knowledge Graphs — intent, decision, evidence, operational, trust
```

## Core Concepts

- **Consent-first** — every action checked against a YAML policy contract
- **Model routing** — free/local models for simple tasks, premium for complex
- **Packet protocol** — structured work units with scope, verification, acceptance criteria
- **Cost tracking** — every routing decision logged for savings dashboard

## Project Structure

```
project-echo/
├── README.md              # This file
├── MEMORY.md              # Living document (ADRs, timeline, environment)
├── docs/
│   └── architecture.md    # Full architecture blueprint
├── scripts/
│   ├── classify_task.py   # Model router — task complexity scoring
│   ├── packet_builder.py  # Structured work unit builder
│   ├── routing_logger.py  # Routing decision log + dashboard
│   ├── graph_store.py     # Knowledge graph read/write/search
│   ├── content_agent.py   # YouTube → content pipeline
│   ├── monitor_agent.py   # System health checks
│   ├── research_agent.py  # arXiv + blog search
│   ├── archiver_agent.py  # Cleanup and compression
│   └── framehead_agent.py # Persona content generation
├── config/
│   └── model-tiers.yaml   # 5 model tiers with cost/routing rules
├── tests/
│   ├── test_classify_task.py   # 10 model routing tests
│   └── test_packet_builder.py  # 11 packet protocol tests
└── graphs/
    ├── intent.yaml
    ├── decision.yaml
    ├── evidence.yaml
    ├── operational.yaml
    └── trust.yaml
```

## Quick Start

See [INSTALL.md](INSTALL.md) for the full step-by-step installation guide covering macOS and Linux.

```bash
git clone https://github.com/NewBitsNow/project-echo.git
cd project-echo
pip3 install pyyaml pytest youtube-transcript-api
python3 -m pytest tests/ -v
# 21 tests should pass
```

## Model Routing

| Complexity | Tier | Model | Cost |
|-----------|------|-------|------|
| < 0.3 | Free | qwen/qwen3-coder:free | $0 |
| 0.3–0.6 | Local | qwen2.5-coder:7b (Ollama) | $0 |
| 0.3–0.6 | Cheap | qwen/qwen3-coder | ~$0.0001/1k |
| > 0.6 | Premium | anthropic/claude-sonnet-4 | ~$0.015/1k |
| 1.0 | Escalate | Human (Jason) | — |

## License

MIT