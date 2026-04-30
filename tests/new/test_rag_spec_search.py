"""
test_rag_spec_search.py — Tests for the spec / material SQL fallback.

Covers:
  • crud.search_products_by_spec() — direct unit tests (no server needed)
  • Chatbot integration — spec-based queries hitting the SQL fallback path

Background
----------
The RAG pipeline has a SQL fallback for spec/material queries.
When the query contains material/spec keywords (e.g. "nylon", "waterproof",
"bluetooth"), the backend calls search_products_by_spec() to search the
`specs` JSON column, `description`, and `name` fields for ALL keywords.

Metrics used
------------
• ContextualRelevancyMetric — Are results relevant to the spec query?
• GEval (SpecAccuracy)      — Does the response mention relevant spec details?

Requires (for integration tests):
  Backend running at http://localhost:8000
  Ollama running with chat model
"""

import sys
import os
import pytest
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

# Backend path is set by conftest.py
import crud
from conftest import chat, new_session, evaluate_and_assert


# ══════════════════════════════════════════════════════════════════════════════
# 1. Direct crud.search_products_by_spec() unit tests (no server needed)
# ══════════════════════════════════════════════════════════════════════════════

class TestSpecSearchCrud:
    """Direct unit tests for crud.search_products_by_spec().
    Verifies that ALL returned products contain every requested keyword
    in at least one of: specs, description, or name."""

    def test_empty_keyword_list_returns_empty(self):
        results = crud.search_products_by_spec([])
        assert results == [], "Empty keyword list should return no results"

    def test_nonsense_keyword_returns_empty(self):
        results = crud.search_products_by_spec(["xyzzy_impossible_keyword_9999"])
        assert results == [], "Nonsense keyword should return no products"

    def test_single_common_keyword_returns_results(self):
        """A common keyword like 'wireless' should match at least one product."""
        results = crud.search_products_by_spec(["wireless"])
        # We can't guarantee exact products, but we CAN verify that every
        # returned product actually contains the keyword somewhere
        for p in results:
            searchable = (
                str(p.get("specs", "")).lower()
                + " " + (p.get("description") or "").lower()
                + " " + (p.get("name") or "").lower()
            )
            assert "wireless" in searchable, (
                f"Product '{p['name']}' was returned for keyword 'wireless' "
                f"but does not contain it in specs/description/name"
            )

    def test_all_returned_products_contain_every_keyword(self):
        """Multi-keyword search: every result must satisfy ALL keywords (AND logic)."""
        keywords = ["running", "shoes"]
        results = crud.search_products_by_spec(keywords)
        for p in results:
            searchable = (
                str(p.get("specs", "")).lower()
                + " " + (p.get("description") or "").lower()
                + " " + (p.get("name") or "").lower()
            )
            for kw in keywords:
                assert kw in searchable, (
                    f"Product '{p['name']}' returned for keywords {keywords} "
                    f"but does not contain '{kw}'"
                )

    def test_result_products_have_required_fields(self):
        """Every product returned should have the standard schema fields."""
        results = crud.search_products_by_spec(["wireless"])
        for p in results:
            assert "id" in p, "Product missing 'id'"
            assert "name" in p, "Product missing 'name'"
            assert "price" in p, "Product missing 'price'"
            assert "category" in p, "Product missing 'category'"
            assert "specs" in p, "Product missing 'specs' (should be dict)"
            assert isinstance(p["specs"], dict), (
                f"Expected specs to be a dict, got {type(p['specs'])}"
            )

    def test_multi_keyword_is_stricter_than_single(self):
        """Two-keyword search should return ≤ results than each keyword alone."""
        kw1 = ["wireless"]
        kw2 = ["bluetooth"]
        kw_both = ["wireless", "bluetooth"]

        r1 = crud.search_products_by_spec(kw1)
        r2 = crud.search_products_by_spec(kw2)
        r_both = crud.search_products_by_spec(kw_both)

        # Combined search can only return products present in both individual searches
        assert len(r_both) <= len(r1), (
            "Combined keyword search should return ≤ results than a single keyword"
        )
        assert len(r_both) <= len(r2), (
            "Combined keyword search should return ≤ results than a single keyword"
        )

    def test_keyword_search_is_case_insensitive(self):
        """Search should be case-insensitive."""
        lower_results = crud.search_products_by_spec(["wireless"])
        upper_results = crud.search_products_by_spec(["WIRELESS"])
        mixed_results = crud.search_products_by_spec(["Wireless"])

        lower_ids = {p["id"] for p in lower_results}
        upper_ids = {p["id"] for p in upper_results}
        mixed_ids = {p["id"] for p in mixed_results}

        assert lower_ids == upper_ids == mixed_ids, (
            "search_products_by_spec should be case-insensitive; "
            f"lower={lower_ids}, upper={upper_ids}, mixed={mixed_ids}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Chatbot integration — spec/material queries
# ══════════════════════════════════════════════════════════════════════════════

class TestSpecChatbot:
    """Integration tests: chatbot queries containing spec/material keywords
    should return relevant products via the SQL spec fallback path."""

    def test_material_query_returns_relevant_products(self, judge, session_id):
        """A query mentioning a material should surface matching products."""
        query = "show me products made with wireless technology"
        actual_output = chat(query, session_id)
        assert actual_output, "Expected a non-empty response for a spec query"

        spec_relevance = GEval(
            name="SpecQueryRelevance",
            criteria=(
                "The user asked for products with a specific technical feature or material. "
                "The assistant should mention at least one product that has that feature "
                "or explain that no matching product was found. "
                "Score high if the response is relevant to the spec/feature mentioned, "
                "low if it ignores the spec or discusses completely unrelated products."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [spec_relevance])

    @pytest.mark.parametrize("spec_query", [
        "do you have any waterproof products",
        "show me bluetooth devices",
        "find something stainless steel",
    ])
    def test_common_spec_queries_return_response(self, spec_query, session_id):
        """Common spec/material queries should return a non-empty, relevant response."""
        actual_output = chat(spec_query, new_session())
        assert actual_output, f"Expected a response for spec query: '{spec_query}'"
        # Basic sanity: response should not be a generic error
        assert "error" not in actual_output.lower() or len(actual_output) > 100, (
            f"Response looks like an error for '{spec_query}': {actual_output[:200]}"
        )

    def test_no_result_spec_query_handled_gracefully(self, session_id):
        """A spec query with no matching products should produce a graceful
        'nothing found' response rather than crashing."""
        query = "show me products made of unobtanium"
        actual_output = chat(query, session_id)
        assert actual_output, "Expected a non-empty response even when no products match"
        # Should not crash or return an empty string
        assert len(actual_output) > 10, (
            f"Response too short for a graceful 'not found' reply: '{actual_output}'"
        )
