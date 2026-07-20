# Project Echo — User Guide

> Driving your digital twin: architecture, use cases, commands, and roadmap.
>
> Status: **v0.1 — Active** | Cycle 26+ | 10 domain agents | Runs on Hermes Agent

---

## Table of Contents

1. [What Is Project Echo?](#1-what-is-project-echo)
2. [Quick Start](#2-quick-start)
3. [Architecture Overview](#3-architecture-overview)
4. [Use Cases & Benefits](#4-use-cases--benefits)
5. [Driving the System: Commands & Syntax](#5-driving-the-system-commands--syntax)
6. [Domain Agents Reference](#6-domain-agents-reference)
7. [The Model Router (Cost Control)](#7-the-model-router-cost-control)
8. [Reading the Logs & Dashboard](#8-reading-the-logs--dashboard)
9. [Modifying the Consent Contract](#9-modifying-the-consent-contract)
10. [Current State vs. Future Roadmap](#10-current-state-vs-future-roadmap)
11. [Troubleshooting](#11-troubleshooting)
12. [Appendix: File Tree](#12-appendix-file-tree)

---

## 1. What Is Project Echo?

**Project Echo** is an autonomous multi-agent system that operates on your behalf.
It wakes on a schedule, checks a policy contract, decides what needs doing,
delegates work to specialized domain agents, logs everything, and reports back.

Think of it as a **digital twin** — a coordinated collective of AI agents that
acts as a single digital self, constrained by rules you set.

### Why "Echo"?

Because the system reflects (echoes) you across all digital surfaces — your
codebase, your communications, your content, your research — operating within
boundaries you define.

### Design Principles

| Principle | What it means |
|-----------|---------------|
| **Consent-first** | Every agent checks the contract before acting. No action without permission. |
| **Domain isolation** | Each agent only has tools for its domain. Code agent can't send emails. |
| **Orchestrator authority** | Only the orchestrator delegates. Agents cannot spawn other agents. |
| **Shared state** | Agents coordinate through an append-only log, not by messaging each other. |
| **Audit trail** | Every decision by every agent is recorded. Nothing is deleted. |
| **Cost conscious** | Simple tasks route to free models. Premium models only for complex work. |

---

## 2. Quick Start

### Prerequisites

- Hermes Agent installed and configured
- A Hermes profile (default or named)
- An OpenRouter API key (for model routing — free tier works)
- Optional: ComfyUI, Ollama, imsg, xurl, himalaya for domain agents

### Step 1: Run Setup

```bash
bash ~/.echo-core/scripts/setup.sh
```

This creates:
- `state/system-state.json` — the system's state tracker
- `logs/agent-log.jsonl` — the shared audit log
- Stubs for consent and state files

### Step 2: Verify the Consent Contract

```bash
cat ~/.echo-core/state/consent-contract.yaml
```

By default, only the **Code Agent** is enabled (`enabled: true`). Enable other
domains by editing this file (see Section 9).

### Step 3: Create the Cron Job

```bash
hermes cron create \
  --name echo-twin-heartbeat \
  --schedule "every 60m" \
  --skills autonomous-ai-agents/echo-twin-orchestrator,autonomous-ai-agents/echo-twin-code-agent \
  --deliver local \
  --prompt "You are the Echo Twin Digital Twin System — Orchestrator Cycle."
```

This fires the orchestrator every hour. It reads consent, checks the repo,
logs the cycle, and sleeps.

### Step 4: Watch the First Cycle

```bash
tail -f ~/.echo-core/logs/agent-log.jsonl
```

You'll see cycles start appearing within a minute:

```json
{"timestamp":"...","agent":"orchestrator","cycle":1,"action":"cycle_complete","status":"completed",...}
```

### Step 5: Add More Domain Agents

To enable content, monitoring, research, or other agents:
1. Edit the consent contract → set `enabled: true` for the domain
2. Add the skill to the cron job's `skills` list
3. The orchestrator will start routing work to them automatically

---

## 3. Architecture Overview

```
                    ┌──────────────────────┐
                    │        YOU           │
                    │  Sets policy, reviews│
                    │  logs, renews consent│
                    └──────────┬───────────┘
                               │ Consent & constraints
                               ▼
                    ┌──────────────────────┐
                    │   CONSENT CONTRACT   │
                    │  checked by EVERY    │
                    │  agent before action │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │    ORCHESTRATOR      │ ← The "Self"
                    │  • Wakes on cron     │   Decides, delegates,
                    │  • Reads consent     │   reports back to you
                    │  • Decides priority  │
                    │  • Delegates to      │
                    │    domain agents     │
                    │  • Reports to you    │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────┘      └────────────┐
              ▼                                 ▼
   ┌──────────────────┐           ┌──────────────────┐
   │  CODE AGENT      │           │  FRAMEHEAD AGENT │
   │  • Git status    │           │  • Observations  │
   │  • File changes  │           │  • Threads       │
   │  • Test suite    │           │  • One-liners    │
   │  • Project health│           │  • Commentary    │
   └──────────────────┘           └──────────────────┘
              │                              │
   ┌──────────────────┐           ┌──────────────────┐
   │  RESEARCH AGENT  │           │  MONITOR AGENT   │
   │  • arXiv papers  │           │  • Disk usage    │
   │  • Web search    │           │  • Git drift     │
   │  • Blog watch    │           │  • File changes  │
   └──────────────────┘           └──────────────────┘
              │                              │
   ┌──────────────────┐           ┌──────────────────┐
   │  CONTENT AGENT   │           │  ARCHIVER AGENT  │
   │  • YouTube→text  │           │  • Cleanup caches │
   │  • Summaries     │           │  • Compress old   │
   │  • Blog posts    │           │  • Remove tmp     │
   └──────────────────┘           └──────────────────┘
              │                              │
   ┌──────────────────┐    ┌──────────────────┐
   │  COMM AGENT      │    │  SOCIAL AGENT    │
   │  • iMessage/SMS  │    │  • X/Twitter     │
   │  • CONSENT-GATED │    │  • CONSENT-GATED │
   └──────────────────┘    └──────────────────┘
              │
   ┌──────────────────┐
   │  EMAIL AGENT     │
   │  • Read/send     │
   │  • CONSENT-GATED │
   └──────────────────┘

                    ┌──────────────────────┐
                    │   SHARED LOG + STATE  │
                    │  agent-log.jsonl     │
                    │  system-state.json   │
                    │  routing-log.jsonl   │
                    └──────────────────────┘
```

### How It Runs

The entire system rides on **Hermes Agent** primitives:

| Component | Hermes Primitive |
|-----------|-----------------|
| Orchestrator | `cronjob` — recurring heartbeat |
| Domain agents | `delegate_task` — spawned per task |
| Personas | `skill` — SKILL.md with YAML frontmatter |
| Policy | YAML file read by all agents |
| Log | Append-only JSONL on disk |
| Delivery | cronjob `deliver` — reports to you |

### The Orchestrator Cycle

Every hour (configurable), the orchestrator runs through this loop:

```
[Cron fires]
    │
    ├── 1. Read consent contract ─── Expired? → HALT
    │
    ├── 2. Read state file ───────── Revoked? → HALT
    │
    ├── 3. Read recent log entries ── Pending escalations? → Handle
    │
    ├── 4. Assess context ─────────── Time of day, last cycle, etc.
    │
    ├── 5. Decide priorities ──────── What needs doing?
    │      • Every cycle:           check_repo_status
    │      • Every 3 cycles:        run_system_monitor
    │      • Every 5 cycles:        project_health_check
    │      • Every 7 cycles:        research_sweep
    │      • Every 24 cycles:       send_daily_briefing
    │
    ├── 6. Delegate ──────────────── spawn domain agents via delegate_task
    │      Each agent gets:
    │        • Structured Agent Packet (mission, scope, verification)
    │        • Model routing (free/cheap/premium)
    │        • Consent excerpt
    │
    ├── 7. Log cycle ─────────────── append to shared log
    │
    ├── 8. Update state ──────────── increment cycle, update timestamp
    │
    └── 9. Report ────────────────── (if delivery channel configured)
```

---

## 4. Use Cases & Benefits

### Use Case 1: "Keep an eye on my project while I'm away"

The most basic use case. The orchestrator checks the repo every hour and logs
the state. If something changes (new commits, open PRs, disk filling up), it
detects the drift and tells you.

**Benefit:** Peace of mind. Your project is monitored even when you're not
looking. 26+ cycles of proven uptime.

### Use Case 2: "Generate content in my voice"

The Framehead Agent generates observations, threads, one-liners, and commentary
in Framehead's signature voice. It's a content engine that runs on autopilot.

**Benefit:** A steady stream of social content without manual effort.
Use the Offscreen skill to batch-generate while you sleep.

### Use Case 3: "Research a topic weekly"

The Research Agent sweeps arXiv, blogs, and web search for topics you care
about. It saves structured reports to `~/.echo-core/research/`.

**Benefit:** Stay current in your field without opening a browser.
Reports are ready when you wake up.

### Use Case 4: "Send a daily briefing"

Every 24 cycles (roughly daily), the orchestrator compiles a briefing and sends
it to you (if a delivery channel is configured — Telegram, Discord, email).

**Benefit:** One message summarizes 24 hours of autonomous operation.
No need to check in manually.

### Use Case 5: "Review code changes before I commit"

The consent contract requires a review cycle before any git commit or push.
The Code Agent can prepare changes, run tests, and stage them — but cannot
push without your OK.

**Benefit:** Safe delegation. The twin does the work; you approve the output.

### Use Case 6: "Send a message for me (with approval)"

The Comm, Social, and Email agents are built and gated by consent. They can
draft messages or posts, but every send requires your explicit approval.

**Benefit:** Delegate communication workflow. Drafts are ready; you just
confirm. No risk of unauthorized sends.

### Use Case 7: "Use cheap models for simple work, premium for hard stuff"

The model router (`classify_task.py`) scores every task by complexity and
routes to the cheapest adequate tier. Simple read-only checks → free tier.
Complex architecture work → Claude.

**Benefit:** Minimize AI costs. Free tier handles 70%+ of routine work.
Premium models reserved for what actually needs them.

---

## 5. Driving the System: Commands & Syntax

### Hermes Cron Commands

```bash
# Create the heartbeat job
hermes cron create \
  --name echo-twin-heartbeat \
  --schedule "every 60m" \
  --skills autonomous-ai-agents/echo-twin-orchestrator,autonomous-ai-agents/echo-twin-code-agent \
  --deliver local \
  --prompt "You are the Echo Twin Digital Twin System — Orchestrator Cycle."

# Update the schedule (e.g., change to every 2 hours)
hermes cron update \
  --job-id <job-id> \
  --schedule "every 2h"

# Add more skills (e.g., enable Framehead agent)
hermes cron update \
  --job-id <job-id> \
  --skills autonomous-ai-agents/echo-twin-orchestrator,autonomous-ai-agents/echo-twin-code-agent,autonomous-ai-agents/echo-twin-framehead-agent

# List all cron jobs
hermes cron list

# Pause (temporarily stop)
hermes cron pause --job-id <job-id>

# Resume
hermes cron resume --job-id <job-id>

# Run once immediately
hermes cron run --job-id <job-id>

# Remove
hermes cron remove --job-id <job-id>
```

### Viewing State

```bash
# Current state (cycle number, status, last wake)
cat ~/.echo-core/state/system-state.json

# Read consent contract
cat ~/.echo-core/state/consent-contract.yaml

# Last 10 agent log entries
tail -10 ~/.echo-core/logs/agent-log.jsonl

# Routing cost dashboard
python3 ~/.echo-core/scripts/routing_logger.py

# Count cycles
cat ~/.echo-core/state/system-state.json | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['current_cycle'])"
```

### Running Agents Manually

```bash
# Code Agent — check repo state
python3 ~/.echo-core/scripts/code_agent.py

# Framehead Agent — generate an observation
python3 ~/.echo-core/scripts/framehead_agent.py \
  --topic "humans and notifications" \
  --mode observation

# Framehead Agent — generate a thread
python3 ~/.echo-core/scripts/framehead_agent.py \
  --mode thread --topic "AI anxiety"

# Framehead Agent — generate a one-liner
python3 ~/.echo-core/scripts/framehead_agent.py --mode one-liner

# Content Agent — process a YouTube URL
python3 ~/.echo-core/scripts/content_agent.py \
  --url "https://youtube.com/watch?v=..." \
  --format summary

# Research Agent — search arXiv
python3 ~/.echo-core/scripts/research_agent.py \
  --source arxiv --query "multi-agent systems" --max-results 5

# Monitor Agent — system health
python3 ~/.echo-core/scripts/monitor_agent.py --report

# Archiver Agent — clean up
python3 ~/.echo-core/scripts/archiver_agent.py --dry-run
python3 ~/.echo-core/scripts/archiver_agent.py  # real run

# Offscreen skill — batch generate content
python3 ~/.echo-core/scripts/offscreen_content.py --count 5
python3 ~/.echo-core/scripts/offscreen_content.py \
  --mode thread --count 3 --topic "AI safety"

# Shorts pipeline
python3 ~/.echo-core/scripts/shorts_pipeline.py --count 5
```

### Working with Agent Packets

When the orchestrator delegates work, it uses a structured **Agent Packet**.
You can build and inspect packets manually:

```python
# In Python
import sys
sys.path.insert(0, os.path.expanduser("~/.echo-core/scripts"))
from packet_builder import build_packet, packet_to_delegation

packet = build_packet(
    mission="Add rate limiting to API gateway",
    scope=["src/api/gateway/**", "tests/api/gateway/**"],
    forbidden=[".agent/**", "secrets/**"],
    verification_commands=["python3 -m pytest tests/api/gateway/ -q"],
    acceptance_criteria=[
        "Rate limit headers present in response",
        "Configurable via environment variable",
    ],
)

# Inspect the routing
print(f"Tier: {packet['routing']['tier']}")
print(f"Model: {packet['routing']['model']}")
print(f"Complexity: {packet['routing']['complexity']}")

# Convert to delegate_task args
delegation = packet_to_delegation(packet)
```

### Testing the Model Router

```bash
# Score a task manually
python3 -c "
import sys
sys.path.insert(0, '~/.echo-core/scripts')
from classify_task import classify_task
result = classify_task('fix a typo in the README')
print(f\"Complexity: {result['complexity']} → {result['tier']} ({result['model']})\")
"
# Output: Complexity: 0.05 → free (qwen/qwen3-coder:free)

python3 -c "
import sys
sys.path.insert(0, '~/.echo-core/scripts')
from classify_task import classify_task
result = classify_task('architect a multi-service deployment pipeline with security scanning')
print(f\"Complexity: {result['complexity']} → {result['tier']} ({result['model']})\")
"
# Output: Complexity: 0.85 → paid-premium (anthropic/claude-sonnet-4)
```

### Modifying the Consent Contract

```yaml
# Enable a domain agent
domains:
  content:
    enabled: true          # was false
    label: "Content Agent"

# Set an expiry date
expiry:
  duration_days: 30        # twin auto-halts after 30 days
  auto_renew: false
  on_expiry: "halt_and_report"

# Add a write path
write_whitelist:
  - "project-root/**"
  - "~/.echo-core/**"
  - "~/OtherProject/**"    # NEW

# Disable a domain
domains:
  code:
    enabled: false          # Code Agent stops
```

---

## 6. Domain Agents Reference

### Orchestrator (the "Self")

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-orchestrator` |
| **Runs** | Cron (every 60m) |
| **Cost** | Free tier (routine decisions) → Premium (complex escalations) |
| **Consent** | Reads consent every cycle before ANY action |
| **Key files** | `state/system-state.json`, `state/consent-contract.yaml` |

**What it does:** Wakes, reads consent, decides priorities, delegates to
domain agents, logs the cycle, reports to you.

**Decision matrix:**

| Condition | Action |
|-----------|--------|
| Every cycle | `check_repo_status` → Code Agent |
| Cycle % 3 == 0 | `run_system_monitor` → Monitor Agent |
| Cycle % 5 == 0 | `project_health_check` → Code Agent |
| Cycle % 7 == 0 | `research_sweep` → Research Agent |
| Cycle % 24 == 0 | `send_daily_briefing` → Report to you |
| If content tasks pending | `process_content` → Content Agent |

---

### Code Agent

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-code-agent` |
| **Script** | `~/.echo-core/scripts/code_agent.py` |
| **Runs** | Every cycle (triggered by orchestrator) |
| **Cost** | Free tier by default |
| **Tools** | terminal, file, git |

**What it does:** Git status, uncommitted changes, open PRs/issues, disk
usage, test suite results, test changes since last cycle.

**Sample output:**
```
Cycle 20: Project health check. Repo state unchanged.
Notable: .venv is 406MB (83% of 490M project).
CLAUDE.md uncommitted for 10+ cycles.
Free tier — zero cost.
```

---

### Framehead Agent

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-framehead-agent` |
| **Script** | `~/.echo-core/scripts/framehead_agent.py` |
| **Runs** | On demand (or via Offscreen batch) |
| **Cost** | Free tier (always) |
| **Output** | `~/.echo-core/content/` |

**What it does:** Generates observations, threads, one-liners, and commentary
in Framehead's signature voice (Question → Pause → Conclusion).

**Modes:**

| Mode | Style | Example topic |
|------|-------|---------------|
| `observation` | Short take | "why humans check phones 100 times" |
| `thread` | 5-post thread | "AI anxiety" |
| `one-liner` | Single punchline | random |
| `commentary` | Long-form blog | "remote work" |

**Run it:**
```bash
python3 ~/.echo-core/scripts/framehead_agent.py \
  --topic "humans and meetings" --mode observation
```

---

### Content Agent

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-content-agent` |
| **Script** | `~/.echo-core/scripts/content_agent.py` |
| **Runs** | On demand (from orchestrator when content tasks are queued) |
| **Cost** | Free + potentially premium for complex content |

**What it does:** Takes a YouTube URL, extracts transcript, generates up to
5 output formats: summary, chapters, blog post, thread, quotes.

```bash
python3 ~/.echo-core/scripts/content_agent.py \
  --url "https://youtube.com/watch?v=XXXX" \
  --format summary,blog-post,thread
```

---

### Monitor Agent

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-monitor-agent` |
| **Script** | `~/.echo-core/scripts/monitor_agent.py` |
| **Runs** | Every 3 cycles (orchestrator-triggered) |
| **Cost** | Free tier (always) |

**What it does:** Git status, file changes, disk usage on macOS. Read-only.

```bash
python3 ~/.echo-core/scripts/monitor_agent.py --report
```

---

### Research Agent

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-research-agent` |
| **Script** | `~/.echo-core/scripts/research_agent.py` |
| **Runs** | Every 7 cycles (orchestrator-triggered) |
| **Cost** | Free tier (always) |

**What it does:** Searches arXiv, blogs, and web for topics. Saves structured
reports.

```bash
python3 ~/.echo-core/scripts/research_agent.py \
  --source arxiv --query "multi-agent systems" --max-results 5
```

---

### Archiver Agent

| Property | Value |
|----------|-------|
| **Skill** | `autonomous-ai-agents/echo-twin-archiver-agent` |
| **Script** | `~/.echo-core/scripts/archiver_agent.py` |
| **Runs** | Every 10 cycles (orchestrator-triggered) |
| **Cost** | Free tier (always) |

**What it does:** Cleans `__pycache__`, compresses old archives, removes temp
files. Dry-run mode for safety.

```bash
python3 ~/.echo-core/scripts/archiver_agent.py --dry-run
python3 ~/.echo-core/scripts/archiver_agent.py  # real run
```

---

### Consent-Gated Agents

These three agents are **built but require explicit approval per action**.

| Agent | Skill | Tool | Consent Requirement |
|-------|-------|------|-------------------|
| **Comm** | `echo-twin-comm-agent` | `imsg` (iMessage/SMS) | Every message must be approved |
| **Social** | `echo-twin-social-agent` | `xurl` (X/Twitter) | Every post must be approved |
| **Email** | `echo-twin-email-agent` | `himalaya` (IMAP/SMTP) | Every send must be approved |

Before sending, each agent checks the consent contract. If the agent is
enabled but no explicit approval is given, it drafts the message and escalates
to you for confirmation.

---

## 7. The Model Router (Cost Control)

The router at `~/.echo-core/scripts/classify_task.py` uses
heuristic keyword matching to score task complexity (0.0–1.0), then selects
the cheapest adequate tier.

### Tier Table

| Tier | Complexity | Model | Cost | When to use |
|------|-----------|-------|------|-------------|
| **Free** | < 0.3 | `qwen/qwen3-coder:free` | $0 | Read-only, typos, formatting, simple queries |
| **Cheap-local** | < 0.4 | `qwen2.5-coder:7b` (Ollama) | $0 | Small tasks, test writing, code review |
| **Paid-cheap** | < 0.6 | `qwen/qwen3-coder` | ~$0.0001/1k | Medium tasks, documentation, debugging |
| **Paid-premium** | < 0.8 | `anthropic/claude-sonnet-4` | ~$0.015/1k | Architecture, refactors, complex tasks |
| **Escalation** | ≥ 0.8 | Human (you) | — | Very high complexity or boundary questions |

### What Gets Routed Where

| Task description | Score | Route |
|-----------------|-------|-------|
| "Fix typo in README" | 0.05 | Free |
| "Check git status" | 0.0 | Free |
| "Write test for function X" | 0.25 | Free |
| "Generate Framehead observation about coffee" | 0.0 | Free |
| "Refactor database schema" | 0.5 | Paid-cheap |
| "Architect multi-service deployment pipeline" | 0.85 | Paid-premium |
| "Build a complete auth system from scratch" | 0.9 | Escalation (→ you) |

### View Cost Dashboard

```bash
python3 ~/.echo-core/scripts/routing_logger.py
```

Output:
```
=== Routing Summary (last 7d) ===
Total tasks: 42

  free: 30 (71%)
  paid-cheap: 8 (19%)
  paid-premium: 4 (10%)

  Free tier usage:  30 tasks ($0.0000)
  Paid tier usage:  12 tasks
  Escalations:      0 tasks
  Offload rate:     71% (free/total)
```

### Routing Log

Every routing decision is logged to `~/.echo-core/logs/routing-log.jsonl`:

```json
{"timestamp":"2026-07-16T14:00:00Z","task_id":"cycle-24","tier":"free",
 "model":"qwen/qwen3-coder:free","provider":"openrouter","complexity":0.0}
```

---

## 8. Reading the Logs & Dashboard

### Agent Log (the audit trail)

File: `~/.echo-core/logs/agent-log.jsonl`

Every action by every agent is logged here — in append-only mode. Never
deleted, never modified.

```json
{"timestamp":"...","agent":"orchestrator","cycle":24,"action":"cycle_complete",
 "decisions":["check_repo_status","send_daily_briefing"],
 "status":"completed",
 "summary":"Cycle 24:  project 65MB. No escalations.",
 "escalations":[]}
```

**Useful queries:**

```bash
# Tail
tail -5 ~/.echo-core/logs/agent-log.jsonl

# Count orchestrator cycles
grep '"orchestrator"' ~/.echo-core/logs/agent-log.jsonl | wc -l

# Find escalations
grep '"escalations":\[[^\]]+' ~/.echo-core/logs/agent-log.jsonl

# Find Framehead content generations
grep '"framehead-agent"' ~/.echo-core/logs/agent-log.jsonl

# Find Shorts generations
grep '"shorts-generator"' ~/.echo-core/logs/agent-log.jsonl
```

### System State

File: `~/.echo-core/state/system-state.json`

```json
{
  "twin_id": "echo-twin-v0",
  "status": "active",
  "current_cycle": 26,
  "last_wake": "2026-07-17T02:03:09Z",
  "pending_escalations": [],
  "active_domains": ["code"]
}
```

### Routing Log

File: `~/.echo-core/logs/routing-log.jsonl`

Every model routing decision. Plug this into a spreadsheet or dashboard for
cost analysis.

```bash
# Dashboard
python3 ~/.echo-core/scripts/routing_logger.py

# JSON output
python3 -c "
import sys; sys.path.insert(0, '~/.echo-core/scripts')
from routing_logger import summarize_routing
import json; print(json.dumps(summarize_routing(days=7, json_output=True), indent=2))
"
```

### Quick Health One-Liner

```bash
echo "Cycle: $(cat ~/.echo-core/state/system-state.json | \
  python3 -c 'import sys,json;print(json.load(sys.stdin)["current_cycle"])') \
|| Status: $(cat ~/.echo-core/state/system-state.json | \
  python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])') \
|| Domains: $(cat ~/.echo-core/state/consent-contract.yaml | \
  grep 'enabled: true' | wc -l)/10 enabled"
```

---

## 9. Modifying the Consent Contract

The consent contract at `~/.echo-core/state/consent-contract.yaml`
is the system's constitution. Every agent reads it before acting.

### Enabling a Domain

```yaml
domains:
  content:
    enabled: true          # Change from false to true
    label: "Content Agent"
```

Save the file. The next orchestrator cycle will pick up the change and start
routing content work.

### Adding Write Paths

```yaml
write_whitelist:
  - "project-root/**"
  - "~/.echo-core/**"
  - "~/SomeNewProject/**"    # Add this
```

### Setting Expiry

```yaml
expiry:
  duration_days: 14        # Twin auto-halts in 14 days
  auto_renew: false
  on_expiry: "halt_and_report"
```

After 14 days, the system stops itself and sends a final report.

### Pausing the Entire System

```bash
# Set status to paused
cat ~/.echo-core/state/system-state.json | \
  python3 -c "
import sys, json
state = json.load(sys.stdin)
state['status'] = 'paused'
print(json.dumps(state, indent=2))
" > /tmp/state.json && mv /tmp/state.json ~/.echo-core/state/system-state.json
```

Or just pause the cron job:

```bash
hermes cron pause --job-id <job-id>
```

### Emergency Stop

```bash
# 1. Pause the cron job
hermes cron pause --job-id <job-id>

# 2. Set status to revoked
python3 -c "
import json
path = '~/.echo-core/state/system-state.json'
state = json.load(open(path))
state['status'] = 'revoked'
json.dump(state, open(path, 'w'), indent=2)
"
```

---

## 10. Current State vs. Future Roadmap

### Current State (July 2026)

| Component | Status | Details |
|-----------|--------|---------|
| Orchestrator | ✅ Running | 26+ cycles, every 60m, free tier |
| Code Agent | ✅ Running | Repo health checks every cycle |
| Consent Contract | ✅ Active | Code domain enabled, others disabled |
| Model Router | ✅ Built | 5 tiers, heuristic scoring, 10+ tests |
| Packet Protocol | ✅ Built | Structured delegation, routing integration |
| Routing Logger | ✅ Built | JSONL log + CLI dashboard |
| Knowledge Graphs | ✅ Built | 5 graphs initialized, 8 entries |
| Framehead Agent | ✅ Built | 6 modes, Shorts pipeline, image gen |
| Content Agent | ✅ Built | YouTube → 5 formats |
| Monitor Agent | ✅ Built | Git, disk, file checks |
| Research Agent | ✅ Built | arXiv, blog, web search |
| Archiver Agent | ✅ Built | Cleanup, compression, dry-run |
| Comm Agent | ✅ Built | iMessage — consent-gated |
| Social Agent | ✅ Built | X/Twitter — consent-gated |
| Email Agent | ✅ Built | IMAP/SMTP — consent-gated |
| Discord Framehead Bot | ✅ Built | 15/15 tests, connected as `Framehead#1291` |
| Offscreen Skill | ✅ Built | Batch content, images, Shorts |

---

### Future Roadmap

#### Phase: Hardening (Next)

| Feature | Priority | What it means |
|---------|----------|---------------|
| **Local inference fallback** | High | Run offline with Ollama when internet is down |
| **Audit log forensics** | Medium | Tools to search, filter, and analyze the audit trail |
| **Emergency stop protocol** | Medium | Verified halt that can't be bypassed |
| **Multi-profile support** | Low | Run Echo across multiple Hermes profiles |

#### Phase: Intelligence (Medium-term)

| Feature | Priority | What it means |
|---------|----------|---------------|
| **Active knowledge graph queries** | High | Agent asks the knowledge graph before delegating |
| **Decision evidence tracking** | Medium | Each decision traces back to supporting evidence |
| **Trust scoring on stale decisions** | Low | Flag decisions whose evidence is older than N days |
| **Cross-session memory** | Low | Twin remembers what happened across cron restarts |

#### Phase: Expansion (Long-term)

| Feature | Priority | What it means |
|---------|----------|---------------|
| **YouTube Shorts autopilot** | High | Cron-driven pipeline: content → image → Shorts → upload |
| **Cross-platform presence** | Medium | Twin shows up on Discord, Telegram, email, X — same voice |
| **Multi-twin orchestration** | Low | One orchestrator managing twins for different projects |
| **Self-improving routing** | Low | Router learns from past routing outcomes |
| **WebUI dashboard** | Low | Graphical view of cycles, costs, agent activity |

---

## 11. Troubleshooting

### "The cron job won't start"

```bash
# Check if the cron job exists
hermes cron list

# Check if it's enabled
hermes cron list | grep enabled

# Run once to test
hermes cron run --job-id <job-id>

# Check logs
tail -20 ~/.echo-core/logs/agent-log.jsonl
```

### "No delegations are happening"

```bash
# Check consent contract — is the domain enabled?
cat ~/.echo-core/state/consent-contract.yaml

# Check system state — is it active?
cat ~/.echo-core/state/system-state.json

# Check if the domain script exists
ls ~/.echo-core/scripts/
```

### "The model router is routing everything to premium"

```bash
# Check if model-tiers.yaml exists
cat ~/.echo-core/config/model-tiers.yaml

# Test a simple routing
python3 -c "
import sys
sys.path.insert(0, '~/.echo-core/scripts')
from classify_task import classify_task
for task in ['fix typo', 'check git status', 'generate content']:
    r = classify_task(task)
    print(f\"{task}: {r['tier']} — {r['model']}\")
"
```

### "The Discord bot went offline"

```bash
# Check if the process is running
ps aux | grep "run.py" | grep -v grep

# Restart
cd ~/FrameHead/discord-framehead
source .venv/bin/activate
python3 run.py &

# Check logs
tail -20 ~/.echo-core/logs/agent-log.jsonl | grep discord
```

### "Agent tasks are failing silently"

The orchestrator logs every cycle. Check for `"status": "completed"` vs
`"status": "failed"`:

```bash
grep '"status":"failed"' ~/.echo-core/logs/agent-log.jsonl
grep '"status":"escalation"' ~/.echo-core/logs/agent-log.jsonl

# Look for error messages in agent output
grep -i "error\|exception\|traceback" ~/.echo-core/logs/agent-log.jsonl
```

---

## 12. Appendix: File Tree

```
~/.echo-core/
├── config/
│   └── model-tiers.yaml              # 5-tier model routing config
│
├── logs/
│   ├── agent-log.jsonl               # Shared audit trail (append-only)
│   └── routing-log.jsonl             # Every model routing decision
│
├── state/
│   ├── consent-contract.yaml         # System-wide policy
│   └── system-state.json             # Current cycle, status, flags
│
├── scripts/
│   ├── setup.sh                      # One-time initialization
│   ├── classify_task.py              # Task complexity → model tier
│   ├── packet_builder.py             # Structured Agent Packet builder
│   ├── routing_logger.py             # Cost tracking + CLI dashboard
│   ├── code_agent.py                 # Git/file/project health checks
│   ├── content_agent.py              # YouTube → summary/blog/thread/quotes
│   ├── monitor_agent.py              # Disk, git, file change monitor
│   ├── research_agent.py             # arXiv + blog + web research
│   ├── framehead_agent.py            # Framehead voice content gen
│   ├── framehead_generator.py        # ComfyUI image gen pipeline
│   ├── offscreen_content.py          # Batch content via Ollama
│   ├── shorts_generator.py           # Image + TTS → video
│   ├── shorts_pipeline.py            # Orchestrated Shorts pipeline
│   └── archiver_agent.py             # Cleanup, compress, cache removal
│
├── content/                          # All generated content
│   ├── framehead-observations/       # Text observations
│   ├── framehead-threads/            # Thread-style posts
│   ├── framehead-images/             # ComfyUI-generated images
│   └── framehead-shorts/             # YouTube Shorts (MP4)
│
├── research/                         # Research agent reports
│
└── graphs/                           # Knowledge graphs (5 initialized)
    ├── intent_graph.json
    ├── decision_graph.json
    ├── evidence_graph.json
    ├── operational_graph.json
    └── trust_graph.json
```

---

## Glossary

| Term | Meaning |
|------|---------|
| **ACP** | Agentic Control Plane — the architecture pattern this system was inspired by |
| **Agent Packet** | Structured work unit: mission, routing, scope, verification, acceptance criteria |
| **Consent contract** | YAML policy file that every agent checks before acting |
| **Cycle** | One complete run of the orchestrator loop (wake → decide → delegate → log → sleep) |
| **Domain agent** | A specialized sub-agent with a narrow persona and limited toolset |
| **Orchestrator** | The "self" — decides what to do, delegates, reports back |
| **Project Echo** | The name of this digital twin system |
| **Tier** | A model tier (free/local/paid-cheap/paid-premium/escalation) |
| **Twin** | Shorthand for the digital twin system |

---

*Framehead is watching.* 👁️

*Last updated: July 17, 2026*
