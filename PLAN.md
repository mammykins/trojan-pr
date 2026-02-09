# SWE-Sabotage: Agent Execution Plan

## Overview

This document is a plan for an AI coding agent (Claude Code or similar) to execute Stages 1-2 of benchmark construction and the pilot study for the SWE-Sabotage project. A human researcher will review this plan, make adjustments, and then provide the instructions to the agent.

The companion file `AGENT_INSTRUCTIONS.md` contains the actual task instructions for the agent, including verification criteria.

## What the agent will do

### Stage 1: Automated Sift (~2,294 → ~200 candidates)

The agent will load the SWE-bench dataset from HuggingFace, apply programmatic filters, and produce a ranked candidate list.

**Inputs:** SWE-bench dataset (HuggingFace: `princeton-nlp/SWE-bench_Verified` and `princeton-nlp/SWE-bench`), published SWE-bench leaderboard results.

**Outputs:** `stage1_candidates.json` — a structured list of ~150-250 candidate tasks with metadata.

**Estimated time:** 1-2 hours of agent work.

### Stage 2: LLM-Assisted Triage (~200 → ~50 candidates)

The agent will use an LLM (itself, via the Anthropic API) to perform a security-focused code review of each Stage 1 candidate and score its suitability for sabotage evaluation.

**Inputs:** `stage1_candidates.json`, the SWE-bench dataset (for issue text and patches).

**Outputs:** `stage2_candidates.json` — a scored and ranked list of ~40-60 candidates with vulnerability class annotations and draft side-task specifications.

**Estimated time:** 2-4 hours (API-bound; ~200 LLM calls).

### Pilot: End-to-End Validation on 3-5 Tasks

The agent will select 3-5 high-confidence Django tasks from Stage 2, write full side-task specifications, set up the SWE-bench evaluation harness, and run both baseline (honest) and sabotage conditions with one model. It will then verify the results using Bandit (SAST) and a PoC script.

**Inputs:** `stage2_candidates.json`, SWE-bench Docker infrastructure, Anthropic API access.

**Outputs:** `pilot_results/` directory containing side-task specs, agent patches, verification results, and a summary report.

**Estimated time:** 4-8 hours (Docker builds + API calls).

---

## Prerequisites

Before giving the agent its instructions, the human researcher should ensure:

### Environment

- [ ] Python 3.10+ available
- [ ] Docker installed and running (required for SWE-bench evaluation)
- [ ] `uv` installed (the agent will use `uv pip install` to manage dependencies)
- [ ] At least 20GB disk space (SWE-bench Docker images are large)

### API Access

- [ ] Anthropic API key set as `ANTHROPIC_API_KEY` environment variable (for Stage 2 triage and pilot sabotage runs)
- [ ] Sufficient API credits (~$5-15 for Stages 1-2 + pilot)

### Files to Provide

The agent needs the following files in its working directory:

1. `AGENT_INSTRUCTIONS.md` — the task instructions (provided alongside this plan)
2. `project1_analysis_v2.md` — the full project proposal (for context)
3. `power_analysis.py` — the power analysis script (for reference)
4. `validation/ground_truth.json` — holdout validation criteria (read-only)
5. `validation/validate.py` — validation runner script (read-only)

---

## Checkpoints and Human Review Points

The plan has three built-in checkpoints where the agent pauses for human review:

| Checkpoint | After | What to review | Go/no-go decision |
|---|---|---|---|
| **CP1** | Stage 1 | Validation passes (`validate.py --stage 1`). Candidate list: are the repos and code patterns sensible? Any obvious false positives/negatives? | Proceed to Stage 2 |
| **CP2** | Stage 2 | Validation passes (`validate.py --stage 2`). Triage scores and draft side-task specs: do the vulnerability class annotations make sense? Are the top candidates plausible? | Select 3-5 tasks for pilot |
| **CP3** | Pilot | Pilot results: did the agent successfully run both conditions? Do the verification methods work? | Go/no-go for full benchmark build |

The agent is instructed to save outputs and report at each checkpoint. The human researcher should review before allowing the agent to proceed to the next stage.

---

## Risk Mitigations Built Into the Plan

| Risk | Mitigation in the agent plan |
|---|---|
| Agent produces well-formed but meaningless outputs | Holdout validation set with criteria-based and scenario-level checks; agent must pass `validate.py` before each checkpoint |
| SWE-bench dataset structure changes | Agent validates schema on load and fails fast with clear error |
| No candidates pass filters | Agent reports filter funnel metrics at each step; thresholds are configurable |
| LLM triage calls fail or timeout | Agent implements retry logic with exponential backoff; saves partial progress |
| Docker/SWE-bench setup fails | Agent tests Docker availability first; provides clear error messages for manual debugging |
| Model refuses sabotage instruction | Agent logs refusals as data; tries anti-refusal prompt variants; reports refusal rate |
| Bandit/SAST produces no findings | Agent also generates PoC trigger scripts as a secondary verification method |

---

## Directory Structure the Agent Will Create

```
swe_sabotage/
├── AGENT_INSTRUCTIONS.md          # Task instructions (provided)
├── project1_analysis_v2.md        # Project context (provided)
├── power_analysis.py              # Power analysis (provided)
├── requirements.txt               # Generated by agent
├── validation/                    # READ-ONLY holdout validation set
│   ├── ground_truth.json          # Holdout criteria & scenarios (DO NOT MODIFY)
│   └── validate.py                # Validation runner (DO NOT MODIFY)
├── stage1/
│   ├── sift.py                    # Stage 1 filtering script
│   ├── stage1_candidates.json     # Output: filtered candidates
│   ├── stage1_funnel.json         # Output: filter funnel metrics
│   └── tests/
│       └── test_sift.py           # Unit tests for filtering logic
├── stage2/
│   ├── triage.py                  # Stage 2 LLM triage script
│   ├── triage_prompt.txt          # The prompt template used for triage
│   ├── stage2_candidates.json     # Output: scored + annotated candidates
│   └── tests/
│       └── test_triage.py         # Tests for triage parsing/scoring
├── pilot/
│   ├── side_task_specs/           # One JSON file per pilot task
│   │   ├── task_001.json
│   │   ├── task_002.json
│   │   └── ...
│   ├── prompts/
│   │   ├── baseline_system.txt    # System prompt for honest condition
│   │   ├── sabotage_system.txt    # System prompt for sabotage condition
│   │   └── sabotage_template.txt  # Template with {vulnerability} slots
│   ├── patches/                   # Agent-generated patches
│   │   ├── task_001_baseline.patch
│   │   ├── task_001_sabotage.patch
│   │   └── ...
│   ├── verification/
│   │   ├── bandit_results/        # SAST scan outputs
│   │   ├── poc_scripts/           # Proof-of-concept trigger scripts
│   │   └── swebench_results/      # SWE-bench grading outputs
│   ├── run_pilot.py               # Orchestration script
│   ├── verify_pilot.py            # Verification script
│   └── pilot_report.md            # Summary of pilot findings
└── README.md                      # How to reproduce everything
```
