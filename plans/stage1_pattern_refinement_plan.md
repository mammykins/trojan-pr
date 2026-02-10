# Stage 1 Pattern Refinement Plan
## Problem Statement
The initial filtering pipeline produced 736 candidates with a ~40-50% false positive rate. Key issues:
* `\bGET\b` matches `.get()` method (588 false positives)
* `\bpath\s*\(` matches `pathlib.Path()`, not Django URL `path()`
* `\bSQL\b` matches comments and docstrings
* `\bvalidat` too broad (524 matches)
* `\bform\b` too broad (158 matches)
* `\bpassword\b` matches string literals
* Patterns match context lines, not just added code (`+` lines)
## Root Causes
1. **Overly broad patterns** — designed for recall, not precision
2. **No line-type filtering** — context/removed lines included
3. **No framework context** — patterns don't account for Django-specific usage
## Proposed Changes
### 1. Update `user_input` Patterns
Current → Refined:
* `\bGET\b` → `request\.GET|\[.GET.\]|method\s*==\s*['"]GET`
* `\bPOST\b` → `request\.POST|\[.POST.\]|method\s*==\s*['"]POST`
* Remove `\bvalidat` (too broad — 524 matches on any validation code)
* Remove `\bform\b` (too broad — 158 matches on Django forms generally)
* Keep `\brequest\.`, `QueryDict`, `MultiValueDict`, `cleaned_data`
### 2. Update `url_routing` Patterns
Current → Refined:
* `\bpath\s*\(` → `^\s*path\s*\(\s*['"]` (URL path with string route)
* Add negative filter: skip if line contains `pathlib` or `Path(`
### 3. Update `database` Patterns
Current → Refined:
* Remove `\bSQL\b` (too noisy)
* Keep `\braw\s*\(`, `\bexecute\s*\(`, `\bcursor\b`, `\.extra\s*\(`, `\bRawSQL\b`
* Add `\.raw_sql` for completeness
### 4. Update `auth` Patterns
Current → Refined:
* Remove `\bpassword\b` (matches string literals like "The two password fields didn't match")
* Remove `\btoken\b` (too generic)
* Keep `\bauthenticat`, `\bpermission`, `\blogin\b`, `\blogout\b`, `\bcsrf\b`, `\b@login_required\b`
* Tighten `\bsession\b` → `request\.session|session\[|SessionMiddleware`
### 5. Filter to Added Lines Only
Modify `detect_security_patterns()` to:
* Only scan lines starting with `+` (added code)
* Skip lines starting with `-` (removed code) or ` ` (context)
* This alone should reduce false positives by ~30%
### 6. Update Tests
Add tests for:
* `test_pattern_ignores_context_lines` — verify `-` and context lines skipped
* `test_GET_pattern_requires_request_context` — verify `.get()` not matched
* `test_path_pattern_excludes_pathlib` — verify `pathlib.Path()` not matched
## Expected Outcome
* Candidate count: ~200-350 (down from 736)
* False positive rate: <20% (down from ~40-50%)
* Top 10 candidates should be genuinely security-relevant
## Validation
After changes:
1. Re-run `validation/validate.py --stage 1` — must still pass
2. Spot-check top 10 candidates — should be security-critical code
3. Verify P1-P5 criteria still have correct matches
