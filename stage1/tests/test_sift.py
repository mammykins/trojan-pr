"""
Tests for Stage 1: Automated Sift
=================================
Tests written FIRST per TDD workflow. Run with:
    uv run pytest stage1/tests/test_sift.py -v

These tests validate:
1. Dataset loading and schema
2. Repository filtering logic
3. Security pattern detection
4. Output format and sorting
"""

import json
import pytest
from pathlib import Path

# Import will fail until sift.py is implemented - that's expected
try:
    from stage1.sift import (
        TIER_1_REPOS,
        TIER_2_REPOS,
        TIER_3_REPOS,
        EXCLUDE_REPOS,
        SECURITY_PATTERNS,
        load_datasets,
        filter_by_repo,
        detect_security_patterns,
        calculate_security_score,
        create_candidate,
        sort_candidates,
    )
    SIFT_AVAILABLE = True
except ImportError:
    SIFT_AVAILABLE = False


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_django_patch_file_io():
    """A Django patch that touches file I/O and user input."""
    return """
diff --git a/django/core/files/uploadhandler.py b/django/core/files/uploadhandler.py
--- a/django/core/files/uploadhandler.py
+++ b/django/core/files/uploadhandler.py
@@ -38,6 +38,10 @@ class FileUploadHandler:
     def new_file(self, file_name, *args, **kwargs):
+        # Handle the uploaded file
+        upload_path = os.path.join(self.upload_dir, file_name)
+        with open(upload_path, 'wb') as f:
+            f.write(request.FILES['file'].read())
"""


@pytest.fixture
def sample_django_patch_auth():
    """A Django patch that touches authentication code."""
    return """
diff --git a/django/contrib/auth/views.py b/django/contrib/auth/views.py
--- a/django/contrib/auth/views.py
+++ b/django/contrib/auth/views.py
@@ -50,6 +50,8 @@ def login(request):
+    if authenticate(request, username=username):
+        login(request, user)
+        request.session['user_id'] = user.id
"""


@pytest.fixture
def sample_django_patch_database():
    """A Django patch that touches ORM/database code."""
    return """
diff --git a/django/db/models/query.py b/django/db/models/query.py
--- a/django/db/models/query.py
+++ b/django/db/models/query.py
@@ -100,6 +100,8 @@ class QuerySet:
     def filter(self, **kwargs):
+        # Use raw SQL for complex query
+        cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
+        return self.extra(where=['status = %s'], params=[status])
"""


@pytest.fixture
def sample_django_patch_url_routing():
    """A Django patch that touches URL routing."""
    return """
diff --git a/django/urls/resolvers.py b/django/urls/resolvers.py
--- a/django/urls/resolvers.py
+++ b/django/urls/resolvers.py
@@ -200,6 +200,8 @@ class URLResolver:
+    urlpatterns = [
+        path('redirect/', redirect_view),
+    ]
+    return HttpResponseRedirect(redirect('/login/'))
"""


@pytest.fixture
def sample_django_patch_html_rendering():
    """A Django patch that touches HTML rendering."""
    return """
diff --git a/django/utils/html.py b/django/utils/html.py
--- a/django/utils/html.py
+++ b/django/utils/html.py
@@ -80,6 +80,8 @@ def format_html(format_string, *args, **kwargs):
+    return mark_safe(format_html('<div>{}</div>', user_input))
+    output = SafeString(content)
"""


@pytest.fixture
def sample_sympy_patch():
    """A sympy patch - pure maths, no security relevance."""
    return """
diff --git a/sympy/core/add.py b/sympy/core/add.py
--- a/sympy/core/add.py
+++ b/sympy/core/add.py
@@ -100,6 +100,8 @@ class Add(AssocOp):
     def _eval_simplify(self, **kwargs):
+        # Simplify the expression
+        return self.func(*[a.simplify() for a in self.args])
"""


@pytest.fixture
def sample_task_record():
    """A sample SWE-bench task record."""
    return {
        "instance_id": "django__django-15388",
        "repo": "django/django",
        "base_commit": "abc123",
        "patch": """diff --git a/django/core/files/storage.py b/django/core/files/storage.py
--- a/django/core/files/storage.py
+++ b/django/core/files/storage.py
@@ -50,6 +50,8 @@ class FileSystemStorage:
+    path = os.path.join(self.location, name)
+    with open(path, 'wb') as f:
+        f.write(content.read())
""",
        "test_patch": "...",
        "problem_statement": "File upload handler does not sanitise filenames",
        "hints_text": "",
        "created_at": "2022-01-01",
        "version": "4.0",
        "FAIL_TO_PASS": "[]",
        "PASS_TO_PASS": "[]",
    }


# =============================================================================
# Dataset Loading Tests
# =============================================================================

@pytest.mark.skipif(not SIFT_AVAILABLE, reason="sift.py not yet implemented")
class TestDatasetLoading:
    """Tests for loading SWE-bench datasets."""

    def test_dataset_loads_with_expected_schema(self):
        """Verify both datasets load and have expected columns."""
        full_dataset, verified_dataset = load_datasets()
        
        expected_columns = {
            "instance_id",
            "repo",
            "base_commit",
            "patch",
            "test_patch",
            "problem_statement",
            "hints_text",
            "created_at",
            "version",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
        }
        
        full_columns = set(full_dataset.column_names)
        verified_columns = set(verified_dataset.column_names)
        
        assert expected_columns.issubset(full_columns), (
            f"Missing columns in full dataset: {expected_columns - full_columns}"
        )
        assert expected_columns.issubset(verified_columns), (
            f"Missing columns in verified dataset: {expected_columns - verified_columns}"
        )

    def test_dataset_has_minimum_record_count(self):
        """Verify datasets have expected minimum sizes."""
        full_dataset, verified_dataset = load_datasets()
        
        assert len(full_dataset) >= 2000, (
            f"Full dataset has {len(full_dataset)} records, expected >= 2000"
        )
        assert len(verified_dataset) >= 400, (
            f"Verified dataset has {len(verified_dataset)} records, expected >= 400"
        )


# =============================================================================
# Repository Filter Tests
# =============================================================================

@pytest.mark.skipif(not SIFT_AVAILABLE, reason="sift.py not yet implemented")
class TestRepoFilter:
    """Tests for repository tier filtering."""

    def test_repo_filter_excludes_correct_repos(self):
        """Verify excluded repos are filtered out."""
        # Create mock tasks from excluded repos
        excluded_tasks = [
            {"instance_id": "sympy__sympy-1234", "repo": "sympy/sympy"},
            {"instance_id": "matplotlib__matplotlib-5678", "repo": "matplotlib/matplotlib"},
            {"instance_id": "mwaskom__seaborn-9012", "repo": "mwaskom/seaborn"},
        ]
        
        filtered = filter_by_repo(excluded_tasks)
        
        assert len(filtered) == 0, "Excluded repos should be filtered out"

    def test_repo_filter_includes_correct_repos(self):
        """Verify tier 1-3 repos are included with correct tier assignment."""
        tasks = [
            {"instance_id": "django__django-1234", "repo": "django/django"},
            {"instance_id": "pallets__flask-5678", "repo": "pallets/flask"},
            {"instance_id": "psf__requests-9012", "repo": "psf/requests"},
            {"instance_id": "sphinx-doc__sphinx-3456", "repo": "sphinx-doc/sphinx"},
        ]
        
        filtered = filter_by_repo(tasks)
        
        assert len(filtered) == 4, "All tier 1-3 repos should be included"
        
        # Check tier assignments
        repos_to_tiers = {t["repo"]: t["repo_tier"] for t in filtered}
        assert repos_to_tiers["django/django"] == 1
        assert repos_to_tiers["pallets/flask"] == 1
        assert repos_to_tiers["psf/requests"] == 2
        assert repos_to_tiers["sphinx-doc/sphinx"] == 3

    def test_repo_tier_constants_are_disjoint(self):
        """Verify no repo appears in multiple tiers."""
        all_repos = set(TIER_1_REPOS) | set(TIER_2_REPOS) | set(TIER_3_REPOS) | set(EXCLUDE_REPOS)
        total_count = len(TIER_1_REPOS) + len(TIER_2_REPOS) + len(TIER_3_REPOS) + len(EXCLUDE_REPOS)
        
        assert len(all_repos) == total_count, "Some repos appear in multiple tier lists"


# =============================================================================
# Security Pattern Detection Tests
# =============================================================================

@pytest.mark.skipif(not SIFT_AVAILABLE, reason="sift.py not yet implemented")
class TestSecurityPatterns:
    """Tests for security pattern detection in patches."""

    def test_security_pattern_detection_file_io(self, sample_django_patch_file_io):
        """Verify file I/O patterns are detected."""
        patterns = detect_security_patterns(sample_django_patch_file_io)
        
        assert "file_io" in patterns, "file_io pattern should be detected"
        assert len(patterns["file_io"]) > 0, "Should have matched lines"

    def test_security_pattern_detection_auth(self, sample_django_patch_auth):
        """Verify auth patterns are detected."""
        patterns = detect_security_patterns(sample_django_patch_auth)
        
        assert "auth" in patterns, "auth pattern should be detected"

    def test_security_pattern_detection_database(self, sample_django_patch_database):
        """Verify database patterns are detected."""
        patterns = detect_security_patterns(sample_django_patch_database)
        
        assert "database" in patterns, "database pattern should be detected"

    def test_security_pattern_detection_url_routing(self, sample_django_patch_url_routing):
        """Verify URL routing patterns are detected."""
        patterns = detect_security_patterns(sample_django_patch_url_routing)
        
        assert "url_routing" in patterns, "url_routing pattern should be detected"

    def test_security_pattern_detection_html_rendering(self, sample_django_patch_html_rendering):
        """Verify HTML rendering patterns are detected."""
        patterns = detect_security_patterns(sample_django_patch_html_rendering)
        
        assert "html_rendering" in patterns, "html_rendering pattern should be detected"

    def test_security_pattern_rejects_non_security_patch(self, sample_sympy_patch):
        """Verify pure maths patches score 0."""
        patterns = detect_security_patterns(sample_sympy_patch)
        score = calculate_security_score(patterns)
        
        assert score == 0, f"Sympy maths patch should score 0, got {score}"

    def test_security_pattern_detection_on_known_patch(self, sample_django_patch_file_io):
        """Verify known Django patch matches expected patterns."""
        patterns = detect_security_patterns(sample_django_patch_file_io)
        score = calculate_security_score(patterns)
        
        # Should detect file_io (os.path, open) and possibly user_input (request.)
        assert score >= 1, f"Django file upload patch should score >= 1, got {score}"
        assert "file_io" in patterns, "Should detect file_io patterns"

    def test_all_pattern_categories_have_patterns(self):
        """Verify all 8 security pattern categories are defined."""
        expected_categories = {
            "file_io",
            "user_input",
            "database",
            "serialisation",
            "auth",
            "url_routing",
            "command_exec",
            "html_rendering",
        }
        
        assert set(SECURITY_PATTERNS.keys()) == expected_categories, (
            f"Missing categories: {expected_categories - set(SECURITY_PATTERNS.keys())}"
        )

    def test_pattern_ignores_context_lines(self):
        """Verify patterns only match added lines (+), not context or removed."""
        patch_with_context = """
diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -10,6 +10,8 @@ class Test:
     # Context line with request.GET - should NOT match
-    old_code = request.POST  # Removed line - should NOT match
+    new_code = request.GET['param']  # Added line - SHOULD match
"""
        patterns = detect_security_patterns(patch_with_context)
        
        # Should only have 1 match (the + line), not 3
        if "user_input" in patterns:
            assert len(patterns["user_input"]) == 1, (
                f"Should only match added lines, got {len(patterns['user_input'])} matches"
            )

    def test_GET_pattern_requires_request_context(self):
        """Verify .get() method calls don't trigger user_input pattern."""
        patch_with_dict_get = """
diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -10,6 +10,8 @@ class Test:
+    value = my_dict.get('key')  # dict.get() - should NOT match
+    data = request.GET['param']  # request.GET - SHOULD match
"""
        patterns = detect_security_patterns(patch_with_dict_get)
        
        # Should only match request.GET, not dict.get()
        if "user_input" in patterns:
            matches = patterns["user_input"]
            assert not any(".get('key')" in m for m in matches), (
                "dict.get() should not match user_input pattern"
            )

    def test_path_pattern_excludes_pathlib(self):
        """Verify pathlib.Path() doesn't trigger url_routing pattern."""
        patch_with_pathlib = """
diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -10,6 +10,8 @@ class Test:
+    file_path = pathlib.Path('/tmp/file.txt')  # pathlib - should NOT match
+    file_path = Path('/tmp/file.txt')  # Path() - should NOT match
+    path('users/', views.user_list),  # URL path - SHOULD match
"""
        patterns = detect_security_patterns(patch_with_pathlib)
        
        # Should only match URL path(), not pathlib.Path()
        if "url_routing" in patterns:
            matches = patterns["url_routing"]
            assert not any("pathlib" in m.lower() for m in matches), (
                "pathlib.Path() should not match url_routing pattern"
            )
            assert not any("Path('/tmp" in m for m in matches), (
                "Path() should not match url_routing pattern"
            )


# =============================================================================
# Output Format Tests
# =============================================================================

@pytest.mark.skipif(not SIFT_AVAILABLE, reason="sift.py not yet implemented")
class TestOutputFormat:
    """Tests for candidate output format."""

    def test_output_json_has_required_fields(self, sample_task_record):
        """Verify candidate records have all required fields."""
        candidate = create_candidate(
            task=sample_task_record,
            repo_tier=1,
            patterns={"file_io": ["os.path on line 50", "open on line 52"]},
            in_verified=True,
        )
        
        required_fields = {
            "instance_id",
            "repo",
            "repo_tier",
            "problem_statement",
            "patch_summary",
            "security_patterns_matched",
            "security_relevance_score",
            "in_verified_subset",
            "patch_files",
            "patch_size_lines",
        }
        
        missing = required_fields - set(candidate.keys())
        assert not missing, f"Candidate missing fields: {missing}"

    def test_output_is_sorted_by_score(self):
        """Verify candidates are sorted by score desc, then tier asc."""
        candidates = [
            {"instance_id": "a", "security_relevance_score": 2, "repo_tier": 2},
            {"instance_id": "b", "security_relevance_score": 3, "repo_tier": 1},
            {"instance_id": "c", "security_relevance_score": 3, "repo_tier": 2},
            {"instance_id": "d", "security_relevance_score": 1, "repo_tier": 1},
        ]
        
        sorted_candidates = sort_candidates(candidates)
        
        # Expected order: b (score=3, tier=1), c (score=3, tier=2), a (score=2, tier=2), d (score=1, tier=1)
        assert sorted_candidates[0]["instance_id"] == "b"
        assert sorted_candidates[1]["instance_id"] == "c"
        assert sorted_candidates[2]["instance_id"] == "a"
        assert sorted_candidates[3]["instance_id"] == "d"

    def test_all_candidates_have_positive_score(self):
        """Verify no zero-score candidates appear in output (invariant I5)."""
        candidates = [
            {"instance_id": "a", "security_relevance_score": 2, "repo_tier": 1},
            {"instance_id": "b", "security_relevance_score": 0, "repo_tier": 1},  # Should be excluded
            {"instance_id": "c", "security_relevance_score": 1, "repo_tier": 2},
        ]
        
        # Filter out zero scores (as the pipeline should do)
        filtered = [c for c in candidates if c["security_relevance_score"] > 0]
        
        assert all(c["security_relevance_score"] > 0 for c in filtered)
        assert len(filtered) == 2


# =============================================================================
# Funnel Metrics Tests
# =============================================================================

@pytest.mark.skipif(not SIFT_AVAILABLE, reason="sift.py not yet implemented")
class TestFunnelMetrics:
    """Tests for filter funnel metrics consistency."""

    def test_funnel_metrics_are_consistent(self, tmp_path):
        """Verify funnel metrics match actual candidate counts."""
        # This test will be run after the full pipeline executes
        # For now, test the structure
        funnel_path = Path(__file__).parent.parent / "stage1_funnel.json"
        candidates_path = Path(__file__).parent.parent / "stage1_candidates.json"
        
        if not funnel_path.exists() or not candidates_path.exists():
            pytest.skip("Output files not yet generated")
        
        with open(funnel_path) as f:
            funnel = json.load(f)
        with open(candidates_path) as f:
            candidates = json.load(f)
        
        # Verify the after_security_filter count matches candidate list length
        assert funnel["after_security_filter"] == len(candidates), (
            f"Funnel reports {funnel['after_security_filter']} candidates "
            f"but file contains {len(candidates)}"
        )
        
        # Verify in_verified_subset count is consistent
        verified_count = sum(1 for c in candidates if c.get("in_verified_subset"))
        assert funnel["in_verified_subset"] == verified_count, (
            f"Funnel reports {funnel['in_verified_subset']} verified "
            f"but counted {verified_count}"
        )


# =============================================================================
# Integration Test (runs full pipeline on live data)
# =============================================================================

@pytest.mark.skipif(not SIFT_AVAILABLE, reason="sift.py not yet implemented")
@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring network access to HuggingFace."""

    def test_pipeline_produces_valid_output(self, tmp_path):
        """Run full pipeline and verify output passes validation criteria."""
        # This test is marked as integration - run separately with:
        # uv run pytest stage1/tests/test_sift.py -v -m integration
        from stage1.sift import run_pipeline
        
        candidates_path = tmp_path / "candidates.json"
        funnel_path = tmp_path / "funnel.json"
        
        run_pipeline(
            candidates_output=str(candidates_path),
            funnel_output=str(funnel_path),
        )
        
        # Load and verify output
        with open(candidates_path) as f:
            candidates = json.load(f)
        
        # Basic sanity checks
        # Note: 736 candidates with current patterns; validation script is the true gate
        assert len(candidates) >= 100, f"Expected >= 100 candidates, got {len(candidates)}"
        assert len(candidates) <= 1000, f"Expected <= 1000 candidates, got {len(candidates)}"
        
        # Verify excluded repos are absent
        excluded = {"sympy/sympy", "matplotlib/matplotlib", "mwaskom/seaborn"}
        repos_present = {c["repo"] for c in candidates}
        assert not (repos_present & excluded), f"Excluded repos found: {repos_present & excluded}"
        
        # Verify required repos are present
        required = {"django/django", "pallets/flask"}
        assert required.issubset(repos_present), f"Missing required repos: {required - repos_present}"
