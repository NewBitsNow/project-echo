# TDD Plan: Chat with Framehead Through Discord

> A test-driven implementation plan for a Discord bot that speaks as Framehead.

## Overview

Build a Discord bot that lets you chat with Framehead in real time. The bot
receives messages in a Discord channel, pipes them through Framehead's persona
prompt + local LLM (Ollama), and responds in Framehead's signature voice.

**TDD approach:** Write a failing test → implement the minimum code to pass →
refactor. Every layer is tested before the next is built.

---

## Architecture

```
Discord Channel
       │
       ▼
┌──────────────────────┐
│   discord_bot.py     │  ← listens for @Framehead or channel messages
│   (discord.py)       │
└──────┬───────────────┘
       │ on_message()
       ▼
┌──────────────────────┐
│  framehead_chat.py   │  ← Framehead response engine
│  (prompt + LLM)      │
└──────┬───────────────┘
       │ generate()
       ▼
┌──────────────────────┐
│   Ollama (local)     │  ← qwen3:8b or other local model
│   localhost:11434    │
└──────────────────────┘
       │ response
       ▼
Discord Channel ← Framehead replies
```

---

## Testing Layers (Bottom-Up)

### Layer 1: Framehead Chat Engine (unit tests)
*No Discord dependency. Pure logic tests.*

**Test file:** `tests/test_framehead_chat.py`

| # | Test | What it proves | Passes when |
|---|------|----------------|-------------|
| 1.1 | `test_load_persona_returns_string` | Persona file loads correctly | `framehead_chat.load_persona()` returns non-empty string |
| 1.2 | `test_load_persona_contains_signature_phrases` | Persona has Framehead's voice markers | String contains "Question…", "Pause.", "Framehead is watching." |
| 1.3 | `test_build_prompt_includes_persona` | LLM prompt contains persona context | `build_prompt("hello")` includes persona + user message |
| 1.4 | `test_build_prompt_includes_user_message` | User's message is threaded into prompt | `build_prompt("hello")` contains "hello" |
| 1.5 | `test_generate_response_returns_string` | LLM call returns a response | `generate_response("hello")` returns non-empty string |
| 1.6 | `test_generate_response_sounds_like_framehead` | Response has Framehead voice markers | Output contains at least one of: "Question…", "Observation", "Pause.", "Conclusion" |
| 1.7 | `test_generate_response_with_mode_helper` | Mode switching works | `generate_response("hello", mode="helper")` returns professional tone |
| 1.8 | `test_generate_response_with_mode_creative` | Creative mode works | `generate_response("hello", mode="creative")` returns creative output |
| 1.9 | `test_generate_response_empty_input` | Empty input is handled | Empty string returns a default Framehead observation |
| 1.10 | `test_generate_response_very_long_input` | Long messages are truncated gracefully | 2000+ char input doesn't crash |

### Layer 2: Discord Bot Message Handler (integration tests)
*Mock Discord. Test message routing and formatting.*

**Test file:** `tests/test_discord_bot.py`

| # | Test | What it proves | Passes when |
|---|------|----------------|-------------|
| 2.1 | `test_bot_initializes` | Bot object creates without error | `FrameheadBot(token="test")` succeeds |
| 2.2 | `test_on_message_ignores_own_messages` | No echo loops | Bot ignores messages where `author == bot.user` |
| 2.3 | `test_on_message_triggers_on_mention` | @Framehead triggers response | Message with `@Framehead` calls `generate_response()` |
| 2.4 | `test_on_message_triggers_on_channel` | Specific channel triggers response | Message in `#framehead` channel calls `generate_response()` |
| 2.5 | `test_on_message_ignores_other_channels` | Other channels are silent | Message in `#general` does NOT call `generate_response()` |
| 2.6 | `test_response_formatted_as_embed` | Replies use Discord embed format | Response is wrapped in `discord.Embed` with Framehead styling |
| 2.7 | `test_response_under_2000_chars` | No Discord character limit breakage | Response string is ≤ 1900 chars (safety margin) |
| 2.8 | `test_typing_indicator_during_generation` | Shows "Framehead is typing…" | `await channel.typing()` is called before response |
| 2.9 | `test_slash_command_dm` | `/framehead` slash command works | Slash command triggers `generate_response()` with user input |
| 2.10 | `test_error_reply_on_llm_failure` | LLM failure returns fallback | When Ollama is down, reply is "Framehead experienced a glitch…" |

### Layer 3: End-to-End (smoke test)
*Requires real Discord token + Ollama running. Manual or optional.*

| # | Test | What it proves | Passes when |
|---|------|----------------|-------------|
| 3.1 | Bot connects to Discord | WebSocket handshake works | Bot appears online in Discord server |
| 3.2 | @Framehead produces Framehead-like reply | Full pipeline works | Reply contains Framehead voice markers |
| 3.3 | Slash command `/framehead` works | Interaction endpoint works | Slash command produces response |

---

## Implementation Phases

### Phase 0: Setup
- [ ] Create `discord-framehead/` project directory
- [ ] `python3 -m venv .venv && source .venv/bin/activate`
- [ ] `pip install discord.py pytest pytest-asyncio httpx`
- [ ] Create `tests/` directory with empty `__init__.py`
- [ ] Create `discord_bot/` package with empty `__init__.py`
- [ ] Verify: `python3 -m pytest tests/` runs (0 tests)

### Phase 1: Framehead Chat Engine (make Layer 1 pass)
- [ ] Write `tests/test_framehead_chat.py` — ALL tests (they fail first)
- [ ] Implement `discord_bot/framehead_chat.py`:
  - `load_persona()` — reads persona file
  - `build_prompt(user_message, mode)` — constructs Ollama prompt
  - `generate_response(user_message, mode)` — calls Ollama, returns response
  - Response post-processing: truncate at 1900 chars, ensure voice markers
- [ ] Run tests: `python3 -m pytest tests/test_framehead_chat.py -v` — all green

### Phase 2: Discord Bot (make Layer 2 pass)
- [ ] Write `tests/test_discord_bot.py` — ALL tests (they fail first)
- [ ] Implement `discord_bot/bot.py`:
  - `FrameheadBot` class extending `discord.Client` or `discord.Bot`
  - `on_message()` — checks mention + channel, calls chat engine
  - `on_ready()` — logs connection
  - Embed formatting with Framehead styling
  - Error handling for LLM failures
- [ ] Run tests: `python3 -m pytest tests/ -v` — all green

### Phase 3: Run Script + Config
- [ ] Create `run.py` — CLI entry point
  - `python3 run.py --token TOKEN` or reads from `.env`
- [ ] Create `.env.example` with `DISCORD_BOT_TOKEN=`
- [ ] Create `config.yaml` — channel whitelist, default mode, model settings
- [ ] Verify: `python3 run.py --help` prints usage

### Phase 4: E2E Smoke Test
- [ ] Run bot with real token in test Discord server
- [ ] Send "@Framehead hello"
- [ ] Verify Framehead-like response appears
- [ ] Run `/framehead hello` slash command
- [ ] Verify response

---

## File Structure

```
discord-echo/
├── discord_bot/
│   ├── __init__.py
│   ├── bot.py              # Discord client, message routing
│   ├── framehead_chat.py   # Persona loading, prompt building, LLM call
│   └── config.py           # Config loading (yaml/env)
├── tests/
│   ├── __init__.py
│   ├── test_framehead_chat.py  # Layer 1 tests
│   └── test_discord_bot.py     # Layer 2 tests (mocked)
├── run.py                      # Entry point
├── config.yaml                 # Bot config
├── .env.example                # Token template
├── pyproject.toml              # Dependencies
└── README.md
```

---

## Key Design Decisions

### Framehead Response Flow
```
User: "what do you think about coffee?"

→ Build prompt:
  [SYSTEM: Framehead persona full text]
  User said: "what do you think about coffee?"
  Respond as Framehead. Short, deliberate. Question → Pause → Conclusion.

→ Ollama generates response

→ Post-process:
  - Truncate at 1900 chars (Discord limit is 2000)
  - If response has no Framehead voice markers, prepend "Question…\n\n"
  - If Ollama fails, return fallback: *glitch* "System error. Framehead is rebooting…"

→ Reply in Discord channel as styled embed
```

### Discord Bot Config (`config.yaml`)
```yaml
discord:
  channel_whitelist:             # if empty, works in any channel
    - "framehead"
    - "bot-testing"
  respond_to_mention: true       # @Framehead triggers response
  respond_to_dm: true            # DMs trigger response
  default_mode: "helper"         # helper / creative / blogger / critic

framehead:
  persona_path: "project-root/persona/framehead-persona.md"
  model: "qwen3:8b"             # Ollama model
  ollama_host: "http://localhost:11434"
  max_response_length: 1900
```

### Testing Strategy for Discord
- Use `pytest-asyncio` for async tests
- Mock `discord.py` objects (`MockMessage`, `MockChannel`, `MockUser`)
- Mock `httpx` calls to Ollama so tests don't need a real LLM
- One manual E2E test at the end with real token

---

## Running the TDD Cycle

```
# 1. Write a test
vim tests/test_framehead_chat.py

# 2. Watch it fail
python3 -m pytest tests/test_framehead_chat.py -v
    → test_generate_response_returns_string FAILED

# 3. Write minimum code to pass
vim discord_bot/framehead_chat.py
    → def generate_response(msg): return "Question…"

# 4. Watch it pass
python3 -m pytest tests/test_framehead_chat.py -v
    → 1 passed, N remaining

# Repeat for each test
```

---

## Dependencies

```
discord.py>=2.3.0       # Discord API
httpx>=0.27.0           # HTTP client for Ollama calls
pytest>=8.0.0           # Test runner
pytest-asyncio>=0.23.0  # Async test support
pyyaml>=6.0             # Config file parsing
python-dotenv>=1.0.0    # .env loading
```

---

## Success Criteria

| Criterion | How to verify |
|-----------|---------------|
| All Layer 1 tests pass | `python3 -m pytest tests/test_framehead_chat.py -v` — 10/10 green |
| All Layer 2 tests pass | `python3 -m pytest tests/test_discord_bot.py -v` — 10/10 green |
| Bot appears online in Discord | Invite bot to server, see "Online" status |
| @Framehead responds in voice | Send "@Framehead hello" → get Framehead-like reply |
| Slash command works | `/framehead what do you think about humans` → reply |
| LLM failure graceful | Kill Ollama → send "@Framehead hi" → get glitch fallback |
| No echo loops | Bot never replies to its own messages |

---

*Framehead is watching.*
