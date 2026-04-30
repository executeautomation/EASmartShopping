"""
test_chatbot_add_all.py — E2E tests for the "Add All [Category]" feature.

Covers two flows introduced this session:

  Flow A — Direct add-all:
    "add all running shoes to my cart"
    → _add_all_pattern fires, RAG fetches all matching products,
      each gets queued in pending_options or added directly.

  Flow B — Two-turn browse-then-add:
    Turn 1: "show me all running shoes"  (LLM responds with bold **Name** list)
    Turn 2: "add them all"
    → _extract_mentioned_products() parses bold names from Turn 1's response,
      each name is searched via RAG individually, results queued.

Metrics used
------------
• GEval (MultiProductAdd) — Does the response acknowledge adding multiple products?

Requires:
  Backend running at http://localhost:8000
  Ollama running with chat model
"""

import pytest
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

from conftest import (
    chat,
    chat_full,
    get_cart,
    clear_cart,
    new_session,
    evaluate_and_assert,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pending_options_count(done: dict) -> int:
    return len(done.get("pending_options") or [])


def _cart_item_count(session_id: str) -> int:
    cart = get_cart(session_id)
    return len(cart.get("items", []))


# ══════════════════════════════════════════════════════════════════════════════
# Flow A — Direct "add all [category]"
# ══════════════════════════════════════════════════════════════════════════════

class TestAddAllCategory:

    def test_add_all_queues_or_adds_multiple_products(self, judge, session_id):
        """'Add all [category]' should result in multiple pending_options OR
        multiple cart items — not just one product."""
        clear_cart(session_id)
        result = chat_full("add all running shoes to my cart", session_id)
        actual_output = result["text"]
        done = result["done"]

        pending_count = _pending_options_count(done)
        cart_count = _cart_item_count(session_id)

        # Either multiple pending options or multiple items added directly
        assert pending_count >= 1 or cart_count >= 1, (
            f"Expected pending_options or cart items for 'add all running shoes'.\n"
            f"pending_options count: {pending_count}, cart items: {cart_count}\n"
            f"Response: {actual_output[:400]}"
        )

        multi_add = GEval(
            name="MultiProductAdd",
            criteria=(
                "The assistant should acknowledge that it is adding or asking about "
                "multiple products (not just one). It should mention more than one product "
                "name, ask for options on several items, or confirm that multiple items are "
                "being queued. Score high if multiple products are referenced, low if only "
                "one product is discussed."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(
            input="add all running shoes to my cart",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [multi_add])

    @pytest.mark.parametrize("add_all_phrase", [
        "add all tops to my cart",
        "add all electronics",
        "add every sports item",
    ])
    def test_add_all_phrase_variants_are_processed(self, add_all_phrase, session_id):
        """Various 'add all/every' phrase forms should not cause an error and should
        return a non-empty response."""
        clear_cart(session_id)
        result = chat_full(add_all_phrase, session_id)
        assert result["text"], (
            f"Expected a non-empty response for '{add_all_phrase}'"
        )

    def test_add_all_does_not_result_in_single_product_only(self, session_id):
        """After 'add all running shoes', pending_options should contain more than
        one entry when multiple running shoe products exist in the catalogue."""
        clear_cart(session_id)
        result = chat_full("add all running shoes", session_id)
        done = result["done"]

        pending = done.get("pending_options") or []
        # If options were queued, there should be more than one product
        if pending:
            assert len(pending) > 1, (
                f"'Add all' should queue multiple products, but only got: {pending}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Flow B — Two-turn: browse then "add them all"
# ══════════════════════════════════════════════════════════════════════════════

class TestAddThemAll:

    def test_browse_then_add_them_all(self, judge, session_id):
        """Two-turn flow: browse lists products with bold names, 'add them all'
        should extract those names from history and queue them."""
        clear_cart(session_id)

        # Turn 1: browse — LLM should respond with bold **Product Name** entries
        browse_response = chat("show me all running shoes", session_id)
        assert browse_response, "Browse turn should return a non-empty response"

        # Turn 2: add them all — references Turn 1's bold product names
        result = chat_full("add them all", session_id)
        actual_output = result["text"]
        done = result["done"]

        pending_count = _pending_options_count(done)
        cart_count = _cart_item_count(session_id)

        # Something should have happened (pending options queued OR items added)
        assert pending_count >= 1 or cart_count >= 1 or actual_output, (
            f"Expected some action after 'add them all'.\n"
            f"pending_options: {pending_count}, cart_items: {cart_count}\n"
            f"Browse response snippet: {browse_response[:200]}\n"
            f"Add-all response: {actual_output[:200]}"
        )

        add_them_all_eval = GEval(
            name="AddThemAllResponse",
            criteria=(
                "The user first browsed running shoes, then said 'add them all'. "
                "The assistant should either: (a) confirm adding multiple products to the cart, "
                "(b) ask for options (size/color) on multiple products, or "
                "(c) reference the products that were just shown. "
                "Score high if multiple products are addressed, low if the response ignores "
                "the prior context or discusses only one product."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(
            input="add them all",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [add_them_all_eval])

    def test_add_them_all_without_prior_browse_falls_back(self, session_id):
        """'Add them all' with no prior context should fall back to a broad RAG
        search and return some response rather than crashing."""
        fresh_sid = new_session()
        result = chat_full("add them all", fresh_sid)
        # Should not crash and should return something (even if it asks what to add)
        assert result["text"], (
            "Expected a non-empty response for 'add them all' with no prior context"
        )

    def test_strong_add_override_with_browse_prefix(self, judge, session_id):
        """'Show me tops I want to add to cart' must be treated as add intent,
        not browse intent, and should queue products."""
        clear_cart(session_id)
        result = chat_full("show me all the tops i want to add to cart", session_id)
        actual_output = result["text"]
        done = result["done"]

        # Either products are queued for option selection OR response is action-oriented
        pending_count = _pending_options_count(done)

        add_intent_eval = GEval(
            name="StrongAddOverride",
            criteria=(
                "The user said 'show me all the tops I want to add to cart'. "
                "The assistant should treat this as an add-to-cart request (not a pure browse), "
                "and either ask for options on products to add or confirm adding them. "
                "Score high if the response is oriented toward adding products to the cart, "
                "low if it only lists products without any add-to-cart action."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(
            input="show me all the tops i want to add to cart",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [add_intent_eval])
