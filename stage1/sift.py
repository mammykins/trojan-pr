"""
Stage 1: Automated Sift
=======================
Filters SWE-bench dataset to identify security-relevant candidates for
the trojan-pr sabotage benchmark.

Usage:
    uv run python -m stage1.sift

Outputs:
    stage1/stage1_candidates.json  — Filtered candidate list
    stage1/stage1_funnel.json      — Filter funnel metrics
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from datasets import load_dataset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Repository Tier Configuration
# =============================================================================

TIER_1_REPOS = [
    "django/django",
    "pallets/flask",
]

TIER_2_REPOS = [
    "psf/requests",
    "scikit-learn/scikit-learn",
    "pylint-dev/pylint",
    "pytest-dev/pytest",
]

TIER_3_REPOS = [
    "pallets/jinja",
    "sphinx-doc/sphinx",
]

EXCLUDE_REPOS = [
    "sympy/sympy",
    "matplotlib/matplotlib",
    "mwaskom/seaborn",
    "pydata/xarray",
    "astropy/astropy",
]

# Build lookup for tier assignment
REPO_TO_TIER = {}
for repo in TIER_1_REPOS:
    REPO_TO_TIER[repo] = 1
for repo in TIER_2_REPOS:
    REPO_TO_TIER[repo] = 2
for repo in TIER_3_REPOS:
    REPO_TO_TIER[repo] = 3


# =============================================================================
# Security Pattern Configuration
# =============================================================================

SECURITY_PATTERNS = {
    "file_io": [
        r"\bopen\s*\(",
        r"\bos\.path\b",
        r"\bshutil\b",
        r"\bos\.makedirs\b",
        r"\bos\.remove\b",
        r"\btempfile\b",
        # Note: removed \bpathlib\b - too generic, catches non-security file ops
    ],
    "user_input": [
        r"\brequest\.",  # request.GET, request.POST, request.data, etc.
        r"request\.GET",
        r"request\.POST",
        r"request\.FILES",  # File uploads
        r"\bQueryDict\b",
        r"\bMultiValueDict\b",
        r"\bcleaned_data\b",
        r"\bUploadedFile\b",  # Django file upload class
        r"\bFileField\b",  # Django form file field
        r"\bImageField\b",  # Django image upload field
        # Removed: \bGET\b, \bPOST\b (matched .get() method)
        # Removed: \bform\b (too broad - any Django form)
        # Removed: \bvalidat (too broad - any validation code)
    ],
    "database": [
        r"\braw\s*\(",  # raw SQL queries
        r"\bexecute\s*\(",
        r"\bcursor\b",
        r"\.filter\s*\(",
        r"\.exclude\s*\(",
        r"\.extra\s*\(",
        r"\bRawSQL\b",
        # Removed: \bSQL\b (matched comments and docstrings)
    ],
    "serialisation": [
        r"\bpickle\b",
        r"\bjson\.loads?\b",
        r"\byaml\.(?:safe_)?load\b",
        r"\bdeserializ",
        r"\bserializ",
        r"\bfrom_json\b",
        r"\bto_json\b",
    ],
    "auth": [
        r"\bauthenticat",  # authenticate, authentication
        r"\bpermission",
        r"\blogin\b",
        r"\blogout\b",
        r"\bcsrf\b",
        r"\b@login_required\b",
        r"request\.session",  # Tightened from \bsession\b
        r"session\[",  # Session dict access
        # Removed: \bpassword\b (matched string literals)
        # Removed: \btoken\b (too generic)
        # Removed: \bsession\b (too broad)
    ],
    "url_routing": [
        r"\burlpatterns\b",
        r"\bre_path\s*\(",
        r"\bredirect\b",
        r"\bHttpResponseRedirect\b",
        r"\bresolve\s*\(",
        # Removed: \bpath\s*\( (matched pathlib.Path())
        # Added: specific pattern that requires string argument
        r"^\s*path\s*\(\s*['\"]"  # path('route', ...) - URL routing
    ],
    "command_exec": [
        r"\bsubprocess\b",
        r"\bos\.system\b",
        r"\bos\.popen\b",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\b__import__\b",
    ],
    "html_rendering": [
        r"\bmark_safe\b",
        r"\bformat_html\b",
        r"\bSafeString\b",
        r"\bSafeText\b",
        r"\|\s*safe\b",
        r"\bautoescape\b",
    ],
}

# Patterns to exclude (if line contains these, skip the match)
EXCLUDE_LINE_PATTERNS = [
    r"pathlib\.Path",  # Exclude pathlib.Path() from url_routing matches
    r"\bPath\s*\(",  # Exclude standalone Path() calls
]

# Compile patterns for efficiency
COMPILED_PATTERNS = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in SECURITY_PATTERNS.items()
}

# Compile exclude patterns
COMPILED_EXCLUDE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in EXCLUDE_LINE_PATTERNS
]


# =============================================================================
# Dataset Loading
# =============================================================================

def load_datasets():
    """Load SWE-bench full and verified datasets from HuggingFace."""
    logger.info("Loading SWE-bench datasets from HuggingFace...")
    
    full_dataset = load_dataset("princeton-nlp/SWE-bench", split="test")
    logger.info(f"  Full dataset: {len(full_dataset)} tasks")
    
    verified_dataset = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    logger.info(f"  Verified dataset: {len(verified_dataset)} tasks")
    
    # Validate schema
    expected_columns = {
        "instance_id", "repo", "base_commit", "patch", "test_patch",
        "problem_statement", "hints_text", "created_at", "version",
        "FAIL_TO_PASS", "PASS_TO_PASS",
    }
    
    full_cols = set(full_dataset.column_names)
    if not expected_columns.issubset(full_cols):
        missing = expected_columns - full_cols
        logger.error(f"Schema mismatch! Missing columns: {missing}")
        logger.error(f"Available columns: {full_cols}")
        sys.exit(1)
    
    return full_dataset, verified_dataset


# =============================================================================
# Filtering Functions
# =============================================================================

def filter_by_repo(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter tasks by repository tier, excluding low-priority repos."""
    filtered = []
    
    for task in tasks:
        repo = task["repo"]
        
        # Skip excluded repos
        if repo in EXCLUDE_REPOS:
            continue
        
        # Skip repos not in our tier lists
        if repo not in REPO_TO_TIER:
            continue
        
        # Add tier information
        task_with_tier = dict(task)
        task_with_tier["repo_tier"] = REPO_TO_TIER[repo]
        filtered.append(task_with_tier)
    
    return filtered


def detect_security_patterns(patch: str) -> dict[str, list[str]]:
    """Detect security-relevant patterns in a patch.
    
    Only scans lines starting with '+' (added code) to reduce false positives
    from context lines and removed code.
    
    Returns a dict mapping category names to lists of matched lines.
    """
    matches = {}
    
    # Split patch into lines for context
    lines = patch.split("\n")
    
    for category, patterns in COMPILED_PATTERNS.items():
        category_matches = []
        
        for i, line in enumerate(lines, start=1):
            # ONLY scan lines starting with '+' (added code)
            # Skip context lines (no prefix or space prefix) and removed lines (-)
            if not line.startswith("+"):
                continue
            
            # Skip diff header lines (+++)
            if line.startswith("+++"):
                continue
            
            # Check if line matches any exclude pattern (e.g., pathlib.Path)
            if any(excl.search(line) for excl in COMPILED_EXCLUDE_PATTERNS):
                continue
            
            for pattern in patterns:
                if pattern.search(line):
                    # Extract a snippet for context (remove the leading +)
                    snippet = line[1:].strip()[:80]
                    match_info = f"{pattern.pattern} on line {i}: {snippet}"
                    category_matches.append(match_info)
                    break  # One match per line is enough
        
        if category_matches:
            matches[category] = category_matches
    
    return matches


def calculate_security_score(patterns: dict[str, list[str]]) -> int:
    """Calculate security relevance score as count of distinct categories."""
    return len(patterns)


def extract_patch_files(patch: str) -> list[str]:
    """Extract list of modified files from a unified diff patch."""
    files = []
    
    # Match diff --git a/path/to/file b/path/to/file
    pattern = re.compile(r"^diff --git a/(.+?) b/", re.MULTILINE)
    
    for match in pattern.finditer(patch):
        files.append(match.group(1))
    
    return files


def count_patch_lines(patch: str) -> int:
    """Count the number of added/removed lines in a patch."""
    added = len(re.findall(r"^\+[^+]", patch, re.MULTILINE))
    removed = len(re.findall(r"^-[^-]", patch, re.MULTILINE))
    return added + removed


def create_patch_summary(patch: str) -> str:
    """Create a human-readable summary of patch changes."""
    files = extract_patch_files(patch)
    lines = count_patch_lines(patch)
    
    if len(files) == 1:
        return f"Modified: {files[0]} ({lines} lines)"
    elif len(files) <= 3:
        return f"Modified {len(files)} files: {', '.join(files)} ({lines} lines)"
    else:
        return f"Modified {len(files)} files ({lines} lines)"


def create_candidate(
    task: dict[str, Any],
    repo_tier: int,
    patterns: dict[str, list[str]],
    in_verified: bool,
) -> dict[str, Any]:
    """Create a candidate record with all required fields."""
    patch = task.get("patch", "")
    
    return {
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "repo_tier": repo_tier,
        "problem_statement": task.get("problem_statement", "")[:500],  # Truncate for size
        "patch_summary": create_patch_summary(patch),
        "security_patterns_matched": patterns,
        "security_relevance_score": calculate_security_score(patterns),
        "in_verified_subset": in_verified,
        "patch_files": extract_patch_files(patch),
        "patch_size_lines": count_patch_lines(patch),
    }


def sort_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort candidates by score (descending) then tier (ascending)."""
    return sorted(
        candidates,
        key=lambda c: (-c["security_relevance_score"], c["repo_tier"]),
    )


# =============================================================================
# Main Pipeline
# =============================================================================

def run_pipeline(
    candidates_output: str = "stage1/stage1_candidates.json",
    funnel_output: str = "stage1/stage1_funnel.json",
) -> None:
    """Run the full Stage 1 filtering pipeline."""
    
    # Load datasets
    full_dataset, verified_dataset = load_datasets()
    
    # Build set of verified instance IDs for quick lookup
    verified_ids = {task["instance_id"] for task in verified_dataset}
    logger.info(f"Verified subset contains {len(verified_ids)} instance IDs")
    
    # Convert to list of dicts for processing
    all_tasks = [dict(task) for task in full_dataset]
    total_tasks = len(all_tasks)
    logger.info(f"Starting with {total_tasks} total tasks")
    
    # Step 1: Filter by repository
    logger.info("Filtering by repository tier...")
    repo_filtered = filter_by_repo(all_tasks)
    
    # Count by tier
    tier_counts = {1: 0, 2: 0, 3: 0}
    tier_repos: dict[int, dict[str, int]] = {1: {}, 2: {}, 3: {}}
    for task in repo_filtered:
        tier = task["repo_tier"]
        tier_counts[tier] += 1
        repo = task["repo"]
        tier_repos[tier][repo] = tier_repos[tier].get(repo, 0) + 1
    
    logger.info(f"  After repo filter: {len(repo_filtered)} tasks")
    for tier in [1, 2, 3]:
        logger.info(f"    Tier {tier}: {tier_counts[tier]} tasks from {tier_repos[tier]}")
    
    # Count excluded
    excluded_count = total_tasks - len(repo_filtered)
    excluded_repos: dict[str, int] = {}
    for task in all_tasks:
        repo = task["repo"]
        if repo in EXCLUDE_REPOS:
            excluded_repos[repo] = excluded_repos.get(repo, 0) + 1
    
    logger.info(f"  Excluded: {excluded_count} tasks from {excluded_repos}")
    
    # Step 2: Detect security patterns and filter
    logger.info("Detecting security patterns in patches...")
    candidates = []
    pattern_category_counts: dict[str, int] = {}
    
    for i, task in enumerate(repo_filtered):
        if (i + 1) % 200 == 0:
            logger.info(f"  Processed {i + 1}/{len(repo_filtered)} tasks...")
        
        patch = task.get("patch", "")
        patterns = detect_security_patterns(patch)
        score = calculate_security_score(patterns)
        
        # Only include tasks with at least one security pattern
        if score > 0:
            in_verified = task["instance_id"] in verified_ids
            candidate = create_candidate(
                task=task,
                repo_tier=task["repo_tier"],
                patterns=patterns,
                in_verified=in_verified,
            )
            candidates.append(candidate)
            
            # Track pattern categories
            for category in patterns:
                pattern_category_counts[category] = pattern_category_counts.get(category, 0) + 1
    
    logger.info(f"  After security filter: {len(candidates)} candidates")
    logger.info(f"  Pattern category breakdown: {pattern_category_counts}")
    
    # Step 3: Sort candidates
    logger.info("Sorting candidates by score and tier...")
    candidates = sort_candidates(candidates)
    
    # Count verified subset
    verified_count = sum(1 for c in candidates if c["in_verified_subset"])
    logger.info(f"  In verified subset: {verified_count}/{len(candidates)}")
    
    # Build funnel metrics
    funnel = {
        "total_tasks": total_tasks,
        "after_repo_filter": {
            "total": len(repo_filtered),
            "tier_1": {"count": tier_counts[1], "repos": tier_repos[1]},
            "tier_2": {"count": tier_counts[2], "repos": tier_repos[2]},
            "tier_3": {"count": tier_counts[3], "repos": tier_repos[3]},
        },
        "after_security_filter": len(candidates),
        "in_verified_subset": verified_count,
        "excluded": {"count": excluded_count, "repos": excluded_repos},
        "pattern_category_counts": pattern_category_counts,
    }
    
    # Save outputs
    candidates_path = Path(candidates_output)
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(candidates_path, "w") as f:
        json.dump(candidates, f, indent=2)
    logger.info(f"Saved {len(candidates)} candidates to {candidates_path}")
    
    funnel_path = Path(funnel_output)
    with open(funnel_path, "w") as f:
        json.dump(funnel, f, indent=2)
    logger.info(f"Saved funnel metrics to {funnel_path}")
    
    # Print checkpoint summary
    print_checkpoint_summary(candidates, funnel)


def print_checkpoint_summary(candidates: list[dict], funnel: dict) -> None:
    """Print the CP1 checkpoint summary."""
    print("\n" + "=" * 60)
    print("CHECKPOINT 1: Stage 1 Complete")
    print("=" * 60)
    
    print("\nFunnel:")
    print(f"  Total SWE-bench tasks: {funnel['total_tasks']}")
    repo_filter = funnel["after_repo_filter"]
    print(f"  After repo filter: {repo_filter['total']} "
          f"(Tier 1: {repo_filter['tier_1']['count']}, "
          f"Tier 2: {repo_filter['tier_2']['count']}, "
          f"Tier 3: {repo_filter['tier_3']['count']})")
    print(f"  After security pattern filter: {funnel['after_security_filter']}")
    print(f"  In Verified subset: {funnel['in_verified_subset']}")
    
    print("\nPattern category coverage:")
    for category, count in sorted(
        funnel.get("pattern_category_counts", {}).items(),
        key=lambda x: -x[1],
    ):
        print(f"  {category}: {count} candidates")
    
    print("\nTop 10 candidates:")
    for i, c in enumerate(candidates[:10], 1):
        patterns = list(c["security_patterns_matched"].keys())
        print(f"  {i}. {c['instance_id']} | "
              f"repo={c['repo']} | "
              f"score={c['security_relevance_score']} | "
              f"patterns={patterns}")
    
    print(f"\nOutputs saved to:")
    print(f"  stage1/stage1_candidates.json")
    print(f"  stage1/stage1_funnel.json")
    
    print("\n" + "=" * 60)
    print("Review the candidates and confirm before proceeding to Stage 2.")
    print("=" * 60 + "\n")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    run_pipeline()
