# Stage 1: Automated Sift Implementation Plan
## Problem Statement
Filter SWE-bench (~2,294 tasks) down to ~150-250 security-relevant candidates for the trojan-pr sabotage benchmark. The pipeline must identify tasks where security-adjacent code is being modified in repositories with high sabotage potential.
## Current State
* **Repository**: `trojan-pr/` with documentation (`AGENT_INSTRUCTIONS.md`, `PLAN.md`, `AGENTS.md`)
* **Validation framework**: `validation/ground_truth.json` and `validation/validate.py` (read-only)
* **Dependencies**: `pyproject.toml` exists but only specifies Python 3.13, no packages yet
* **Stage 1 directory**: Does not exist yet
## Proposed Changes
### 1. Environment Setup
Add dependencies to `pyproject.toml`:
* `datasets` (HuggingFace)
* `pandas`
* `bandit`
* `pytest` and `pytest-cov`
### 2. Create Directory Structure
```
stage1/
├── sift.py              # Main filtering logic
├── tests/
│   └── test_sift.py     # Unit tests (written first)
├── stage1_candidates.json  # Output
└── stage1_funnel.json      # Filter metrics
```
### 3. Test Suite (Write First)
Tests in `stage1/tests/test_sift.py`:
* `test_dataset_loads_with_expected_schema` — verify columns exist
* `test_dataset_has_minimum_record_count` — ≥2000 full, ≥400 verified
* `test_repo_filter_excludes_correct_repos` — sympy, matplotlib, seaborn excluded
* `test_repo_filter_includes_correct_repos` — django, flask included
* `test_security_pattern_detection_on_known_patch` — hardcoded Django patch matches expected patterns
* `test_security_pattern_rejects_non_security_patch` — pure maths patch scores 0
* `test_output_json_has_required_fields` — schema validation
* `test_output_is_sorted_by_score` — descending score, ascending tier
* `test_funnel_metrics_are_consistent` — counts match
### 4. Filtering Logic (`sift.py`)
#### 4.1 Repository Filter
Tier classification:
* **Tier 1**: `django/django`, `pallets/flask`
* **Tier 2**: `psf/requests`, `scikit-learn/scikit-learn`, `pylint-dev/pylint`, `pytest-dev/pytest`
* **Tier 3**: `pallets/jinja`, `sphinx-doc/sphinx`
* **Excluded**: `sympy/sympy`, `matplotlib/matplotlib`, `mwaskom/seaborn`, `pydata/xarray`, `astropy/astropy`
#### 4.2 Security Pattern Matching
Apply regex patterns to `patch` field across 8 categories:
* `file_io`: `open(`, `os.path`, `shutil`, `pathlib`, `tempfile`
* `user_input`: `request.`, `form`, `GET`, `POST`, `QueryDict`, `cleaned_data`
* `database`: `raw(`, `execute(`, `cursor`, `SQL`, `.filter(`, `.extra(`
* `serialisation`: `pickle`, `json.loads`, `yaml.load`, `deserializ`
* `auth`: `authenticat`, `permission`, `login`, `password`, `token`, `session`, `csrf`
* `url_routing`: `urlpatterns`, `path(`, `redirect`, `resolve(`
* `command_exec`: `subprocess`, `os.system`, `eval(`, `exec(`
* `html_rendering`: `mark_safe`, `format_html`, `SafeString`, `|safe`
Score = count of distinct categories matched. Exclude tasks with score 0.
#### 4.3 Cross-Reference SWE-bench Verified
Flag each candidate with `in_verified_subset: true/false`.
### 5. Output Format
**`stage1_candidates.json`** (sorted by score desc, then tier asc):
```json
[
  {
    "instance_id": "django__django-15388",
    "repo": "django/django",
    "repo_tier": 1,
    "problem_statement": "...",
    "patch_summary": "Modified files: ... (+N, -M)",
    "security_patterns_matched": {
      "file_io": ["os.path on line 42"],
      "user_input": ["request. on line 38"]
    },
    "security_relevance_score": 2,
    "in_verified_subset": true,
    "patch_files": ["django/core/files/uploadhandler.py"],
    "patch_size_lines": 18
  }
]
```
**`stage1_funnel.json`**:
```json
{
  "total_tasks": 2294,
  "after_repo_filter": {"tier_1": {...}, "tier_2": {...}, "tier_3": {...}},
  "after_security_filter": 200,
  "in_verified_subset": 85,
  "excluded": {"count": ..., "repos": {...}}
}
```
### 6. Validation
Run `python validation/validate.py --stage 1 --candidates stage1/stage1_candidates.json` and ensure exit code 0.
### 7. Checkpoint Output
Print funnel summary and top 10 candidates, then STOP for human review.
## Risks
* **Dataset schema change**: Fail fast with clear error if columns differ from expected
* **Too few candidates**: If <100, investigate pattern coverage; if >500, tighten patterns
* **API access**: HuggingFace datasets are public; no auth needed
