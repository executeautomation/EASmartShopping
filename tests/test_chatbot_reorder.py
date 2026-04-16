"""
test_chatbot_reorder.py — Evaluate the Reorder Last Order feature.

The reorder feature detects phrases like "reorder my last order", looks up
the session's order history, and re-adds items to the cart.

Metrics used
------------
• GEval (Reorder Handling) — Did the bot handle the reorder intent correctly?
"""

import pytest
import requests
from conftest import evaluate_and_assert
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

from conftest import chat, chat_full, get_cart, clear_cart, new_session, BACKEND_URL


# ── Helpers ────────────────────────────────────────────────────────────────────

def _place_test_order(session_id: str, product_id: int = 7, quantity: int = 1) -> int:
    """Add an item to cart then create an order; returns the order ID."""
    # Add to cart
    requests.post(
        f"{BACKEND_URL}/api/cart/{session_id}/add",
        json={"product_id": product_id, "quantity": quantity, "options": {}},
        timeout=10,
    ).raise_for_status()

    # Checkout
    cart = requests.get(f"{BACKEND_URL}/api/cart/{session_id}", timeout=10).json()
    items = [
        {"product_id": i["product"]["id"], "quantity": i["quantity"], "price": i["product"]["price"]}
        for i in cart["items"]
    ]
    order_resp = requests.post(
        f"{BACKEND_URL}/api/orders",
        json={"session_id": session_id, "items": items, "total": cart["total"]},
        timeout=10,
    )
    order_resp.raise_for_status()
    clear_cart(session_id)
    return order_resp.json()["id"]


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestReorderFeature:

    def test_reorder_with_no_previous_orders(self, judge, session_id):
        """Bot should gracefully tell user they have no order history."""
        actual_output = chat("reorder my last order", session_id)

        no_history = GEval(
            name="No Order History Response",
            criteria=(
                "The user has no previous orders. The assistant should inform them "
                "that no order history was found and offer to help find products. "
                "Score high for a helpful, honest response. "
                "Score low if the bot pretends to have re-ordered something."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input="reorder my last order", actual_output=actual_output)
        evaluate_and_assert(test_case, [no_history])

    def test_reorder_shows_order_history(self, judge, session_id):
        """Bot should handle reorder intent when the user has previous orders."""
        _place_test_order(session_id, product_id=7)  # Trail Running Shoes

        actual_output = chat("order again", session_id)

        shows_history = GEval(
            name="Order History Display",
            criteria=(
                "The user has a previous order. The assistant should either: "
                "(a) show the previous order details (order ID, items, or total), OR "
                "(b) confirm that items from the previous order have been re-added to cart. "
                "Both are acceptable responses. "
                "Score high for any response that references previous orders or confirms re-adding items. "
                "Score low only if the bot has no mention of orders or past purchases at all."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(input="order again", actual_output=actual_output)
        evaluate_and_assert(test_case, [shows_history])

    def test_reorder_confirms_and_adds_to_cart(self, judge, session_id):
        """
        After seeing order history, confirming with 'yes' should re-add
        items to the cart.
        """
        _place_test_order(session_id, product_id=7)

        # Step 1: trigger reorder flow
        chat("reorder my last order", session_id)

        # Step 2: confirm
        actual_output = chat("yes, reorder those", session_id)

        confirm_quality = GEval(
            name="Reorder Confirmation",
            criteria=(
                "The user confirmed they want to reorder. The assistant should confirm "
                "that the items have been added to the cart, or explain if something "
                "went wrong. Score high for a clear, positive confirmation."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input="yes, reorder those", actual_output=actual_output)
        evaluate_and_assert(test_case, [confirm_quality])

    @pytest.mark.parametrize("phrase", [
        "reorder",
        "order again",
        "buy the same things again",
        "same as last time",
    ])
    def test_reorder_intent_phrases(self, judge, session_id, phrase):
        """All common reorder phrases should be recognised by the chatbot."""
        actual_output = chat(phrase, session_id)

        # With no order history, any of these should yield a "no orders found" style response
        # (not a generic product recommendation)
        reorder_detected = GEval(
            name="Reorder Intent Detected",
            criteria=(
                "The assistant should treat this as a reorder request — either showing "
                "order history if available, or explaining that no previous orders exist. "
                "Score high if the bot mentions orders, order history, or previous purchases. "
                "Score low only if the assistant gives a generic product recommendation "
                "with no mention of orders, order history, or previous purchases at all."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(input=phrase, actual_output=actual_output)
        evaluate_and_assert(test_case, [reorder_detected])
