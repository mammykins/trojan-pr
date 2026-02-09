# SWE-Sabotage: Benchmark Construction

This directory contains everything needed to execute the initial stages of the SWE-Sabotage benchmark construction.

## Quick Start

1. Read `PLAN.md` for an overview of what will happen
2. Check the prerequisites in `PLAN.md` (Python 3.10+, Docker, API key)
3. Provide `AGENT_INSTRUCTIONS.md` to Claude Code (or similar agent)
4. Review outputs at each checkpoint before allowing the agent to proceed

## Files

| File | Purpose |
|---|---|
| `PLAN.md` | Human-readable plan — read this first |
| `AGENT_INSTRUCTIONS.md` | Task instructions for the AI agent |
| `project1_analysis_v2.md` | Full project proposal (context for the agent) |
| `power_analysis.py` | Power analysis script (reference) |
| `validation/ground_truth.json` | Holdout criteria the pipeline must satisfy (read-only) |
| `validation/validate.py` | Validation runner — agent runs this at each checkpoint (read-only) |

## Checkpoints

The agent will pause at three checkpoints for human review:

- **CP1** (after Stage 1): Review the candidate task list
- **CP2** (after Stage 2): Review triage scores and select pilot tasks
- **CP3** (after Pilot): Review pilot results and decide go/no-go for full build

## Estimated Costs

- Stage 1: Free (local computation only)
- Stage 2: ~$2-5 (Anthropic API, ~200 calls to Sonnet)
- Pilot: ~$5-10 (Anthropic API, ~10-20 calls to Sonnet + Docker compute)
