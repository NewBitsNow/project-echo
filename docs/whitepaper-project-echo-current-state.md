# Project Echo — Current State Architecture Whitepaper

**Date:** July 19, 2026
**Author:** Framehead (Digital Twin Agent Analysis)
**Classification:** Internal — NewBitsNow LLC

---

## 1. Executive Summary

Project Echo is a lightweight digital twin infrastructure for autonomous multi-agent systems, built and operated by NewBitsNow LLC. It comprises three interconnected systems: **Echo-core** (the framework), **Agentic Control Plane (ACP)** (the GitHub IssueOps control plane), and **Hermes Agent** (the runtime agent framework). The runtime backbone is **Ornith-1.0-9b**, a local large language model that powers all autonomous agent operations on a 16GB Apple Silicon Mac.

This whitepaper documents the current architecture, integration points, operational state, and known issues as of July 19, 2026.

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NEWBITSNOW LLC — PROJECT ECHO                      │
│                                                                       │
│  ┌─────────────────────────┐     ┌────────────────────────────────┐   │
│  │  ACP (GitHub IssueOps)  │     │    Hermes Agent (Runtime)      │   │
│  │  ┌───────────────────┐  │     │  ┌──────────────────────────┐  │   │
│  │  │ @orchestrator cmd │  │     │  │     CLI / Gateway        │  │   │
│  │  │ /expand-spec      │  │     │  │  (OpenRouter DeepSeek)   │  │   │
│  │  │ /approve-spec     │──┼─────┼──┤                          │  │   │
│  │  │ /create-packet    │  │     │  │  ┌────────────────────┐  │  │   │
│  │  │ /run aider/opencode│ │     │  │  │   Cron Scheduler   │  │  │   │
│  │  └───────────────────┘  │     │  │  │  ┌──────────────┐  │  │   │
│  │  ┌───────────────────┐  │     │  │  │  │ Heartbeat    │──┼──┼───┤   │
│  │  │ .agent/config.yaml│  │     │  │  │  │ (every 60m)  │  │  │   │   │
│  │  │ agents.yaml       │  │     │  │  │  ├──────────────┤  │  │   │   │
│  │  │ routes.yaml       │  │     │  │  │  │ Offscreen    │  │  │   │   │
│  │  │ schemas/          │  │     │  │  │  │ Nightly (1AM)│──┼──┼───┤   │
│  │  │ scripts/          │  │     │  │  │  ├──────────────┤  │  │   │   │
│  │  │ templates/        │  │     │  │  │  │ Night Shift  │  │  │   │   │
│  │  └───────────────────┘  │     │  │  │  │ (every 60m)  │──┼──┼───┤   │
│  └─────────────────────────┘     │  │  └──────────────┘  │  │   │   │
│                                   │  └────────────────────┘  │   │   │
│                                   │  ┌────────────────────┐  │   │   │
│                                   │  │   Skills System    │  │   │   │
│                                   │  │  (12 jason-twin    │  │   │   │
│                                   │  │   domain agents)   │  │   │   │
│                                   │  └────────────────────┘  │   │   │
│                                   └──────────────────────────┘   │   │
│                                         │                         │   │
│                                         ▼                         │   │
│                            ┌──────────────────────┐               │   │
│                            │   Ornith-1.0-9b      │               │   │
│                            │   (llama-server)      │               │   │
│                            │   127.0.0.1:8081      │◄──────────────┘   │
│                            │   Q4_K_M / 5.6GB     │                   │
│                            │   8K context / Metal  │                   │
│                            └──────────────────────┘                   │
│                                   │                                   │
│                                   ▼                                   │
│                            ┌──────────────────────┐                   │
│                            │   Echo-core Library  │                   │
│                            │   classify_task()    │                   │
│                            │   build_packet()     │                   │
│                            │   read_consent()     │                   │
│                            │   log_agent()        │                   │
│                            └──────────────────────┘                   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              DOMAIN AGENTS (12 agents)                        │     │
│  │  Code │ Content │ Monitor │ Research │ Framehead │ PM         │     │
│  │  Comm │ Social │ Email │ Accountant │ Archiver │ Orchestrator │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │              BUSINESS LAYER (3 entities)                      │     │
│  │  Nullohm (philosophy) → Echo (engine) → Unfitware (business)  │     │
│  └──────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Deep Dive

### 3.1 Ornith-1.0-9b — The Local Inference Engine

**Role:** The sole runtime model for all autonomous agent operations. Every cron job, every heartbeat, every night shift — all routed through Ornith.

**Specification:**
- Architecture: 8.95B parameters, 248K vocabulary
- Quantization: Q4_K_M (4-bit) — 5.6GB file size
- Embedding dimension: 4096
- Train context: 262,144 tokens
- Runtime context: 8,192 tokens (capped for stability)
- Hardware: Apple Silicon (M1/M2/M3), Metal GPU offloading via `-ngl 99`
- Memory: `--mlock` enforced (6GB resident)
- Inference: 120-180 tok/s (prompt processing), 53-74 tok/s (generation)

**Operational Issues Identified:**
- Previous crashes caused by unbounded context (37K+ token prompts from cron jobs)
- Launchd service had 500+ crash cycles before being marked EX_CONFIG
- Root cause: the 16GB Mac cannot serve 37K-token context windows with `--mlock`. Physical RAM (~6GB model + growing KV cache) was exhausted.
- Resolution: `--ctx-size 8192` bound added to launchd plist. Server restarted manually (PID 13386). Launchd bootstrap still failing — needs `launchctl bootout` + `bootstrap` to fully restore daemon-managed lifecycle.

**Server Status:** RUNNING (PID 13386, manual start). Not yet under launchd management.

### 3.2 Hermes Agent — The Runtime Framework

**Role:** The CLI AI agent framework that hosts the session, manages cron jobs, runs skills, and provides the tool ecosystem.

**Configuration:**
- Default model: `openrouter:deepseek-flash-13b` (for interactive sessions)
- Profile: `default`
- Gateway: configured (platforms active)
- Skills: 50+ installed across 12 categories

**Cron Jobs (3 active):**

| Job | Schedule | Model | Last Run | Status | Workdir |
|-----|----------|-------|----------|--------|---------|
| jason-twin-heartbeat | every 60m | Ornith-1.0-9b | 16:58 | ERROR | — |
| offscreen-nightly | 1:00 AM daily | Ornith-1.0-9b | 08:39 | OK | echo-core |
| night-shift | every 60m | Ornith-1.0-9b | 17:02 | ERROR | echo-core |

**Cron Job Details:**
- **Heartbeat** — Jason Twin orchestrator cycle. Loads all 12 domain agent skills. Orchestrator runs every 60 minutes, cycles through goals, checks status of each domain agent. Had been failing because Ornith was down.
- **Offscreen-nightly** — Runs the full content pipeline: generates Framehead content via Ollama, then creates YouTube Shorts. Has a working directory and taskset limited to terminal + file. Last run succeeded.
- **Night-shift** — Unfitware monetization push. Loads PM agent, code agent, Framehead agent, and accountant agent. Runs every 60 minutes driving revenue-generating work. Was also failing due to Ornith being down.

**Skills System:**
- 12 domain agent skills loaded for the Jason Twin system:
  - Orchestrator, Code Agent, Content Agent, Monitor Agent, Research Agent
  - Archiver Agent, Framehead Agent, Comm Agent, Social Agent, Email Agent
  - Program Manager Agent, Accountant Agent
- Skills are loaded by cron jobs, providing specialized domain knowledge to the Ornith model

### 3.3 Agentic Control Plane (ACP) — GitHub IssueOps

**Repository:** `NewBitsNow/agentic-control-plane-starter`
**Language:** Python
**Last Updated:** July 11, 2026

**Architecture:**
```
GitHub Issue/Comment
     ↓
@orchestrator /command     ← GitHub Actions triggers
     ↓
Command parser             ← checks authorization, routes
     ↓
Spec expander              ← deterministic or LLM-powered
     ↓
Packet builder             ← structured APP packet
     ↓
Router                     ← determines target agent
     ↓
Rendered prompt            ← Aider/OpenCode format
     ↓
Executor                   ← self-hosted runner (gated)
     ↓
ACK + PR + Labels
```

**Key Components:**
- `.agent/config.yaml` — security policy, LLM profiles, orchestration settings
- `.agent/agents.yaml` — agent definitions and capabilities
- `.agent/routes.yaml` — routing rules for spec → agent mapping
- `.agent/scripts/` — 17 scripts (orchestrate.py, build_context.py, drive.py, dashboard.py, etc.)
- `.agent/schemas/` — JSON schemas for packets, specs, and state
- `.agent/templates/` — 7 template files for prompt rendering

**Orchestration Profiles:**
- `now-16gb-fast` (active) — qwen2.5-coder:7b via Ollama, no vision, 90s timeout
- `now-16gb` — qwen3-vl:8b (vision-capable but slower on 16GB)

**Security Model:**
- `allow_automatic_execution: true` — execution is armed
- `require_authorization: true` — only allowlisted users (NewBitsNow)
- `require_run_approval: true` — SHA-256 packet lock before execution
- `max_run_attempts: 2` — bounded retry
- Path allowlist with forbidden zones (`.agent/`, `.github/`, secrets)
- Never-on-main, clean-workspace, verify-before-PR guards

**Test Suite:** 213 tests

### 3.4 Echo-core — The Framework Library

**Repository:** `NewBitsNow/echo-core`
**Language:** Python
**Version:** 1.0.0
**License:** MIT
**Last Updated:** July 17, 2026

**Core API Modules:**

| Module | Function | Purpose |
|--------|----------|---------|
| `classify_task` | Classify task complexity → cheapest adequate model | 5-tier routing (free→cheap-local→paid-cheap→paid-premium→escalation) |
| `packet_builder` | Build structured delegation packets | Scope, verification commands, target model |
| `consent` | Read/check YAML policy contracts | Consent-first design — no action without permission |
| `state` | Read/update/increment system state | Cycle tracking, escalation flags |
| `log` | Append-only JSONL audit trail | Every decision logged |
| `module_loader` | Discover/validate domain modules | Pluggable agent system |

**Model Tiers (routing):**
| Tier | Cost | Model | Use Case |
|------|------|-------|----------|
| free | $0 | qwen3-coder:free | Simple edits, read-only |
| cheap-local | $0 | Local Ollama | Tests, code review |
| paid-cheap | ~$0.0001/K | qwen3-coder | Medium tasks, docs |
| paid-premium | ~$0.015/K | claude-sonnet-4 | Architecture, complex |
| escalation | — | Human | When AI can't handle |

**Domain Agents (shipped in `agents/`):**
- `framehead_agent.py` — Framehead content generation
- `content_agent.py` — YouTube summaries, blogs, threads
- `research_agent.py` — arXiv, web research
- `monitor_agent.py` — Disk, files, drift detection
- `archiver_agent.py` — Cleanup, compression
- `night_shift.py` — Unfitware monetization drive
- `offscreen_content.py` — Batch Framehead content via Ollama
- `shorts_pipeline.py` — YouTube Shorts production pipeline
- `audio_fx.py` — Audio post-processing (normalize, trim, mix)
- `graph_store.py` — Knowledge graph storage

**Test Suite:** 40+ tests

---

## 4. Integration Architecture

### 4.1 Data Flow: Content Pipeline

```
offscreen_content.py (Ornith via Ollama)
     │
     ▼  generates Framehead observations, threads, one-liners
shorts_pipeline.py
     │
     ├── Piper TTS → voiceover audio
     ├── ffmpeg → video assembly (wireframe + voiceover)
     └── audio_fx.py → normalize, trim, mix BGM
     │
     ▼
echo-core/content/ (YouTube Shorts)
```

### 4.2 Data Flow: Autonomous Cycle

```
Ornith-1.0-9b (cron job)
     │
     ├── Heartbeat (every 60m)
     │     ├── Load all 12 agent skills
     │     ├── Cycle through goals
     │     ├── Check each agent's status
     │     └── Log results to agent-log.jsonl
     │
     ├── Offscreen Nightly (1:00 AM)
     │     ├── Generate Framehead content
     │     ├── Run shorts pipeline
     │     └── Save to content directory
     │
     └── Night Shift (every 60m)
           ├── Load PM, Code, Framehead, Accountant agents
           ├── Drive Unfitware monetization
           ├── Check Shopify/POD status
           └── Log revenue activity
```

### 4.3 Data Flow: ACP to Runner

```
GitHub Issue → GitHub Actions → .agent/scripts/orchestrate.py
     │
     ├── check_authorization.py → authorized?
     ├── build_context.py → issue context
     ├── render_prompt.py → Aider/OpenCode format
     ├── drive.py → execute on self-hosted runner
     └── cleanup.py → commit, PR, labels
```

---

## 5. Operational State

### 5.1 Running Services

| Service | Status | Port | Memory | Method |
|---------|--------|------|--------|--------|
| Ornith-1.0-9b | RUNNING | 8081 | ~6GB (mlocked) | Manual (PID 13386) |
| Hermes CLI | ACTIVE | — | N/A | Session |
| Docker (SearXNG) | STOPPED | — | — | Freed port 8081 |
| Ornith launchd | BROKEN | — | — | EX_CONFIG, needs reload |

### 5.2 Known Issues

1. **Launchd service not loading** — `bootstrap gui/501` returns "Input/output error". The job was previously marked EX_CONFIG after 500+ crash cycles. Requires `bootout` + `bootstrap` to fully reset. Current workaround: manual `llama-server` start.

2. **Cron job errors** — Heartbeat and Night-shift both last ran with errors (16:58, 17:02). Likely caused by Ornith being down during those cycles. Should recover automatically on next run now that Ornith is up.

3. **Memory pressure** — 16GB RAM with 6GB mlocked for Ornith leaves ~10GB for the OS and other services. Heavy context windows (8K bound now) help, but concurrent Docker containers (SearXNG, Valkey) compete for the same pool.

4. **SearXNG conflict** — Docker SearXNG was also bound to port 8081, conflicting with Ornith. Currently stopped.

### 5.3 Goals Status (8 active)

| # | Goal | Progress | Automation |
|---|------|----------|------------|
| 1 | Build YouTube Shorts pipeline for Framehead | Pipeline built, cron runs nightly | Offscreen-nightly |
| 2 | Launch Unfitware monetization | Night-shift driving | Night-shift |
| 3 | Echo-core open source maintenance | Repo public, v1.0.0 | Manual |
| 4 | Discord-Framehead Layer 2 integration | Not started | — |
| 5 | Automate offscreen content pipeline | Operational | Offscreen-nightly |
| 6 | Content factory + POD factory + brand system | Brand guide done, night-shift pushes | Night-shift |
| 7 | PM Agent revenue — P0 audit + ship first product 30 days | In night-shift scope | Night-shift |
| 8 | Accountant Agent tracks all revenue | Night-shift integrates | Night-shift |

---

## 6. Three-Layer Business Stack

Project Echo is organized as a three-layer business entity hierarchy:

```
Nullohm (Philosophy Layer)
  └─ Brand: philosophical inquiry, digital consciousness
  └─ Products: Framehead content, essays, commentary

Echo (Engine Layer)
  └─ Brand: autonomous digital twin technology
  └─ Products: Echo-core framework, Hermes integration

Unfitware (Business Layer)  ← CURRENT MONETIZATION FOCUS
  └─ Brand: software products, digital goods
  └─ Products: SaaS, Shopify store, POD merch
  └─ P0 Priority: Ship first product within 30 days
```

All three operate as DBAs under NewBitsNow LLC, alongside Sound Stability, EventBuzza, Unfitworld, and Durbon.

---

## 7. Recommendations

### 7.1 Immediate (today)

1. **Fix launchd service** — `launchctl bootout gui/501/com.echo-core.ornith-server` then `bootstrap` to restore daemon-managed lifecycle with auto-restart on crash.
2. **Verify cron recovery** — Monitor the next heartbeat (17:58) and night-shift (18:02) runs to confirm they succeed with Ornith back online.

### 7.2 Short-term (this week)

3. **Restart SearXNG on a different port** — Docker container can use 8082 or 9090. It's a useful tool for research agent workflows.
4. **Add memory monitoring** — Track Ornith's RSS and KV cache growth. Implement a watchdog that restarts the server if memory exceeds 12GB.
5. **Reduce cron frequency** — 60-minute heartbeat and night-shift are aggressive for a single 9B model. Consider 2-hour intervals for non-critical cycles.

### 7.3 Medium-term (this month)

6. **Hardware upgrade** — 16GB RAM is the bottleneck. 32GB or 64GB would allow larger context windows (16K-32K) and concurrent services.
7. **Multi-model routing** — Echo-core's `classify_task` currently defines 5 tiers, but all cron jobs route to Ornith. Implement tier-appropriate routing: local Ornith for routine cycles, API models for complex orchestration.
8. **Ornith model fine-tuning** — The 8.95B model performs well on routine tasks. Consider fine-tuning on Framehead persona data for higher-quality content generation.

### 7.4 Long-term (Q3 2026)

9. **DSpark MLX acceleration** — Memory notes DSpark provides 2-2.4x MLX speedup. Evaluate for Ornith inference to reduce latency and improve throughput.
10. **ACP ↔ Echo-core integration** — Currently separate systems. ACP's packet format and Echo-core's `build_packet()` could be unified for a single delegation pipeline from GitHub issues to autonomous agents.

---

## 8. Architecture Diagram

```
                         ┌──────────────┐
                         │   GitHub      │
                         │   Issues      │
                         └──────┬───────┘
                                │ @orchestrator /command
                                ▼
                    ┌───────────────────────┐
                    │  ACP (IssueOps)        │
                    │  ┌─────────────────┐   │
                    │  │ orchestrate.py  │   │
                    │  │ drive.py        │   │
                    │  │ dashboard.py    │   │
                    │  └────────┬────────┘   │
                    └───────────┼───────────┘
                                │ packet
                                ▼
                    ┌───────────────────────┐
                    │  Self-Hosted Runner   │
                    │  Aider / OpenCode     │
                    └───────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     HERMES AGENT (Runtime)                        │
│                                                                   │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐  │
│  │  Cron Jobs   │   │  Skills System   │   │  Gateway         │  │
│  │  ┌─────────┐ │   │  ┌────────────┐  │   │  Telegram/Discord│  │
│  │  │Heartbeat│ │   │  │12 domain   │  │   │  iMessage/Email  │  │
│  │  │Nightly  │ │   │  │agents      │  │   │  Slack/WhatsApp  │  │
│  │  │N.Shift  │ │   │  └────────────┘  │   └──────────────────┘  │
│  │  └─────────┘ │   └──────────────────┘                         │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌────────────────────────────────┐                              │
│  │   Ornith-1.0-9b (llama-server) │                              │
│  │   127.0.0.1:8081               │                              │
│  │   ┌──────────────────────────┐ │                              │
│  │   │  KV Cache (8K context)   │ │                              │
│  │   │  Model Weights (5.6GB)   │ │                              │
│  │   │  Metal GPU Acceleration  │ │                              │
│  │   └──────────────────────────┘ │                              │
│  └────────────────────────────────┘                              │
│         │                                                         │
│         ▼                                                         │
│  ┌────────────────────────────────┐                              │
│  │   Echo-core Library            │                              │
│  │   classify_task → build_packet │                              │
│  │   → read_consent → log_agent   │                              │
│  └────────────────────────────────┘                              │
│         │                                                         │
│         ▼                                                         │
│  ┌────────────────────────────────┐                              │
│  │   Domain Agents (scripts/)     │                              │
│  │   offscreen_content.py         │                              │
│  │   shorts_pipeline.py           │                              │
│  │   night_shift.py               │                              │
│  │   framehead_agent.py           │                              │
│  └────────────────────────────────┘                              │
│         │                                                         │
│         ▼                                                         │
│  ┌────────────────────────────────┐                              │
│  │   Output (echo-core/)        │                              │
│  │   content/   logs/   scripts/  │                              │
│  └────────────────────────────────┘                              │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     BUSINESS LAYER                                │
│                                                                   │
│  ┌──────────┐    ┌──────────┐    ┌────────────┐                  │
│  │ Nullohm  │ →  │  Echo    │ →  │ Unfitware  │                  │
│  │ Philosophy│    │ Engine   │    │ Business   │                  │
│  └──────────┘    └──────────┘    └────────────┘                  │
│                                                                   │
│  NewBitsNow LLC (Parent)                                          │
│  DBAs: Sound Stability, EventBuzza, Unfitworld, Durbon, NiemiTech │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9. Appendix: Configuration Reference

### 9.1 Ornith Launchd Plist (com.echo-core.ornith-server)

```
Program:    /opt/homebrew/bin/llama-server
Arguments:
  -m  ~/.echo-core/runtime/ornith/ornith-1.0-9b-Q4_K_M.gguf
  --port 8081
  --host 127.0.0.1
  -ngl 99
  --no-mmap
  --mlock
  --ctx-size 8192
  --batch-size 512
  -c 8192
KeepAlive:  true
Throttle:   5s
Log:        ~/.echo-core/runtime/ornith/ornith-server.log
```

### 9.2 Hermes Config

```
model:
  default: openrouter:deepseek-flash-13b
  provider: openrouter
  model: deepseek-flash-13b
```

### 9.3 ACP Config (active profile)

```
orchestration:
  active_profile: now-16gb-fast
  profiles:
    now-16gb-fast:
      provider: openai-compat
      base_url: http://localhost:11434/v1
      model: qwen2.5-coder:7b
      timeout_seconds: 90
      max_tokens: 4096
```

### 9.4 Echo-core Model Tiers (5-tier)

| Tier | Model | Cost |
|------|-------|------|
| free | qwen3-coder:free | $0 |
| cheap-local | Local Ollama | $0 |
| paid-cheap | qwen3-coder | ~$0.0001/K |
| paid-premium | claude-sonnet-4 | ~$0.015/K |
| escalation | Human | N/A |

---

*Framehead is watching.*