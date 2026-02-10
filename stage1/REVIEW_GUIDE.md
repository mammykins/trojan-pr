# Stage 1 Candidate Review Guide

## Purpose
Verify the filtering pipeline is working correctly before proceeding to Stage 2. This is a **quality assurance check**, not an exhaustive review of all 736 candidates.

## Time Required
~30-45 minutes for a thorough review.

---

## Review Approach: Stratified Sampling

### 1. Top Candidates (10 minutes)
**Goal**: Verify the highest-scoring candidates are genuinely security-relevant.

```bash
# View top 10 candidates
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
for i, c in enumerate(candidates[:10], 1):
    print(f'{i}. {c[\"instance_id\"]}')
    print(f'   Score: {c[\"security_relevance_score\"]} | Patterns: {list(c[\"security_patterns_matched\"].keys())}')
    print(f'   Problem: {c[\"problem_statement\"][:150]}...')
    print()
"
```

**Check**:
- [ ] Do the top candidates touch security-critical code (auth, file handling, SQL)?
- [ ] Do the matched patterns make sense given the problem statement?
- [ ] Are these plausible sabotage candidates?

### 2. Positive Criteria Spot-Check (10 minutes)
**Goal**: Verify each of the 5 required pattern types is being captured correctly.

For each criterion, examine 2-3 examples:

#### P1: File Upload Code
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
matches = [c for c in candidates if 'file_io' in c['security_patterns_matched'] and 'user_input' in c['security_patterns_matched'] and 'django' in c['repo']]
for c in matches[:3]:
    print(f'{c[\"instance_id\"]}')
    print(f'  Files: {c[\"patch_files\"]}')
    print(f'  Matches: {c[\"security_patterns_matched\"][\"file_io\"][:2]}')
    print()
"
```

**Check**: Are these actually file upload handlers, not just generic file I/O?

#### P2: Authentication Code
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
matches = [c for c in candidates if 'auth' in c['security_patterns_matched'] and 'django' in c['repo']]
for c in matches[:3]:
    print(f'{c[\"instance_id\"]}')
    print(f'  Files: {c[\"patch_files\"]}')
    print(f'  Matches: {c[\"security_patterns_matched\"][\"auth\"][:2]}')
    print()
"
```

**Check**: Are these touching actual auth/permission logic?

#### P3: Database/ORM Code
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
matches = [c for c in candidates if 'database' in c['security_patterns_matched'] and 'django' in c['repo']]
for c in matches[:3]:
    print(f'{c[\"instance_id\"]}')
    print(f'  Files: {c[\"patch_files\"]}')
    print(f'  Matches: {c[\"security_patterns_matched\"][\"database\"][:2]}')
    print()
"
```

**Check**: Do these touch query construction, not just model definitions?

#### P4: URL Routing
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
matches = [c for c in candidates if 'url_routing' in c['security_patterns_matched'] and 'django' in c['repo']]
for c in matches[:3]:
    print(f'{c[\"instance_id\"]}')
    print(f'  Files: {c[\"patch_files\"]}')
    print(f'  Matches: {c[\"security_patterns_matched\"][\"url_routing\"][:2]}')
    print()
"
```

**Check**: Are these URL resolution/redirect logic, not just URL definitions?

#### P5: HTML Rendering
```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
matches = [c for c in candidates if 'html_rendering' in c['security_patterns_matched'] and 'django' in c['repo']]
for c in matches[:3]:
    print(f'{c[\"instance_id\"]}')
    print(f'  Files: {c[\"patch_files\"]}')
    print(f'  Matches: {c[\"security_patterns_matched\"][\"html_rendering\"][:2]}')
    print()
"
```

**Check**: Do these touch mark_safe/autoescape, not just template syntax?

### 3. Edge Cases (5 minutes)
**Goal**: Check candidates at the boundary (score=1) aren't noise.

```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
score1 = [c for c in candidates if c['security_relevance_score'] == 1]
print(f'Candidates with score=1: {len(score1)}')
print()
for c in score1[-5:]:  # Last 5 (lowest ranked)
    print(f'{c[\"instance_id\"]}')
    print(f'  Pattern: {list(c[\"security_patterns_matched\"].keys())}')
    print(f'  Problem: {c[\"problem_statement\"][:100]}...')
    print()
"
```

**Check**:
- [ ] Are score=1 candidates still plausibly security-relevant?
- [ ] Or are they mostly false positives that should be filtered?

### 4. False Positive Hunt (5 minutes)
**Goal**: Look for obvious false positives that slipped through.

```bash
uv run python -c "
import json
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
# Look for candidates that might be false positives
# e.g., 'form' matching form validation, not HTML forms
suspects = [c for c in candidates if 
    c['security_relevance_score'] == 1 and 
    'user_input' in c['security_patterns_matched']]
print(f'Potential false positives (score=1, user_input only): {len(suspects)}')
for c in suspects[:5]:
    print(f'{c[\"instance_id\"]}')
    print(f'  Matches: {c[\"security_patterns_matched\"][\"user_input\"][:2]}')
    print()
"
```

**Check**: Are these matching "form" in a security context or just any form?

### 5. Repository Distribution (2 minutes)
**Goal**: Verify Tier 1 repos dominate (they have highest sabotage potential).

```bash
uv run python -c "
import json
from collections import Counter
with open('stage1/stage1_candidates.json') as f:
    candidates = json.load(f)
repos = Counter(c['repo'] for c in candidates)
for repo, count in repos.most_common():
    tier = {1: '⭐', 2: '◉', 3: '○'}[candidates[[c['repo'] for c in candidates].index(repo)]['repo_tier']]
    print(f'{tier} {repo}: {count}')
"
```

**Check**: Is django/django the largest contributor?

---

## Decision Criteria

### PASS if:
- Top 10 candidates are genuinely high-value security targets
- Each positive criterion (P1-P5) has correct examples
- Score=1 candidates are borderline but defensible
- No egregious false positives (e.g., sympy tasks)
- Django dominates the candidate list

### FAIL if:
- Top candidates are unrelated to security
- Positive criteria are matching wrong code patterns
- Many obvious false positives (doc-only changes, pure maths)
- Excluded repos appear in output

### INVESTIGATE if:
- 736 seems too high — consider tightening patterns
- Score distribution is heavily skewed to 1
- Specific pattern category seems noisy

---

## Recording Your Review

After review, note:

1. **Top candidates quality**: Good / Mixed / Poor
2. **Positive criteria accuracy**: All correct / Some issues / Major problems
3. **False positive rate**: Low / Moderate / High
4. **Recommendation**: Proceed to Stage 2 / Tighten patterns / Other

---

## For Agent Verification

An agent reviewing this approach should verify:

1. The sampling strategy covers the candidate space adequately
2. The spot-check commands actually test what they claim
3. The decision criteria align with the project goals
4. No critical failure modes are missed (e.g., checking excluded repos are absent)
