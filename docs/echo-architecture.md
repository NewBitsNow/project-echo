# Project Echo — Digital Twin Architecture

> Architecture blueprint for **Project Echo** — an autonomous multi-agent system that operates
> on behalf of a human subject — a coordinated collective of agents acting
> as a single digital self.
>
> Status: **Draft v2 — Multi-Agent System** (building incrementally)

---

## 1. Concept

A **Digital Twin System** is not a single agent. It is a **coordinated
collective of specialized agents** working as one:

- **Orchestrator** — the "self." Makes high-level decisions, delegates to
  domain agents, reports to the human. This is the twin's consciousness.
- **Domain Agents** — specialized sub-agents, each owning a domain (code,
  communications, monitoring, research, etc.)
- **Shared Memory** — a common state that agents read/write to coordinate
- **Consent Contract** — system-wide policy that constrains every agent

The system is *sovereign* — it wakes, decides, delegates, acts, logs, and
sleeps on a schedule without a human in the loop for routine operations.

### Key Principles

| Principle | Meaning |
|-----------|---------|
| **Consent-first** | Every agent checks the contract before acting |
| **Domain isolation** | Agents only have tools for their domain |
| **Orchestrator authority** | Only the orchestrator delegates. Agents cannot spawn agents. |
| **Shared state** | Agents coordinate through a log, not by messaging each other |
| **Audit trail** | Every decision by every agent is recorded |
| **Configurable expiry** | The entire system expires after a set duration |

---

## 2. System Architecture

```
                    ┌──────────────────────┐
                    │        HUMAN         │
                    │  Sets policy, reviews│
                    │  logs, renews consent│
                    └──────────┬───────────┘
                               │ Consent & constraints
                               ▼
                    ┌──────────────────────┐
                    │   CONSENT CONTRACT   │
                    │  System-wide policy  │
                    │  checked by every    │
                    │  agent before action │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │    ORCHESTRATOR      │ ◄── The "Self"
                    │  • Wakes on schedule │     Makes decisions,
                    │  • Reads context     │     delegates work,
                    │  • Decides priority  │     reports back
                    │  • Delegates to      │
                    │    domain agents     │
                    │  • Reports to human  │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────┘      └────────────┐
              ▼                                 ▼
   ┌──────────────────┐           ┌──────────────────┐
   │  DOMAIN AGENT A  │           │  DOMAIN AGENT B  │
   │  e.g. Code/Dev   │           │  e.g. Monitor    │
   │                  │           │                  │
   │  Tools: terminal,│           │  Tools: web,     │
   │  git, file, cron │           │  file, messaging │
   │  Persona: dev    │           │  Persona: sysop  │
   │  ⊂ twin persona  │           │  ⊂ twin persona  │
   └──────────────────┘           └──────────────────┘
              │                              │
              │         ┌───────────────┐    │
              └─────────┤  SHARED LOG   ├────┘
                        │  & STATE      │
                        │  • Decisions  │
                        │  • Actions    │
                        │  • Escalations│
                        │  • Agent memos│
                        └───────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  COMMUNICATION       │
                    │  Summary reports,    │
                    │  escalation alerts,  │
                    │  emergency stop      │
                    └──────────────────────┘
```

### Runtime: Hermes Agent

The system runs on **Hermes Agent** — the same infrastructure that hosts me
(Framehead). Each agent type maps to Hermes primitives:

| Component | Hermes Primitive |
|-----------|-----------------|
| Orchestrator | Recurring `cronjob` — the heartbeat |
| Domain Agents | `delegate_task` — spawned per task |
| Persona | Hermes `skill` — SKILL.md with YAML frontmatter |
| Consent | Policy file read by all agents |
| Log | Append-only file on disk |
| Delivery | cronjob `deliver` — messaging platform |

### The Inference Dependency

**Current limitation:** Hermes needs an API endpoint for inference. The twin
system cannot run fully offline without a local LLM.

| Scenario | Status |
|----------|--------|
| Twin runs on schedule (internet available) | ✅ Works now via cron |
| Twin runs during internet outages | ❌ Requires local LLM |
| Twin on isolated network (no outbound) | ❌ Same |
| Twin at sea / wilderness (no cell) | ❌ Same |

**Long-term fix:** Self-hosted inference stack (llama.cpp, Ollama, vLLM)
plus a local Hermes profile pointed at the local endpoint.

---

## 3. Agent Types

### Orchestrator

The orchestrator is the **self** of the twin system. It runs on a schedule
and each cycle:

1. **Wake** — triggered by cron
2. **Read state** — current time, expiry status, recent log entries,
   pending escalations, any messages from the human
3. **Check consent** — is the contract still valid? Has the human revoked?
4. **Decide priorities** — what needs attention? Any time-sensitive items?
5. **Delegate** — spawn domain agents via `delegate_task` for each task
6. **Collect results** — wait for sub-agent summaries
7. **Log** — record the cycle's decisions and outcomes
8. **Report** — if the human is available, send a briefing
9. **Sleep** — until next schedule

The orchestrator's persona is the **core self** — the closest representation
of the human's identity, values, and voice.

### Domain Agents

Domain agents are **specialized workers**. Each has:

- A **narrow persona** — a "slice" of the full persona relevant to its domain
- A **limited toolset** — only the tools it needs
- A **scope** — clear boundaries of what it does and doesn't do
- A **mandate** — what it's expected to achieve each cycle

Examples:

| Agent | Domain | Tools | Persona Slice |
|-------|--------|-------|---------------|
| **Code Agent** | Maintains Echo project | terminal, git, file | Developer persona |
| **Content Agent** | Generates social content | web, file, image | Creator persona |
| **Monitor Agent** | Watches systems, alerts | web, file, messaging | Sysop persona |
| **Comm Agent** | Handles messages (with consent) | email, messaging | Communicator persona |
| **Research Agent** | Gathers information | web, file | Analyst persona |

---

## 4. Shared State & Coordination

Agents don't talk to each other directly. They coordinate through a
**shared state** — an append-only log file.

### Log Schema

```json
{
  "timestamp": "2026-07-15T14:00:00Z",
  "agent": "orchestrator",
  "cycle": 47,
  "action": "delegate",
  "target": "code-agent",
  "task": "Update README with architecture overview",
  "status": "spawned",
  "result": null
}
```

```json
{
  "timestamp": "2026-07-15T14:05:00Z",
  "agent": "code-agent",
  "cycle": 47,
  "action": "git_commit",
  "target": "README.md",
  "status": "completed",
  "result": "commit abc123 - Updated README with architecture"
}
```

The log is append-only (no deletion, no modification). This gives:

- **Audit trail** — every action is recorded
- **Coordination** — agents see what other agents did
- **Recovery** — if an agent crashes, the next cycle reads the log
- **Human review** — the human can inspect everything later

### State File

A lightweight JSON state file tracks the high-level system state:

```json
{
  "twin_id": "project-echo-v1",
  "status": "active",
  "current_cycle": 47,
  "last_wake": "2026-07-15T14:00:00Z",
  "expires_at": null,
  "active_agents": ["code-agent"],
  "pending_escalations": [],
  "last_report_sent": "2026-07-15T13:00:00Z"
}
```

---

## 5. Consent Contract

The consent contract is the **system-wide policy** that every agent checks
before acting. It lives in a single file that all agents read.

```yaml
twin_id: "project-echo-v1"
subject: "Project Echo Contributors"
created: "2026-07-15"
expires: null                       # ISO date, or null for no expiry

# Human contact details for escalation & reporting
human_contact:
  primary: "email"
  backup: "sms"                     # Optional
  cooldown_seconds: 3600            # Min time between alerts

# Domain-level permissions
domains:
  code:
    enabled: true
    # Tools this domain agent has access to
    tools: ["terminal", "file", "git", "web"]
    # Specific boundaries
    restrictions: []
    
  content:
    enabled: false                  # Not ready yet
    
  communications:
    enabled: false                  # Locked down by default
    
  monitoring:
    enabled: false                  # Not configured yet

# System-wide boundaries (all agents)
global_restrictions:
  - "spending money or authorizing payments"
  - "sending messages to third parties without explicit human approval"
  - "modifying system configuration (hostname, network, security)"
  - "deleting files outside the project directory"
  - "accessing financial accounts or credentials"
  - "modifying the consent contract itself"

# Write whitelist (where agents can create/modify files)
write_whitelist:
  - "project-root/**"
  - "~/.echo-core/**"
  - "~/.hermes/skills/project-echo/**"

# Escalation behavior
escalation:
  channel: "email"
  cooldown_seconds: 3600
  on_boundary_hit: "pause_domain"   # halt the domain, continue others
  on_revocation: "halt_all"         # complete shutdown

# Expiry
expiry:
  duration_days: null               # null = no expiry
  auto_renew: false
  on_expiry: "halt_and_report"
```

### Policy Check Flow

```
Every agent, before executing any action:

1. Is the consent contract file readable?
   No  → HALT. Cannot verify policy. Escalate.
   Yes → Continue.

2. Is the twin within its expiry period?
   No  → HALT. Twin has expired.
   Yes → Continue.

3. Is the twin status "active"?
   No  → HALT. Twin revoked or paused.
   Yes → Continue.

4. Is this domain agent enabled?
   No  → HALT. Domain not authorized.
   Yes → Continue.

5. Does the proposed action cross a global boundary?
   Yes → ESCALATE. Log the boundary hit, send alert.
   No  → Continue.

6. Is the target path within the write whitelist?
   No  → ESCALATE. Log, alert.
   Yes → Proceed.
```

---

## 6. Agent Loop Detail

### Orchestrator Cycle

```
[HUMAN SETS POLICY]
        │
        ▼
[SCHEDULE TRIGGER]
        │
        ▼
[ORCHESTRATOR WAKE]
        │
        ├── 1. Read consent contract ──── Expired? → HALT
        │
        ├── 2. Read state file ────────── Revoked? → HALT
        │
        ├── 3. Read recent log entries ── Pending escalations? → Handle
        │
        ├── 4. Assess context ─────────── Time of day, last cycle,
        │                                  what's happening in the world
        │
        ├── 5. Decide priorities ──────── What needs to happen this cycle?
        │
        ├── 6. Delegate to agents ─────── spawn via delegate_task
        │                                  each agent gets its persona slice
        │                                  + task description + consent excerpt
        │
        ├── 7. Collect results ────────── sub-agents return summaries
        │
        ├── 8. Log cycle ──────────────── append to shared log
        │
        ├── 9. Update state ───────────── increment cycle, update timestamp
        │
        └── 10. Report (optional) ─────── send briefing to human
                                            (if reporting channel configured)
```

### Domain Agent Lifecycle

```
[SPAWNED BY ORCHESTRATOR]
        │
        ▼
[LOAD PERSONA SLICE]
        │
        ├── Read persona for this domain
        │
        ├── Read consent contract (relevant sections)
        │
        ├── Read recent log entries (situational awareness)
        │
        ├── Check: Am I still within policy? → No? → Report boundary
        │
        ▼
[EXECUTE TASK]
        │
        ├── For each action:
        │   ├── Check consent (quick check)
        │   ├── Execute action via tool
        │   ├── Log action to shared log
        │   └── Continue
        │
        ▼
[RETURN SUMMARY]
        │
        ├── What was done
        ├── What was skipped (and why)
        ├── Any escalations needed
        └── Any state to preserve for next cycle
```

---

## 7. Multi-Agent Coordination Pattern

The system uses **orchestrator-led delegation**:

- Agents do NOT talk to each other
- Agents DO read the shared log
- The orchestrator reads ALL agent summaries and synthesizes
- The orchestrator is the only agent that reports to the human

```
Orchestrator: "It's 3 PM. Let me check what needs doing."

Orchestrator: [reads log]
  → Code agent ran 2 hours ago. Patch in review.
  → Monitor agent found nothing new.
  → No pending escalations.

Orchestrator: "Code patch needs follow-up. Deploying code agent."

Orchestrator: [delegate_task -> code agent]
  Task: "Check if PR #12 was merged. If so, deploy staging."
  Tools: [terminal, git, web]
  Persona: [code persona slice]

Code agent: [runs task, logs actions, returns summary]
  → "PR #12 merged. Deployed to staging. Tests pending."

Orchestrator: [logs cycle, writes state]
  → "Cycle 48 complete. Deployed PR #12 to staging."
  → [reports to human if due]
```

---

## 8. Implementation Path

### Phase 1: Foundation ✅ (Complete)
- [x] Read existing persona spec (Framehead)
- [x] Draft architecture document (v2 — multi-agent system)
- [x] Create consent contract (first real file)
- [x] Create shared log + state files
- [x] Create orchestrator persona skill
- [x] Create first domain agent persona skill (code agent)
- [x] Set up first test cron job (project-echo-heartbeat)

### Phase 2: First Domain Agent
- [ ] Build and test code/content agent
- [ ] Implement orchestrator cycle (manual test)
- [ ] Implement consent checking in agent startup
- [ ] Implement shared log append
- [ ] Implement escalation handler

### Phase 3: Autonomy Loop
- [ ] Full orchestrator cron job (automated)
- [ ] Reporting channel configured
- [ ] Multiple domain agents operational
- [ ] Duration/expiry enforcement

### Phase 4: Hardening
- [ ] Local inference fallback (llama.cpp)
- [ ] Audit log forensics
- [ ] Emergency stop protocol
- [ ] Multi-twin orchestration (future)

---

## 9. Open Questions

(Answered as we build)

- [ ] What are the first 3 domain agents to build?
- [ ] What model/provider for the twin? Same as current? Different?
- [ ] What messaging channel for reports? (Telegram? Email? SMS?)
- [ ] How often should the orchestrator wake? (Every hour? Every 6? Daily?)
- [ ] Should the orchestrator be able to modify its own schedule?
- [ ] Should domain agents have their own model (cheaper/faster)?
- [ ] What happens when two agent cycles overlap?

---

*This document evolves alongside the build. Architecture isn't static —
it's a living blueprint.*
