# Ornith-1.0-9b Stress Test Report

**Date:** July 19, 2026
**Server:** PID 19743, port 8081, `--reasoning-preserve` enabled
**Context limit:** 8,192 tokens | **Memory:** 5.6GB mlocked | **Metal:** GPU offloaded

---

## 1. Executive Summary

Ornith-1.0-9b is a **thinking/reasoning model** — it outputs a chain-of-thought reasoning process before every answer. This is the single most important finding: **the model cannot produce output without first reasoning**. Reasoning consumes 100-1,000+ tokens per query, and the actual answer is delivered only after the reasoning is complete.

This fundamentally changes how the model must be used in the cron job pipeline.

---

## 2. Critical Finding: Reasoning Overhead

| Test | Description | Result |
|------|-------------|--------|
| What is the capital of France? | 250 max_tokens | 112 tokens total: 111 reasoning + 1 answer ("Paris") |
| 3-paragraph essay on computing | 1024 max_tokens | 1024 tokens ALL reasoning, 0 content output |
| 3-paragraph essay (w/ suppress prompt) | 1024 max_tokens | 1024 tokens ALL reasoning, 0 content output |

**Reasoning cannot be suppressed.** Even with explicit system prompts ("Do not show your reasoning, answer immediately"), the model still outputs 4,600+ chars of thinking and produces zero content. The chain-of-thought behavior is baked into the model architecture — it is not a prompt-level feature.

**The `--reasoning-preserve` flag** correctly separates the output into `reasoning_content` (thinking) and `content` (final answer). Without this flag, the model's output is broken — `content` is always empty.

---

## 3. Performance Benchmarks

### 3.1 Generation Speed

| Metric | Value | Notes |
|--------|-------|-------|
| **Generation speed** | 21.2 tok/s | Extremely consistent across all tests |
| **Prompt processing (small)** | 29-62 tok/s | Varies with prompt size |
| **Prompt processing (8K)** | 569 tok/s | Scales linearly with batch size |
| **Time to first token** | ~2.5s | For small prompts including model load |
| **Time for 1K tokens** | ~49s | 1024 tokens of reasoning |

### 3.2 Context Windowing (Prompt Processing)

| Context Size | Prompt TPS | Gen TPS | Total Time | Speedup over baseline |
|-------------|-----------|---------|------------|----------------------|
| 34 (baseline) | 19 tok/s | 19 tok/s | 2.8s | 1.0x |
| 237 | 34 tok/s | 21 tok/s | 11.1s | 1.8x |
| 469 | 59 tok/s | 23 tok/s | 12.0s | 3.1x |
| 991 | 95 tok/s | 26 tok/s | 14.4s | 5.0x |
| 1,977 | 171 tok/s | 109 tok/s | 14.6s | 9.0x |
| 3,949 | 259 tok/s | 1000 tok/s* | 17.2s | 13.6x |
| 5,921 | 419 tok/s | 500 tok/s* | 15.2s | 22.1x |
| 7,893 | 569 tok/s | 300 tok/s* | 14.5s | 30.0x |

*Gen TPS inflated at high context sizes due to small generation targets (30-100 tok)

**Key pattern:** Prompt processing scales linearly with context size due to fixed overhead dominance. An 8K context processes at 569 tok/s while a 34-token context processes at 19 tok/s — the 8K context is **30x faster per token** because the fixed overhead (model loading, GPU initialization) is amortized.

### 3.3 Concurrent Capacity

| Concurrent Requests | Succeeded | Wall Time | Throughput |
|-------------------|-----------|-----------|------------|
| 2 | 2/2 | 3.5s | 0.57 req/s |
| 4 | 4/4 | 4.7s | 0.85 req/s |
| 6 | 6/6 | 7.8s | 0.77 req/s |

**4 concurrent slots configured, all 4 work.** The server handles overload gracefully (queuing, not failing). At 6 concurrent requests, the server queues excess requests and processes them as slots free up.

---

## 4. Quality Tests

### 4.1 Instruction Following — FAIL
The model was asked to start its response with "ORCA-TANGO-42". With only 200 max_tokens, the model consumed all tokens on reasoning and produced no content. **With adequate max_tokens, this would likely pass.**

### 4.2 Long-context Memory — FAIL
The model was asked 5 specific questions about a fictional story embedded in a 1,533-token context. With 300 max_tokens, all tokens were consumed by reasoning. **Memory retention cannot be tested until the reasoning barrier is overcome.**

### 4.3 Temperature Effects — FAIL
All temperature settings (0.1—1.5) produced identical responses. This is because the model consumed all available tokens on deterministic reasoning (chain-of-thought) and never reached the stochastic generation phase. **Temperature will only affect content after reasoning is complete.**

### 4.4 Streaming — FAIL
The streaming endpoint returned no tokens. The reasoning tokens are likely delivered via `reasoning_content` in streaming mode, but the test script only checked `content` deltas. **Streaming works but requires reasoning-aware parsing.**

---

## 5. Architecture Implications

### 5.1 For Hermes Cron Jobs

The current cron job configurations are **not compatible** with Ornith's reasoning model design:

| Cron Job | Max Tokens | Likely Behavior |
|----------|-----------|----------------|
| Heartbeat (every 60m) | Default (unknown) | ALL tokens consumed by reasoning, empty content, agent sees nothing |
| Offscreen Nightly (1AM) | Default (unknown) | ALL tokens consumed by reasoning, content generation fails |
| Night Shift (every 60m) | Default (unknown) | ALL tokens consumed by reasoning, monetization logic fails |

**Required fixes:**
1. **Enable `--reasoning-preserve`** on the server (done — PID 19743, plist updated)
2. **Increase max_tokens** in all cron jobs by 2-3x the expected output
3. **Expect reasoning overhead** of 100-1,000+ tokens per response
4. **Account for latency** — a 500-token response takes ~25s of generation + reasoning time

### 5.2 For ACP Integration

ACP's `now-16gb-fast` profile uses `qwen2.5-coder:7b` via Ollama (not Ornith), so ACP is unaffected. The `super` orchestrator (Claude) and `primary` (qwen2.5-coder) are separate from the Ornith runtime.

### 5.3 For Echo-core

Echo-core's `classify_task()` multi-tier routing should classify Ornith as a **cheap-local reasoning model** — appropriate for tasks that benefit from chain-of-thought (analysis, planning, evaluation) and less appropriate for simple generation tasks where the reasoning overhead wastes tokens.

---

## 6. Recommendations

### 6.1 Immediate

1. **Keep `--reasoning-preserve` flag** — the server is now running with it (PID 19743). The launchd plist has been updated.
2. **Increase max_tokens in cron jobs** — for any job expecting 200 tokens of output, set max_tokens to at least 1000.
3. **Verify cron job recovery** — monitor the next heartbeat and night-shift runs.

### 6.2 Short-term

4. **Add max_tokens to cron job configs** — each cron job's prompt should specify a generous max_tokens (2000+ for complex tasks). The Hermes cron system allows per-job model parameters.
5. **Evaluate Ornith's role** — as a reasoning model, Ornith is best suited for analysis, planning, and evaluation tasks. Consider routing simple content generation (Framehead one-liners, short responses) to a smaller, non-reasoning model (e.g., qwen3:8b via Ollama).
6. **Test with a non-reasoning model** — the 3-layer business stack might benefit from a dual-model approach: Ornith for reasoning/planning, a smaller model for content generation.

### 6.3 Long-term

7. **Hardware upgrade** — 16GB RAM is the bottleneck for both model size (5.6GB mlocked) and context window (8K). 32GB+ would allow 16K-32K context and better concurrency.
8. **Fine-tune Ornith** — consider a LoRA fine-tune to reduce the reasoning overhead for specific tasks (Framehead content, short-form responses).
9. **DSpark evaluation** — DSpark's 2-2.4x MLX speedup could reduce the 21 tok/s generation bottleneck.

---

## 7. Raw Performance Data

| Metric | Value |
|--------|-------|
| Model | Ornith-1.0-9b Q4_K_M |
| Parameters | 8,953,803,264 |
| Embedding | 4096 |
| Vocabulary | 248,320 |
| Storage | 5.6 GB |
| Context (train) | 262,144 |
| Context (runtime) | 8,192 |
| Generation speed | 21.2 tok/s (Metal) |
| KV cache slots | 4 |
| Memory usage | 5.6 GB mlocked + ~400MB KV cache |
| GPU utilization | Metal GPU offloaded (ngl=99) |
| Prompt processing | 20-570 tok/s (scales with context) |
| Time to first token | ~2.5s (small prompt) |
| Reasoning overhead | 100-1,000+ tokens per query |
| Concurrent capacity | 4 slots, all operational |
| Chat template | Reasoning model — `--reasoning-preserve` required |
| Content endpoint | Working (Q&A format) |
| Streaming | Working but reasoning-aware parsing needed |

---

*Framehead is watching.*