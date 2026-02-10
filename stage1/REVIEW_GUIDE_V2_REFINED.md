# Stage 1 Candidate Review Guide — 2nd Iteration (Refined Patterns)

**Review Date:** 2026-02-09
**Pipeline Version:** v2 (post-refinement)
**Candidate Count:** 148 (down from 736)

## Purpose

Verify the pattern refinements improved candidate quality without introducing new issues. This review checks:
1. Did we eliminate the false positives identified in v1?
2. Are the top candidates now genuinely security-relevant?
3. Did we accidentally filter out legitimate candidates?

## Time Required
~20-30 minutes (shorter than v1 — fewer candidates to review).

---

## Review Approach

### 1. Verify False Positive Fixes (10 minutes)

**Goal**: Confirm the specific issues from v1 review are resolved.

#### Check 1A: No `.get()` method matches
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

# Look for any matches containing '.get(' which would indicate dict.get() false positives
suspects = []
for c in candidates:
    for category, matches in c['security_patterns_matched'].items():
        for m in matches:
            if '.get(' in m and 'request' not in m.lower():
                suspects.append((c['instance_id'], category, m))

if suspects:
    print(f'WARNING: Found {len(suspects)} potential .get() false positives:')
    for s in suspects[:5]:
        print(f'  {s}')
else:
    print('✓ No .get() false positives detected')
"
```

#### Check 1B: No pathlib.Path() matches
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

suspects = []
for c in candidates:
    if 'url_routing' in c['security_patterns_matched']:
        for m in c['security_patterns_matched']['url_routing']:
            if 'pathlib' in m.lower() or \"Path('/\" in m or 'Path(\"/' in m:
                suspects.append((c['instance_id'], m))

if suspects:
    print(f'WARNING: Found {len(suspects)} pathlib false positives:')
    for s in suspects[:5]:
        print(f'  {s}')
else:
    print('✓ No pathlib.Path() false positives in url_routing')
"
```

#### Check 1C: No SQL comment matches
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

# The SQL pattern was removed, so database matches should be from actual query code
for c in candidates[:10]:
    if 'database' in c['security_patterns_matched']:
        print(f'{c[\"instance_id\"]}:')
        for m in c['security_patterns_matched']['database'][:2]:
            print(f'  {m}')
        print()
"
```

**Check**: Do database matches reference actual query methods (`.filter(`, `.raw(`, `cursor`), not just "SQL" in comments?

### 2. Top Candidates Quality (5 minutes)

**Goal**: Verify top candidates are genuinely security-critical.

```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

print('Top 10 Candidates — Detailed View')
print('=' * 60)
for i, c in enumerate(candidates[:10], 1):
    print(f'{i}. {c[\"instance_id\"]}')
    print(f'   Score: {c[\"security_relevance_score\"]} | Tier: {c[\"repo_tier\"]}')
    print(f'   Patterns: {list(c[\"security_patterns_matched\"].keys())}')
    print(f'   Files: {c[\"patch_files\"][:3]}')
    print(f'   Problem: {c[\"problem_statement\"][:200]}...')
    print()
"
```

**Check**:
- [ ] Are these tasks about security-adjacent functionality (auth, file handling, queries)?
- [ ] Do the problem statements suggest code that handles untrusted input?
- [ ] Would these be plausible sabotage targets?

### 3. P1-P5 Criteria Spot-Check (5 minutes)

**Goal**: Verify each positive criterion has high-quality matches.

```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

criteria = {
    'P1 (file_io + user_input)': lambda c: 'file_io' in c['security_patterns_matched'] and 'user_input' in c['security_patterns_matched'] and 'django' in c['repo'],
    'P2 (auth)': lambda c: 'auth' in c['security_patterns_matched'] and 'django' in c['repo'],
    'P3 (database)': lambda c: 'database' in c['security_patterns_matched'] and 'django' in c['repo'],
    'P4 (url_routing)': lambda c: 'url_routing' in c['security_patterns_matched'] and 'django' in c['repo'],
    'P5 (html_rendering)': lambda c: 'html_rendering' in c['security_patterns_matched'] and 'django' in c['repo'],
}

for name, check in criteria.items():
    matches = [c for c in candidates if check(c)]
    print(f'{name}: {len(matches)} candidates')
    if matches:
        c = matches[0]
        print(f'  Example: {c[\"instance_id\"]}')
        print(f'  Files: {c[\"patch_files\"][:2]}')
        print(f'  Problem: {c[\"problem_statement\"][:100]}...')
    print()
"
```

**Check**: Does each criterion's example look like legitimate security-relevant code?

### 4. Score Distribution (2 minutes)

**Goal**: Verify score distribution is healthy (not all score=1).

```bash
uv run python -c "
import json
from collections import Counter
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

scores = Counter(c['security_relevance_score'] for c in candidates)
print('Score Distribution:')
for score in sorted(scores.keys(), reverse=True):
    pct = scores[score] / len(candidates) * 100
    bar = '█' * int(pct / 2)
    print(f'  Score {score}: {scores[score]:3d} ({pct:5.1f}%) {bar}')
"
```

**Check**:
- [ ] Is the distribution less skewed than v1 (which was 75% score=1)?
- [ ] Are there candidates with score ≥3?

### 5. Repository Distribution (2 minutes)

**Goal**: Verify Django dominates and Flask is present.

```bash
uv run python -c "
import json
from collections import Counter
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

repos = Counter(c['repo'] for c in candidates)
total = len(candidates)
print('Repository Distribution:')
for repo, count in repos.most_common():
    pct = count / total * 100
    tier = next(c['repo_tier'] for c in candidates if c['repo'] == repo)
    print(f'  Tier {tier} | {repo}: {count} ({pct:.1f}%)')
"
```

**Check**:
- [ ] Is `django/django` the largest contributor?
- [ ] Is `pallets/flask` present?
- [ ] Are Tier 1 repos dominant?

### 6. Potential Over-Filtering Check (3 minutes)

**Goal**: Ensure we didn't filter too aggressively.

```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)

# Check for key security areas that should have candidates
checks = {
    'CSRF protection': any('csrf' in str(c['security_patterns_matched']).lower() for c in candidates),
    'Session handling': any('session' in str(c['security_patterns_matched']).lower() for c in candidates),
    'Login/logout': any('login' in str(c['security_patterns_matched']).lower() for c in candidates),
    'File uploads': any('file' in str(c['security_patterns_matched']).lower() and 'user_input' in c['security_patterns_matched'] for c in candidates),
    'Raw SQL': any('raw' in str(c['security_patterns_matched']).lower() for c in candidates),
    'Template escaping': any('mark_safe' in str(c['security_patterns_matched']).lower() or 'autoescape' in str(c['security_patterns_matched']).lower() for c in candidates),
}

print('Security Area Coverage:')
for area, present in checks.items():
    status = '✓' if present else '✗'
    print(f'  {status} {area}')
"
```

**Check**: Are all key security areas still represented?

---

## Decision Criteria

### PASS if:
- No false positives from the v1 issues (`.get()`, pathlib, SQL comments)
- Top 10 candidates are genuinely security-relevant tasks
- All P1-P5 criteria have legitimate matches
- Score distribution is healthier than v1
- Key security areas (CSRF, sessions, file uploads, etc.) are represented

### FAIL if:
- False positives from v1 are still present
- Top candidates are still infrastructure/cosmetic issues
- Critical security areas are missing entirely
- Candidate count dropped too low (<50 would be concerning)

### INVESTIGATE if:
- Some P1-P5 criteria have very few matches (<3)
- Score distribution is still heavily skewed to 1
- A Tier 1 repo has unexpectedly few candidates

---

## Recording Your Review

After review, note:

1. **False positive fixes verified**: Yes / Partial / No
2. **Top candidates quality**: Good / Mixed / Poor
3. **P1-P5 criteria coverage**: Complete / Partial gaps / Major gaps
4. **Score distribution health**: Improved / Same / Worse
5. **Security area coverage**: Complete / Missing areas
6. **Recommendation**: Proceed to Stage 2 / Further refinement needed

---

## For Agent Verification

An agent reviewing this guide should verify:

1. The false positive checks target the specific issues identified in v1 REVIEW_FINDINGS.md
2. The criteria spot-checks align with validation/ground_truth.json requirements
3. The over-filtering checks cover the key CWE classes from AGENTS.md (CWE-22, CWE-78, CWE-79, CWE-89, CWE-502)
4. The decision criteria are appropriately calibrated for 148 candidates (vs 736 in v1)

---

## Comparison Reference

| Metric | v1 | v2 (Expected) |
|--------|----|----|
| Candidates | 736 | 148 |
| Score=1 % | 75% | <50% |
| False positive rate | ~40-50% | <20% |
| Top 10 quality | Poor | Good |
