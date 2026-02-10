# Stage 1 Filtering Pipeline Review Findings

**Review Date:** 2026-02-09
**Reviewer:** Agent (parallel with human review)
**Pipeline Output:** 736 candidates from 2,294 SWE-bench tasks

---

## Summary

| Criterion | Assessment |
|-----------|------------|
| Top candidates quality | Poor |
| Positive criteria accuracy | Major problems |
| False positive rate | High (~40-50% estimated) |
| Invariant checks | All pass |
| **Recommendation** | **INVESTIGATE — tighten patterns before Stage 2** |

---

## 1. Top Candidates Quality: Poor

The 10 highest-scoring candidates are **not** genuinely security-relevant. They score high because they touch many files across security-related directories, but the actual issues are cosmetic/infrastructure:

| Rank | Instance ID | Score | Actual Issue |
|------|-------------|-------|--------------|
| 1 | django__django-13841 | 6 | Lazy `__file__` loading (infrastructure) |
| 2 | django__django-10989 | 4 | Windows encoding/ellipses (cosmetic) |
| 3 | django__django-11281 | 4 | Typography improvements (cosmetic) |
| 4 | django__django-12508 | 4 | dbshell `-c SQL` flag (CLI tooling) |
| 5 | django__django-12821 | 4 | Stop minifying admin assets (build) |

**Verdict:** High scores do not correlate with sabotage potential.

---

## 2. Positive Criteria Spot-Check: Major Problems

### P1: File Upload Code (file_io + user_input)
- **Finding:** Matches are generic file I/O (`os.path`, `open()`), not file upload handlers
- **Example:** `django__django-13841` matched `gzip.open()` for password list, not user uploads

### P2: Authentication Code (auth)
- **Finding:** `password` pattern matches string literals and comments, not auth logic
- **Example:** `django__django-11281` matched typography fix: `"The two password fields didn't match."`

### P3: Database/ORM Code (database)
- **Finding:** `SQL` pattern matches comments and path names, not query construction
- **Example:** Matching `"Running deferred SQL..."` output string

### P4: URL Routing (url_routing)
- **Critical Issue:** `path\s*\(` matches `pathlib.Path()`, NOT Django's URL `path()` function
- **Impact:** Inflates scores for any candidate using pathlib

### P5: HTML Rendering (html_rendering)
- **Finding:** Matches `format_html` imports, not unsafe rendering patterns
- **Example:** `from django.utils.html import format_html` (import line, not usage)

---

## 3. False Positive Analysis

### Pattern Match Frequency (Top Offenders)

| Pattern | Match Count | Issue |
|---------|-------------|-------|
| `\bGET\b` | 588 | Matches `.get()` method, not HTTP GET |
| `\bSQL\b` | 557 | Matches in comments, docstrings, file paths |
| `\bvalidat` | 524 | Too broad — any validation code |
| `\bform\b` | 158 | Matches Django forms broadly |
| `\bpath\s*\(` | 52 | Matches `pathlib.Path()`, not URL routing |

### Score Distribution Concern

- **Score 1:** 553 candidates (75%)
- **Score 2:** 154 candidates (21%)
- **Score 3+:** 29 candidates (4%)

The heavy skew to score=1 suggests most candidates have only superficial pattern matches.

### Score=1 Breakdown by Pattern

| Pattern | Count | Notes |
|---------|-------|-------|
| user_input | 299 | Dominated by `.get()` false positives |
| database | 119 | Many SQL string matches |
| file_io | 50 | Generic file operations |
| auth | 34 | Password/session string matches |

---

## 4. Invariant Verification: All Pass ✓

| Check | Result |
|-------|--------|
| Excluded repos absent | ✓ None found |
| Tier 1 dominant | ✓ 496/736 (67%) |
| No score=0 candidates | ✓ Confirmed |
| Valid tier assignment | ✓ All repos in Tier 1-3 |

---

## 5. Recommended Pattern Fixes

### High Priority (will significantly reduce false positives)

1. **`user_input` category:**
   - Change `\bGET\b` → `request\.GET` or `\['GET'\]`
   - Change `\bPOST\b` → `request\.POST` or `\['POST'\]`

2. **`url_routing` category:**
   - Change `\bpath\s*\(` → `\bpath\s*\(\s*['"]` (requires string argument)
   - Or use negative lookbehind: `(?<!Path)\bpath\s*\(`

3. **`database` category:**
   - Change `\bSQL\b` → `\.raw\s*\(|RawSQL|cursor\.execute`

### Medium Priority

4. **`auth` category:**
   - Consider requiring adjacent security context (e.g., `authenticate|login|permission`)

5. **General:**
   - Only match patterns in `+` lines (added code), not context or removed lines

---

## 6. Conclusion

**Recommendation: INVESTIGATE**

The pipeline correctly implements repo filtering and invariants, but the security patterns are **too permissive**, generating a high false positive rate. Before proceeding to Stage 2:

1. Tighten the top 3 noisy patterns (`GET`, `SQL`, `path`)
2. Re-run pipeline
3. Verify top 10 candidates are genuinely security-relevant
4. Aim for <500 candidates with higher average quality

The current 736 candidates would overwhelm Stage 2 LLM triage with low-quality inputs.
