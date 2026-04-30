"""
test_top_rated.py — Tests for the Top-Rated Products feature.

Covers:
  • GET /api/products/top-rated endpoint (API contract + sorting)
  • _detect_top_rated_query intent (covered in test_intent_detection_new.py)
  • Chatbot integration — queries like "best rated shoes" trigger the endpoint

Endpoint contract
-----------------
  GET /api/products/top-rated
  Query params:
    category    (optional str)
    limit       (int, 1–20, default 5)
    min_reviews (int, ≥0,  default 100)

  Returns: list[Product] sorted by rating DESC, review_count DESC.
  Products with fewer than min_reviews are excluded by default.

Product schema includes:
  id, name, price, category, description, image_url, stock, options,
  rating (float 0–5), review_count (int), specs (dict), manufacturer (str)

Metrics used
------------
• GEval (TopRatedRelevance) — Does the chatbot response surface highly-rated products?

Requires:
  Backend running at http://localhost:8000
  Ollama running with chat model
"""

import pytest
import requests

from conftest import chat, new_session, evaluate_and_assert, BACKEND_URL
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_top_rated(category: str = None, limit: int = 5, min_reviews: int = 0) -> list[dict]:
    """Call the top-rated endpoint and return the parsed JSON."""
    params = {"limit": limit, "min_reviews": min_reviews}
    if category:
        params["category"] = category
    resp = requests.get(f"{BACKEND_URL}/api/products/top-rated", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# 1. API contract tests (no LLM judge needed)
# ══════════════════════════════════════════════════════════════════════════════

class TestTopRatedAPI:

    def test_returns_200_and_list(self):
        """Endpoint must return HTTP 200 and a JSON list."""
        resp = requests.get(
            f"{BACKEND_URL}/api/products/top-rated",
            params={"min_reviews": 0},
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        )
        body = resp.json()
        assert isinstance(body, list), f"Expected a list, got: {type(body)}"

    def test_respects_limit_param(self):
        """Passing limit=3 should return at most 3 products."""
        results = _get_top_rated(limit=3)
        assert len(results) <= 3, (
            f"Expected at most 3 products, got {len(results)}"
        )

    def test_sorted_by_rating_descending(self):
        """Products must be ordered by rating (highest first)."""
        results = _get_top_rated(limit=10, min_reviews=0)
        ratings = [p["rating"] for p in results]
        assert ratings == sorted(ratings, reverse=True), (
            f"Products not sorted by rating DESC. Ratings: {ratings}"
        )

    def test_each_product_has_rating_and_review_count(self):
        """Every returned product must have rating and review_count fields."""
        results = _get_top_rated(limit=10, min_reviews=0)
        for p in results:
            assert "rating" in p, f"Product '{p.get('name')}' missing 'rating'"
            assert "review_count" in p, f"Product '{p.get('name')}' missing 'review_count'"
            assert 0.0 <= p["rating"] <= 5.0, (
                f"Rating out of range for '{p.get('name')}': {p['rating']}"
            )
            assert p["review_count"] >= 0, (
                f"review_count must be non-negative for '{p.get('name')}': {p['review_count']}"
            )

    def test_min_reviews_filter_is_applied(self):
        """Products with fewer reviews than min_reviews must be excluded."""
        high_threshold = 100_000  # deliberately high to expect empty / very few results
        results = _get_top_rated(limit=20, min_reviews=high_threshold)
        for p in results:
            assert p["review_count"] >= high_threshold, (
                f"Product '{p['name']}' has review_count={p['review_count']} "
                f"but min_reviews={high_threshold}"
            )

    def test_category_filter_returns_only_that_category(self):
        """When category is specified, all returned products must be in that category."""
        # Use a category likely to exist in the 39-product catalogue
        for category in ("Sports & Fitness", "Electronics", "Clothing"):
            results = _get_top_rated(category=category, limit=10, min_reviews=0)
            for p in results:
                assert p["category"] == category, (
                    f"Expected category '{category}' but got '{p['category']}' "
                    f"for product '{p['name']}'"
                )
            # Once we find a category with results we can stop checking
            if results:
                break

    def test_products_have_standard_schema_fields(self):
        """Each product in the response must have the standard fields."""
        results = _get_top_rated(limit=5, min_reviews=0)
        required_fields = {"id", "name", "price", "category", "description", "stock"}
        for p in results:
            missing = required_fields - set(p.keys())
            assert not missing, (
                f"Product '{p.get('name')}' missing fields: {missing}"
            )

    def test_limit_boundary_max(self):
        """limit=20 (max) should be accepted and return ≤ 20 products."""
        resp = requests.get(
            f"{BACKEND_URL}/api/products/top-rated",
            params={"limit": 20, "min_reviews": 0},
            timeout=15,
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 20

    def test_limit_boundary_invalid_rejects(self):
        """limit=0 (below minimum of 1) should be rejected with 422."""
        resp = requests.get(
            f"{BACKEND_URL}/api/products/top-rated",
            params={"limit": 0, "min_reviews": 0},
            timeout=15,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for limit=0, got {resp.status_code}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Chatbot integration — top-rated queries
# ══════════════════════════════════════════════════════════════════════════════

class TestTopRatedChatbot:

    def test_best_rated_query_returns_product_names(self, judge, session_id):
        """'Best rated products' should surface product names and ratings."""
        query = "show me the best rated products"
        actual_output = chat(query, session_id)
        assert actual_output, "Expected a non-empty response"

        top_rated_eval = GEval(
            name="TopRatedRelevance",
            criteria=(
                "The user asked for the best-rated products. "
                "The assistant should mention specific product names and ideally include "
                "rating information (stars, score, or 'highest rated'). "
                "Score high if product names with ratings are mentioned, "
                "low if the response is generic or mentions no specific products."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [top_rated_eval])

    def test_top_rated_with_category_returns_relevant_products(self, judge, session_id):
        """'Best rated headphones' should return electronics, not sports products."""
        query = "what are the highest rated headphones"
        actual_output = chat(query, session_id)
        assert actual_output, "Expected a non-empty response"

        category_relevance = GEval(
            name="CategoryTopRated",
            criteria=(
                "The user asked for the highest-rated headphones specifically. "
                "The assistant should mention headphones or audio products. "
                "Score high if the response is about audio/headphone products, "
                "low if it mentions unrelated categories like sports gear or clothing."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [category_relevance])

    @pytest.mark.parametrize("query", [
        "most popular running shoes",
        "best selling sports gear",
        "customer favourite products",
        "most reviewed electronics",
    ])
    def test_top_rated_phrase_variants_return_responses(self, query, session_id):
        """Various top-rated phrase forms should return non-empty responses
        without crashing or producing an error."""
        actual_output = chat(query, new_session())
        assert actual_output, f"Expected a non-empty response for: '{query}'"
        assert len(actual_output) > 20, (
            f"Response too short for top-rated query '{query}': '{actual_output}'"
        )
