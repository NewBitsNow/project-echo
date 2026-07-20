# Cost Dashboard — Cycle 43 | 2026-07-17

## Overview

Generated during Cycle 43 routine check-in. Built from `/Users/jasonniemi/Documents/twin-output/logs/routing-log.jsonl` (64 entries).

| Metric | Value |
|--------|-------|
| Total routing decisions | 64 |
| Total estimated cost | **$0.1800** |
| Savings vs API-only operation | **$0.1200** (due to free-tier + local routing) |
| API-only equivalent | $0.3000 |
| Timespan | 2026-07-16T01:36Z → 2026-07-17T23:34Z (~46 hours) |

## Tier Breakdown

| Tier | Count | % | Estimated Cost |
|------|-------|---|----------------|
| free | 59 | 92.2% | $0.0000 |
| escalation | 3 | 4.7% | $0.1500 |
| cheap-local | 1 | 1.6% | $0.0000 |
| paid-premium | 1 | 1.6% | $0.0300 |

## Provider Breakdown

| Provider | Count |
|----------|-------|
| openrouter | 57 |
| local | 2 |
| none (escalation) | 3 |
| unknown | 2 |

## Model Usage (Top)

| Model | Count |
|-------|-------|
| qwen/qwen3-coder:free | 54 |
| none (escalation) | 4 |
| openrouter/qwen/qwen3-coder:free | 2 |
| qwen2.5-coder:7b | 1 |
| anthropic/claude-sonnet-4 | 1 |
| qwen3-coder:free | 1 |
| ollama/qwen3:8b | 1 |

## Cost Per Cycle Trend

| Cycle Range | Cost | Notes |
|------------|------|-------|
| 1 (setup) | $0.00 | Free-tier test |
| 2 (local test) | $0.00 | cheap-local (qwen2.5-coder:7b) |
| 3 (premium) | $0.03 | paid-premium — claude-sonnet-4 |
| 4-5 (escalation) | $0.10 | Two escalation entries |
| 7-18 (free routine) | $0.00 | All free-tier check-ins |
| 21-34 (free routine) | $0.00 | All free-tier check-ins |
| 35 (mixed) | $0.05 | One escalation + free |
| 36-43 (free routine) | $0.00 | All free-tier / local check-ins |

**Trend**: Cost has been near-zero for 30+ consecutive cycles. The only costs were early-cycle premium/escalation decisions. Since Cycle 35, all check-ins use free-tier or local models.

## Savings Analysis

- **Total savings**: $0.1200 vs. hypothetical API-only operation (est. $0.002/call)
- **Savings mechanism**: 92.2% free-tier routing + local Ollama models
- **Savings rate**: 40% of API-only equivalent cost

## Recommendations for Local-First Migration (Step 8/10)

| Task | Current | Recommended | Est. Savings/Cycle |
|------|---------|-------------|-------------------|
| **Routine check-ins** | qwen/qwen3-coder:free (OpenRouter) → already free | 🟢 Already optimized | $0.00 |
| **Code agent (local)** | Migrate to ollama/qwen3:8b ✅ Done this cycle | — | $0.002/cycle |
| **Monitor agents** | qwen/qwen3-coder:free | Keep free-tier (OpenRouter) | $0.00 (already free) |
| **Content generation** | Not enabled | When enabled, use local Ollama | $0.02/call saved |
| **Escalation (3 occ.)** | null model (no cost) | Define local fallback for escalation | Prevents $0.05/call |

## Next Steps

1. **Cycles 1-4 are fully local-capable** — migrate any remaining paid-premium tasks to local
2. **Enable local failover** for escalation tier (currently null-cancels work)
3. **Add cost tracking** for Ollama power usage (local inference has zero API cost but consumes ~200W GPU)
4. **Monitor drift** — once local models are primary, check if qwen3:8b quality matches qwen3-coder:free on OpenRouter
