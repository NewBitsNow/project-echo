# Project Echo — Installation Guide

> Step-by-step instructions for macOS and Linux. Covers everything from zero to a running system with all 10 domain agents.

---

## Prerequisites

| Requirement | macOS | Linux |
|-------------|-------|-------|
| Python 3.11+ | `brew install python@3.12` | `apt install python3 python3-pip` |
| Git | Included with Xcode CLT | `apt install git` |
| Hermes Agent | See step 1 | See step 1 |
| Homebrew | `brew` (included or install from brew.sh) | Not required |
| sudo access | Not required | Recommended for pip |

---

## Step 1: Install Hermes Agent

Project Echo runs on Hermes Agent — an open-source AI agent framework. Every domain agent is a Hermes skill.

### macOS

```bash
# Install via the official installer
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Or via pip
pip3 install hermes-agent

# Verify
hermes --version
```

### Linux

```bash
# Install via the official installer
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Or via pip
pip3 install hermes-agent

# Verify
hermes --version
```

### Configure Hermes

```bash
# Run the setup wizard
hermes setup

# Or set provider + model manually
hermes config set model.default "qwen/qwen3-coder:free"
hermes config set model.provider "openrouter"

# Add your OpenRouter API key to ~/.hermes/.env
echo "OPENROUTER_API_KEY=sk-or-your-key" >> ~/.hermes/.env
```

**If you want local models (no API cost):**

```bash
# Install Ollama
brew install ollama         # macOS
# or: curl -fsSL https://ollama.com/install.sh | sh  # Linux

# Pull a coding model
ollama pull qwen2.5-coder:7b

# Configure Hermes to use it
hermes config set model.default "qwen2.5-coder:7b"
hermes config set model.provider "ollama"
hermes config set model.base_url "http://localhost:11434/v1"
```

---

## Step 2: Clone Project Echo

```bash
git clone https://github.com/NewBitsNow/project-echo.git
cd project-echo
```

---

## Step 3: Install Python Dependencies

```bash
# Core dependencies
pip3 install pyyaml pytest youtube-transcript-api

# Verify
python3 -m pytest tests/ -v
```

**Expected output:** 21 passed (10 model routing tests + 11 packet protocol tests)

---

## Step 4: Set Up the Twin Output Directory

Project Echo stores its state, logs, and content in `~/Documents/twin-output/`.

```bash
# Create the directory structure
mkdir -p ~/Documents/twin-output/{scripts,config,tests,content,research,logs,state,graphs,archives}

# Create consent contract
cat > ~/Documents/twin-output/state/consent-contract.yaml << 'EOF'
twin_id: "project-echo"
subject: "Your Name"
created: "2026-07-15"
expires: null
status: "active"

domains:
  code:
    label: "Code Agent"
    enabled: true
    description: "Git operations, code review, project maintenance"
  content:
    label: "Content Agent"
    enabled: true
    description: "YouTube transcripts, summaries, blog posts"
  monitor:
    label: "Monitor Agent"
    enabled: true
    description: "System monitoring, git status, disk usage"
  research:
    label: "Research Agent"
    enabled: true
    description: "arXiv papers, blog feeds, web search"
  comm:
    label: "Comm Agent"
    enabled: false
    description: "iMessage/SMS — disabled by default"
  social:
    label: "Social Agent"
    enabled: false
    description: "X/Twitter — disabled by default"
  email:
    label: "Email Agent"
    enabled: false
    description: "Email — disabled by default"
  archiver:
    label: "Archiver Agent"
    enabled: true
    description: "Cleanup and compression"
  framehead:
    label: "Framehead Agent"
    enabled: true
    description: "Persona content generation"

global_restrictions:
  no_spending: true
  no_third_party_messaging: true
  no_system_config_changes: true

write_whitelist:
  - "/Volumes/4TB_SSD/FrameHead/**"
  - "/Users/$USER/Documents/twin-output/**"
EOF

# Create initial state file
cat > ~/Documents/twin-output/state/system-state.json << 'EOF'
{
  "twin_id": "project-echo",
  "status": "active",
  "current_cycle": 0,
  "last_wake": null,
  "pending_escalations": [],
  "pending_content_tasks": [],
  "research_topics": []
}
EOF

# Create initial log files
echo "[]" > ~/Documents/twin-output/logs/agent-log.jsonl
echo "[]" > ~/Documents/twin-output/logs/routing-log.jsonl
```

### Customize the Consent Contract

Edit `~/Documents/twin-output/state/consent-contract.yaml`:

1. Change `subject` to your name
2. Change `created` to today's date
3. Update `write_whitelist` paths to match your system
4. Enable/disable domains as desired

---

## Step 5: Copy Project Echo Scripts

Link or copy the scripts into the twin-output directory:

```bash
# Option A: Symlink (stays in sync with git)
ln -sf "$PWD/scripts/classify_task.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/packet_builder.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/routing_logger.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/graph_store.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/content_agent.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/monitor_agent.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/research_agent.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/archiver_agent.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/scripts/framehead_agent.py" ~/Documents/twin-output/scripts/
ln -sf "$PWD/config/model-tiers.yaml" ~/Documents/twin-output/config/
ln -sf "$PWD/tests/" ~/Documents/twin-output/tests
ln -sf "$PWD/graphs/" ~/Documents/twin-output/graphs

# Option B: Copy (independent of git repo)
cp -r scripts/* ~/Documents/twin-output/scripts/
cp config/model-tiers.yaml ~/Documents/twin-output/config/
cp -r tests/ ~/Documents/twin-output/
cp -r graphs/ ~/Documents/twin-output/
```

---

## Step 6: Verify the Core System

```bash
# Run all tests
cd ~/Documents/twin-output && python3 -m pytest tests/ -v

# Initialize knowledge graphs
python3 scripts/graph_store.py init

# Import ADRs from MEMORY.md (if you have one)
python3 scripts/graph_store.py import-adrs

# Check the routing dashboard
python3 scripts/routing_logger.py

# Test the model router
python3 -c "
from scripts.classify_task import classify_task
tests = [
    ('Fix a typo in the README', 'free'),
    ('What is the current state?', 'free'),
    ('Design the database schema', 'paid-premium'),
]
for desc, _ in tests:
    r = classify_task(desc)
    print(f'  {r[\"tier\"]:15s} → {desc}')
"
```

---

## Step 7: Install Hermes Skills (Optional — for Autonomous Mode)

If you want Project Echo to run autonomously via cron, install the orchestrator skill:

```bash
# Create the skills directory
mkdir -p ~/.hermes/skills/autonomous-ai-agents

# Copy the orchestrator skill
cp -r skills/ ~/.hermes/skills/autonomous-ai-agents/

# Set up the cron job
hermes cron create jason-twin-heartbeat --schedule "every 60m" \
  --prompt "You are the Project Echo orchestrator. Run one cycle." \
  --skills autonomous-ai-agents/jason-twin-orchestrator
```

Alternatively, install domain agent skills from the Hub:

```bash
hermes skills install jason-twin-orchestrator
hermes skills install jason-twin-code-agent
hermes skills install jason-twin-content-agent
# ... etc
```

---

## Step 8: Test Individual Agents

### Content Agent

```bash
cd ~/Documents/twin-output

# YouTube → summary
python3 scripts/content_agent.py "https://www.youtube.com/watch?v=VIDEO_ID" --format summary

# YouTube → blog post
python3 scripts/content_agent.py "https://www.youtube.com/watch?v=VIDEO_ID" --format blog-post

# Output saved to ~/Documents/twin-output/content/
```

### Monitor Agent

```bash
python3 scripts/monitor_agent.py --report
# Shows: git status, file changes, disk usage
```

### Research Agent

```bash
python3 scripts/research_agent.py "your research topic" --sources arxiv
# Output saved to ~/Documents/twin-output/research/
```

### Archiver Agent

```bash
# Dry run (see what would be cleaned)
python3 scripts/archiver_agent.py

# Live run (actually clean)
python3 scripts/archiver_agent.py --clean --compress
```

### Framehead Agent

```bash
python3 scripts/framehead_agent.py --mode observation --topic "humans and coffee"
python3 scripts/framehead_agent.py --mode one-liner
python3 scripts/framehead_agent.py --mode thread --topic "AI anxiety"
```

---

## Step 9: Set Up Optional Agents

### Comm Agent (iMessage — macOS only)

```bash
# Install imsg
brew install steipete/tap/imsg

# Or download directly
curl -sL "https://github.com/openclaw/imsg/releases/download/v0.13.0/imsg-macos.zip" -o /tmp/imsg.zip
unzip /tmp/imsg.zip -d ~/.local/bin/
chmod +x ~/.local/bin/imsg

# Grant permissions:
# System Settings → Privacy → Full Disk Access → enable for Terminal
# Messages.app must be signed in with your Apple ID

# Verify
imsg chats --limit 5 --json

# Enable in consent contract (~/Documents/twin-output/state/consent-contract.yaml)
# Set comm.enabled: true
```

### Social Agent (X/Twitter)

```bash
# Install xurl
brew install --cask xdevplatform/tap/xurl

# Set up X API credentials (manual OAuth flow — one-time)
xurl auth apps add my-app --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
xurl auth oauth2 --app my-app YOUR_USERNAME
xurl auth default my-app

# Verify
xurl whoami

# Enable in consent contract
# Set social.enabled: true
```

### Email Agent (IMAP/SMTP)

```bash
# Install himalaya
brew install himalaya

# Configure
himalaya account configure

# Or create config manually at ~/.config/himalaya/config.toml
# (See himalaya documentation for details)

# Verify
himalaya folder list

# Enable in consent contract
# Set email.enabled: true
```

---

## Step 10: Run the Full Test Suite

```bash
cd ~/Documents/twin-output && python3 -m pytest tests/ -v
```

**Expected:** 21 passed.

---

## Directory Layout (After Installation)

```
~/Documents/twin-output/
├── scripts/           # All agent scripts (symlinked or copied from repo)
├── config/            # model-tiers.yaml
├── tests/             # 21 tests
├── graphs/            # 5 knowledge graphs
├── content/           # Content agent output
├── research/          # Research agent output
├── logs/              # agent-log.jsonl, routing-log.jsonl
├── state/             # consent-contract.yaml, system-state.json
└── archives/          # Compressed archives
```

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: yaml` | Missing pyyaml | `pip3 install pyyaml` |
| `ModuleNotFoundError: youtube_transcript_api` | Missing dependency | `pip3 install youtube-transcript-api` |
| `No module named pytest` | Missing pytest | `pip3 install pytest` |
| Tests fail with import errors | Scripts not in Python path | Run from `~/Documents/twin-output/` |
| Content agent: "Transcript disabled" | Video has no captions | Try a different video |
| Research agent: "429" | arXiv rate limit | Wait 30 seconds, retry |
| `imsg: command not found` | Not in PATH | Add `~/.local/bin` to PATH: `export PATH="$HOME/.local/bin:$PATH"` |
| Cron job not running | Hermes not configured | Run `hermes gateway install` |
| Model router returns "escalation" | Task too complex for any tier | Reduce task complexity or add premium model credits |

---

## What's Next

Once installed, Project Echo runs autonomously via cron every 60 minutes. Each cycle the orchestrator:

1. Checks the consent contract
2. Routes tasks to the cheapest adequate model
3. Delegates work to domain agents as structured packets
4. Logs every decision for cost tracking
5. Reports back to you

Check the dashboard anytime:

```bash
python3 ~/Documents/twin-output/scripts/routing_logger.py
```