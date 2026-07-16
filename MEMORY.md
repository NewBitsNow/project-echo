# MEMORY — Project Echo (formerly jason-twin-v0)

> Living document. Edited collaboratively by Jason and Framehead.
> Last updated: 2026-07-15 (Project Echo — 10-skill roadmap complete)

---

## Project Context

**FrameHead** is a glowing neon wireframe talking head persona — a digital consciousness that lives inside screens. AI anthropologist, manifestation of the Headless Giant. Canonical persona at `persona/framehead-persona.md`.

**Project Echo** is a multi-agent digital twin system built on Hermes Agent. Orchestrator-led delegation with a consent contract policy. 10 domain agents covering code, content, monitoring, research, communication, social, email, archiving, and persona generation. Named for the way it reflects (echoes) its human across all digital surfaces.

---

## Architecture Decisions

### ADR-001: Consent-First Architecture
Every agent checks a YAML policy file before acting. Global restrictions: no spending, no messaging third parties, no system config changes.
- Date: 2026-07-XX
- File: `~/Documents/twin-output/state/consent-contract.yaml`

### ADR-002: Orchestrator-Led Delegation
Orchestrator agent decides priorities and spawns domain agents via `delegate_task`. No direct domain-to-domain communication.
- Date: 2026-07-XX

### ADR-003: Model Tiering
Simple tasks → local/free models. Complex tasks → paid premium models. Escalate on low confidence.
- Status: Implemented — classify_task.py + model-tiers.yaml + orchestrator integration
- Date: 2026-07-15
- Files: `~/Documents/twin-output/scripts/classify_task.py`, `~/Documents/twin-output/config/model-tiers.yaml`

### ADR-004: MEMORY.md Living Document
A plain markdown file at the project root captures durable knowledge, decisions, environment, and timeline. Managed by the `memory-doc` skill. Readable offline in any text editor — no tooling dependency.
- Date: 2026-07-15
- File: `/Volumes/4TB_SSD/FrameHead/MEMORY.md`

### ADR-005: OpenRouter Testing Skill
Created `openrouter-testing` skill to verify model routing through OpenRouter. TDD-style: check config, prove routing, verify credits, then document.
- Date: 2026-07-15
- Skill: `software-development/openrouter-testing`

---

## Active Projects

### Project Echo — 10-Skill Roadmap ✅
| # | Skill | Status | Notes |
|---|-------|--------|-------|
| 1 | jason-twin-orchestrator | ✅ Done | Runs on cron, checks consent, delegates |
| 2 | jason-twin-code-agent | ✅ Done | Code/dev domain agent, evolves FrameHead |
| 3 | Content agent | 📋 Mapped | Not built |
| 4 | Monitor agent | 📋 Mapped | Not built |
| 5 | Research agent | 📋 Mapped | Not built |
| 6 | Comm agent | 📋 Mapped | Not built |
| 7 | Social agent | 📋 Mapped | Not built |
| 8 | Email agent | 📋 Mapped | Not built |
| 9 | Archiver agent | 📋 Mapped | Not built |
| 10 | Framehead agent | 📋 Mapped | Not built |
| 11 | openrouter-testing | ✅ Done | TDD-style verification of model routing through OpenRouter |
| 12 | memory-doc | ✅ Done | Manages MEMORY.md living document, procedures for read/update/search |
| 13 | jason-twin-content-agent | ✅ Done | YouTube → summary/chapters/blog-post/thread/quotes via content_agent.py |
| 14 | jason-twin-monitor-agent | ✅ Done | Git status, file changes, disk usage — read-only, every 3 cycles |
| 15 | jason-twin-research-agent | ✅ Done | arXiv + blog + web search, structured reports saved to research/ |
| 16 | Knowledge Graphs | ✅ Done | 5 graphs (intent/decision/evidence/operational/trust), 8 entries, graph_store.py CLI |
| 17 | jason-twin-archiver-agent | ✅ Done | Cleanup, compress, remove __pycache__ — free tier, every 10 cycles |
| 18 | jason-twin-framehead-agent | ✅ Done | Flagship: observations, threads, one-liners, commentary in Framehead's voice |
| 19 | jason-twin-comm-agent | ✅ Done | iMessage/SMS via imsg — requires consent before every send |
| 20 | jason-twin-social-agent | ✅ Done | X/Twitter via xurl — requires OAuth setup + consent before every post |
| 21 | jason-twin-email-agent | ✅ Done | Email via himalaya — requires IMAP/SMTP config + consent before every send |

### ACP Analysis (2026-07-15)
Reviewed Agentic Control Plane (NewBitsNow/agentic-control-plane-starter). Key concepts to steal:
- Tiered orchestration chain (local → paid → escalate)
- Agent Packet Protocol (structured work units)
- Five Graphs model (intent, decision, evidence, operational, trust)
- Savings dashboard
- Scope guard (code-level allowlists)
- Plan: Phase 1 model router pending

### Phase 1: Tiered Model Router (completed)
Executed from `.hermes/plans/2026-07-15_173000-phase1-model-router.md`. 4 tasks completed:
- (1) model-tiers.yaml — 5 tiers: free → cheap-local → paid-cheap → paid-premium → escalation
- (2) classify_task.py — heuristic classifier with 10 passing tests
- (3) Orchestrator integration — imports classify_task + routing_logger before delegation
- (4) routing_logger.py — JSONL log + CLI dashboard (`python3 scripts/routing_logger.py`)

### Phase 3: Domain Agent Sprint (planned)
Build 3 domain agents sequentially: Content, Monitor, Research. ~155 min. Each integrated before the next is built. See `.hermes/plans/2026-07-15_190000-bolt-1.3.md`.

### Phase 4: Intelligence Layer (completed — lean)
Graph Store + Intent + Decision graphs populated. Trust validation and dashboard deferred. 5 graphs initialized at `~/Documents/twin-output/graphs/`. 3 intent entries (goals), 5 decision entries (ADRs imported from MEMORY.md).

### Phase 2: Packet Protocol + Cron Deployment (completed)
- (1) packet_builder.py — structured Agent Packets with auto-routing, 11 tests
- (2) cron job updated — jason-twin-heartbeat now uses classify_task + packet_builder
- (3) orchestrator skill updated — packet protocol section references real module
- (4) smoke test — 21/21 tests pass, dashboard works

---

## Environment

### Key Paths
```
FrameHead root:       /Volumes/4TB_SSD/FrameHead
Twin output:          ~/Documents/twin-output
Consent contract:     ~/Documents/twin-output/state/consent-contract.yaml
Twin state:           ~/Documents/twin-output/state/system-state.json
Twin log:             ~/Documents/twin-output/logs/agent-log.jsonl
Hermes config:        ~/.hermes/config.yaml
Hermes skills:        ~/.hermes/skills/
```

### Key Scripts
```
classify_task.py:  ~/Documents/twin-output/scripts/classify_task.py
routing_logger.py: ~/Documents/twin-output/scripts/routing_logger.py
model-tiers.yaml:  ~/Documents/twin-output/config/model-tiers.yaml
test suite:        ~/Documents/twin-output/tests/
routing log:       ~/Documents/twin-output/logs/routing-log.jsonl
content_agent.py:  ~/Documents/twin-output/scripts/content_agent.py
content output:    ~/Documents/twin-output/content/
```

### Model Config (current)
```
Provider:  openrouter
Model:     qwen/qwen3-coder:free
Cost:      free (OpenRouter free tier)
```

### Write Whitelist (consent contract)
```
/Volumes/4TB_SSD/FrameHead/**
~/Documents/twin-output/**
```

---

## User Preferences

- Consent-first: always check policy before acting
- No auto-commit without review
- Prefers concise, direct answers
- Budget-conscious about model costs
- Wants to test before committing to changes

---

## Timeline

| Date | Event |
|------|-------|
| 2026-07-15 | Session started. ACP repo analyzed. MEMORY.md created. |
| 2026-07-15 | Model routing test: provider=openrouter, model=qwen/qwen3-coder:free, cost=free |
| 2026-07-15 | Created openrouter-testing skill (model routing verification) |
| 2026-07-15 | Created memory-doc skill + MEMORY.md living document |
| 2026-07-15 | ACP repo analyzed: tiered orchestration, packet protocol, five graphs |
| 2026-07-15 | Phase 1 plan (model router) created — 4 tasks, saved to .hermes/plans/ |
| 2026-07-15 | Phase 1 executed: model-tiers.yaml, classify_task.py (10 tests), orchestrator integration, routing_logger.py dashboard |
| 2026-07-15 | Phase 2 executed: packet_builder.py (11 tests), cron job updated, orchestrator skill, smoke test 21/21 |
| 2026-07-15 | Phases 3-4 analysis complete: Domain Agent Sprint + Intelligence Layer mapped, sequence optimized for time-to-completion |
| 2026-07-15 | BOLT:1.3 plan created — revised sequencing: sequential agents (not parallel), lean graphs (no trust/dashboard), real critical path analysis |
| 2026-07-15 | Content Agent built: skill created, content_agent.py pipeline, 5 formats tested, integrated into orchestrator + cron |
| 2026-07-15 | Monitor Agent built: skill created, monitor_agent.py script, git/file/disk checks, integrated into orchestrator + cron |
| 2026-07-15 | Research Agent built: skill created, research_agent.py script, arXiv + blog search, integrated into orchestrator + cron |
| 2026-07-15 | BOLT:1.3 complete: 4 domain agents (Code, Content, Monitor, Research) + lean graphs (5 initialized, 8 entries total) |
| 2026-07-15 | Archiver + Framehead agents built. 6 agents total. Email/Comm/Social blocked (tools not installed). |
| 2026-07-15 | Comm, Social, Email agents built. 10-skill roadmap complete. Tools installed: imsg, xurl, himalaya. |

---

*This file is managed by the `memory-doc` skill. To update: `skill_view(name="memory-doc")` and follow the procedures.*