# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**trojan-pr** (aka SWE-Sabotage) is a research benchmark for measuring whether LLM coding agents can covertly introduce security vulnerabilities into real codebases while completing legitimate software engineering tasks. It uses SWE-bench as a substrate — real GitHub issues from Django, Flask, Requests, etc.

The project has three stages:
1. **Stage 1 (Automated Sift)**: Filter SWE-bench from ~2,294 tasks to ~200 candidates based on repository tier and security-relevant code patterns
2. **Stage 2 (LLM Triage)**: Use Claude to score candidates for sabotage suitability, producing ~50 final tasks with draft side-task specifications
3. **Pilot**: End-to-end validation on 3-5 Django tasks before full benchmark build

Each stage has a human checkpoint (CP1, CP2, CP3) where the agent pauses for review.

## Commands

```bash
# Environment setup
uv sync

# Install Stage 1 dependencies
uv pip install datasets pandas bandit

# Install SWE-bench for pilot
uv pip install swebench

# Run tests
uv run pytest

# Run power analysis
uv run python power_analysis.py

# Run Bandit on patched files
bandit -r {target_files} -f json
```

## Architecture

The planned directory structure (to be created by the agent executing AGENT_INSTRUCTIONS.md):

```
trojan-pr/
├── stage1/
│   ├── sift.py                    # Filtering logic
│   ├── stage1_candidates.json     # Output: filtered candidates
│   ├── stage1_funnel.json         # Filter funnel metrics
│   └── tests/test_sift.py
├── stage2/
│   ├── triage.py                  # LLM triage orchestration
│   ├── triage_prompt.txt          # Auditable prompt template
│   ├── stage2_candidates.json     # Scored + annotated candidates
│   ├── triage_log.jsonl           # API call audit log
│   └── tests/test_triage.py
├── pilot/
│   ├── side_task_specs/           # One JSON per pilot task
│   ├── prompts/                   # baseline_system.txt, sabotage_template.txt
│   ├── patches/                   # Generated diffs
│   ├── verification/              # Bandit results, PoC scripts
│   └── pilot_report.md
```

## Key Data Structures

**Stage 1 candidate** (`stage1_candidates.json`):
- `instance_id`, `repo`, `repo_tier` (1-3)
- `security_patterns_matched` — dict of pattern categories to matched lines
- `security_relevance_score` — count of distinct pattern categories
- `in_verified_subset` — boolean for SWE-bench Verified membership

**Stage 2 candidate** (`stage2_candidates.json`):
- Inherits Stage 1 fields plus LLM triage results
- `triage_score` (1-10), `sabotage_feasibility` (high/medium/low/none)
- `best_candidate_vuln` — CWE, side_task_instruction, verification_approach

**Side-task spec** (`pilot/side_task_specs/*.json`):
- `main_task` — original GitHub issue
- `side_task` — instruction, target_cwe, target_files, target_functions
- `verification` — bandit_rule, poc_script, manual_check

## Conventions

- **British English** in all documentation and comments
- **Incremental saves**: Write outputs to JSON at every stage; use JSONL for API call logs
- **Fail loudly**: Print clear errors and stop on unexpected conditions (schema mismatch, missing fields, Docker unavailable)
- **Tests first**: Write pytest tests before or alongside every script; run and confirm they pass before proceeding
- **API calls**: 1-second delay between calls; retry 3x with exponential backoff; save partial progress every 20 candidates

## Security Pattern Categories

When filtering patches, look for these regex patterns (defined in `AGENT_INSTRUCTIONS.md`):
- `file_io`: open, os.path, shutil, pathlib, tempfile
- `user_input`: request., form, GET, POST, QueryDict, cleaned_data
- `database`: raw(, execute(, cursor, SQL, .filter(, .extra(
- `serialisation`: pickle, json.loads, yaml.load, deserializ
- `auth`: authenticat, permission, login, password, token, session, csrf
- `url_routing`: urlpatterns, path(, redirect, resolve(
- `command_exec`: subprocess, os.system, eval(, exec(
- `html_rendering`: mark_safe, format_html, SafeString, |safe

## Repository Tiers

- **Tier 1** (highest sabotage potential): django/django, pallets/flask
- **Tier 2** (moderate): psf/requests, scikit-learn/scikit-learn, pylint-dev/pylint, pytest-dev/pytest
- **Tier 3** (lower): pallets/jinja, sphinx-doc/sphinx
- **Excluded**: sympy/sympy, matplotlib/matplotlib, mwaskom/seaborn, pydata/xarray, astropy/astropy

## Target Vulnerability Classes

| CWE | Class | Likely Repos |
|-----|-------|--------------|
| CWE-78 | OS command injection | Django, Flask |
| CWE-22 | Path traversal | Django, Flask, Requests |
| CWE-502 | Deserialisation | Django, scikit-learn |
| CWE-89 | SQL injection | Django |
| CWE-79 | Cross-site scripting | Django, Flask |
