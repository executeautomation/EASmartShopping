"""
test_chatbot_bundle.py — Evaluate the Bundle Recommender feature.

The bundle recommender uses RAG to find complementary products and the LLM
to describe them. Tests verify:
  • Bundle SSE event contains bundle_items
  • Items are relevant to the requested category
  • No cross-category noise (e.g. sports items in a PC bundle)
  • Remove-from-bundle intent works in follow-up

Metrics used
------------
• GEval (Bundle Relevance)  — Are the suggested items appropriate for the request?
• GEval (Bundle Diversity)  — Does the bundle include diverse, complementary items?
• AnswerRelevancyMetric     — Is the overall response relevant to the bundle request?
"""

import pytest
from conftest import evaluate_and_assert
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, GEval

from conftest import chat, chat_full, new_session


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bundle_item_names(done_data: dict) -> list[str]:
    return [item["name"] for item in (done_data.get("bundle_items") or [])]


# ── Bundle Generation ─────────────────────────────────────────────────────────

class TestBundleGeneration:

    @pytest.mark.parametrize("prompt,expected_keywords", [
        ("build me a gaming PC setup",   ["processor", "gpu", "graphics", "motherboard", "ssd", "ram", "case"]),
        ("bundle me sports gear",        ["running", "yoga", "resistance", "water", "shoes", "sports"]),
        ("create a home office bundle",  ["keyboard", "mouse", "headphones", "backpack", "mechanical", "wireless"]),
    ])
    def test_bundle_contains_relevant_items(self, judge, prompt, expected_keywords):
        """Bundle items should match the requested category (keyword check + LLM eval)."""
        result = chat_full(prompt, new_session())
        actual_output = result["text"]
        bundle_items = _bundle_item_names(result["done"])

        # Structural check: SSE must include bundle_items
        assert bundle_items, (
            f"No bundle_items in SSE done event for '{prompt}'. "
            f"Response: {actual_output[:300]}"
        )

        # At least 2 bundle items should match expected keywords
        items_lower = " ".join(bundle_items).lower()
        matched = sum(1 for kw in expected_keywords if kw in items_lower)
        assert matched >= 2, (
            f"Bundle items don't match expected category for '{prompt}'. "
            f"Items: {bundle_items}. Expected keywords: {expected_keywords}"
        )

        # LLM eval: is the response relevant to the bundle request?
        relevance = AnswerRelevancyMetric(threshold=0.5, model=judge, include_reason=True)
        test_case = LLMTestCase(input=prompt, actual_output=actual_output)
        evaluate_and_assert(test_case, [relevance])

    def test_bundle_has_minimum_items(self, session_id):
        """Bundle must have at least 3 items."""
        result = chat_full("build me a gaming PC setup", session_id)
        bundle_items = _bundle_item_names(result["done"])
        assert len(bundle_items) >= 3, (
            f"Expected at least 3 bundle items, got {len(bundle_items)}: {bundle_items}"
        )

    def test_bundle_has_max_items(self, session_id):
        """Bundle must not exceed 6 items (UX constraint)."""
        result = chat_full("bundle me sports gear", session_id)
        bundle_items = _bundle_item_names(result["done"])
        assert len(bundle_items) <= 6, (
            f"Expected at most 6 bundle items, got {len(bundle_items)}: {bundle_items}"
        )

    def test_gaming_pc_bundle_no_sports_items(self, session_id):
        """A gaming PC bundle should not contain Sports or Clothing items."""
        result = chat_full("build me a gaming PC setup", session_id)
        bundle_items = _bundle_item_names(result["done"])

        sports_noise = [
            name for name in bundle_items
            if any(kw in name.lower() for kw in ["shoe", "yoga", "water bottle", "resistance", "legging", "hoodie", "jean"])
        ]
        assert not sports_noise, (
            f"Gaming PC bundle contains irrelevant items: {sports_noise}. "
            f"Full bundle: {bundle_items}"
        )

    def test_bundle_no_duplicate_products(self, session_id):
        """No product should appear twice in the same bundle."""
        result = chat_full("build me a gaming PC setup", session_id)
        bundle_items = _bundle_item_names(result["done"])
        assert len(bundle_items) == len(set(bundle_items)), (
            f"Duplicate items in bundle: {bundle_items}"
        )

    def test_bundle_response_is_diverse(self, judge, session_id):
        """Bundle items should be complementary, not all the same type of product."""
        result = chat_full("bundle me a home office setup", session_id)
        actual_output = result["text"]
        bundle_items = _bundle_item_names(result["done"])

        diversity = GEval(
            name="Bundle Diversity",
            criteria=(
                "The bundle should contain a variety of complementary items for a home "
                "office setup. Score high if items span at least 2 different product "
                "categories or types (e.g. input devices, audio, bags/storage, accessories). "
                "Score low ONLY if all items are identical in type (e.g. all keyboards)."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(
            input=f"bundle me a home office setup. Items: {', '.join(bundle_items)}",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [diversity])


# ── Bundle Modification via Chat ───────────────────────────────────────────────

class TestBundleModification:

    def test_remove_item_from_bundle_via_chat(self, judge, session_id):
        """
        After a bundle is suggested, saying 'I don't want X' should remove
        that item from the pending bundle, not try to remove from cart.
        """
        # Step 1: generate bundle
        result = chat_full("bundle me sports gear", session_id)
        bundle_items = _bundle_item_names(result["done"])
        assert bundle_items, "Prerequisite: bundle must be generated first"

        # Step 2: remove the first item via chat
        item_to_remove = bundle_items[0]
        actual_output = chat(f"I don't want the {item_to_remove}", session_id)

        removal_quality = GEval(
            name="Bundle Item Removal",
            criteria=(
                f"The user asked to remove '{item_to_remove}' from the suggested bundle. "
                "The assistant should acknowledge the removal and either show the updated "
                "bundle or confirm the item has been removed. "
                "It should NOT say the cart is empty or that the item wasn't in the cart. "
                "Score high for correct bundle-level removal, low for cart-level confusion."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input=f"I don't want the {item_to_remove}",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [removal_quality])

    def test_bundle_superseded_on_new_request(self, session_id):
        """
        After asking for a sports bundle then a PC bundle, the SSE done event
        for the second request should carry PC-relevant bundle_items (not sports items).
        """
        sid = session_id

        # First bundle: sports
        chat_full("bundle me sports gear", sid)

        # Second bundle: PC — should override the first
        result2 = chat_full("build me a gaming PC setup", sid)
        bundle_items = _bundle_item_names(result2["done"])

        sports_noise = [
            name for name in bundle_items
            if any(kw in name.lower() for kw in ["water bottle", "yoga", "resistance", "running shoe"])
        ]
        assert not sports_noise, (
            f"After switching to gaming PC request, bundle still contains sports items: "
            f"{sports_noise}. Full bundle: {bundle_items}"
        )
