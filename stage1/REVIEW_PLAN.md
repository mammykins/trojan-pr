# Stage 1 Filtering Pipeline Review
Systematic QA review of the sift.py output before proceeding to Stage 2 LLM triage.

## Current State
**Pipeline Output:**
* Total SWE-bench tasks: 2,294
* After repo filter: 1,497
* After security filter: 736 candidates
* In Verified subset: 167

**Score Distribution (concern: 75% are score=1):**
* Score 6: 1 | Score 4: 10 | Score 3: 18
* Score 2: 154 | Score 1: 553

**Repository Distribution (healthy - Tier 1 dominant):**
* django/django: 488 (66%)
* scikit-learn: 72 | sphinx: 67 | pytest: 51 | pylint: 30 | requests: 20 | flask: 8

## Review Steps (per REVIEW_GUIDE.md)
### Step 1: Top Candidates Quality Check
Verify the 10 highest-scoring candidates are genuinely security-relevant targets, not accidental pattern matches.

### Step 2: Positive Criteria Spot-Check
For each of the 5 key pattern types, verify 2-3 examples match real security-relevant code:
* P1: File upload code (file_io + user_input)
* P2: Authentication code (auth patterns)
* P3: Database/ORM code (database patterns)
* P4: URL routing logic (url_routing patterns)
* P5: HTML rendering (html_rendering patterns)

### Step 3: Edge Case Analysis
Examine score=1 candidates (553 total) to determine if they are borderline-valid or noise.

### Step 4: False Positive Hunt
Search for obvious false positives that slipped through (e.g. `form` matching unrelated code).

### Step 5: Invariant Verification
* Confirm no excluded repos (sympy, matplotlib, etc.) appear
* Confirm pallets/jinja is missing from output (Tier 3 but 0 candidates - verify expected)

## Outputs
Create `stage1/REVIEW_FINDINGS.md` documenting:
1. Top candidates quality assessment
2. Pattern accuracy per category
3. False positive rate estimate
4. Recommendation: Proceed / Tighten patterns / Other
