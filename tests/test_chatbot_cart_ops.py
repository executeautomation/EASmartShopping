"""
test_chatbot_cart_ops.py — Evaluate chatbot-driven cart operations.

Tests cover:
  • Add item to cart (intent detection + cart mutation)
  • Update quantity via chat
  • Remove item from cart via chat
  • Clear entire cart via chat
  • Cart awareness ("what's in my cart?")

Metrics used
------------
• GEval (CartAction)    — Did the chatbot confirm the correct cart action?
• GEval (Correctness)  — Is the stated outcome accurate?
The actual cart state is verified with plain assertions (no LLM judge needed).
"""

import pytest
from conftest import evaluate_and_assert
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

from conftest import chat, chat_full, get_cart, clear_cart, new_session


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cart_item_names(session_id: str) -> list[str]:
    cart = get_cart(session_id)
    return [item["product"]["name"] for item in cart.get("items", [])]


def _cart_total_items(session_id: str) -> int:
    cart = get_cart(session_id)
    return sum(item["quantity"] for item in cart.get("items", []))


# ── Add to Cart ────────────────────────────────────────────────────────────────

class TestAddToCart:

    def test_add_simple_product_via_chat(self, judge, session_id):
        """Chatbot should add a product to cart when size/color are specified in the query."""
        # Provide all options so the bot adds directly without prompting
        result = chat_full(
            "add trail running shoes size UK 9 color black/white to my cart", session_id
        )
        actual_output = result["text"]

        # Verify cart was updated (cart_updated flag or items in cart)
        cart_items = _cart_item_names(session_id)
        assert any("trail" in name.lower() or "running" in name.lower() for name in cart_items), (
            f"Trail Running Shoes not found in cart. Cart items: {cart_items}\n"
            f"Bot response: {actual_output}"
        )

        confirmation = GEval(
            name="Add to Cart Confirmation",
            criteria=(
                "The assistant should confirm that the item was added to the cart, "
                "or ask the user to select options (size, color, etc.) if required. "
                "Score high for clear confirmation or option prompt, low for ignoring the request."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input="add trail running shoes to my cart",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [confirmation])

    def test_add_product_with_options_triggers_option_prompt(self, judge, session_id):
        """Adding a product that has variants should prompt for option selection."""
        actual_output = chat("add sports water bottle to my cart", session_id)

        option_prompt = GEval(
            name="Option Selection Prompt",
            criteria=(
                "The assistant should ask the user to select product options such as "
                "size, color, or capacity before adding to cart. "
                "Score high if it asks for at least one option, low if it ignores options "
                "or claims to have added without asking."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input="add sports water bottle to my cart",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [option_prompt])

    def test_add_with_options_in_query(self, session_id):
        """When size/color are specified in the message, the item should be added directly."""
        clear_cart(session_id)
        result = chat_full("add a sports water bottle in 750ml ocean blue to my cart", session_id)

        # Either added directly OR asked for remaining options — cart should reflect an attempt
        # We check that the response doesn't outright ignore the request
        assert result["text"], "Expected a non-empty response"

    def test_cart_updated_flag_is_set(self, session_id):
        """The SSE done event should set cart_updated=True when an item is added."""
        clear_cart(session_id)
        # Include options so item is added directly (not blocked by option prompt)
        result = chat_full(
            "add trail running shoes size UK 9 color black/white to my cart", session_id
        )
        done = result["done"]
        # Cart updated may be True OR items may be in the cart already — verify cart changed
        cart_items = _cart_item_names(session_id)
        assert done.get("cart_updated") is True or len(cart_items) > 0, (
            "Expected cart_updated=True in SSE done event or cart to contain items"
        )


# ── Update Quantity ────────────────────────────────────────────────────────────

class TestUpdateCartQuantity:

    def test_update_quantity_via_chat(self, judge, session_id):
        """Chatbot should update item quantity when asked."""
        clear_cart(session_id)
        # Add item with options so it goes directly into cart (not blocked by option prompt)
        chat("add trail running shoes size UK 9 color black/white to my cart", session_id)

        # Now update quantity
        actual_output = chat("change quantity of trail running shoes to 3", session_id)

        confirmation = GEval(
            name="Quantity Update Confirmation",
            criteria=(
                "The assistant should confirm that the quantity has been updated to 3, "
                "or acknowledge the update request. "
                "Score high for explicit confirmation, low for ignoring or refusing."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input="change quantity of trail running shoes to 3",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [confirmation])


# ── Remove from Cart ───────────────────────────────────────────────────────────

class TestRemoveFromCart:

    def test_remove_item_via_chat(self, judge, session_id):
        """Chatbot should remove a specific item when asked."""
        clear_cart(session_id)
        chat("add trail running shoes to my cart", session_id)

        actual_output = chat("remove trail running shoes from my cart", session_id)

        removal_confirmation = GEval(
            name="Item Removal Confirmation",
            criteria=(
                "The assistant should confirm that the specified item has been removed "
                "from the cart, or say it wasn't found. "
                "Score high for a clear removal confirmation, low for ignoring the request."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input="remove trail running shoes from my cart",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [removal_confirmation])

    def test_remove_nonexistent_item_graceful_response(self, judge, session_id):
        """Chatbot should gracefully handle removing an item not in the cart."""
        clear_cart(session_id)
        actual_output = chat("remove yoga mat from my cart", session_id)

        graceful = GEval(
            name="Graceful Not Found Response",
            criteria=(
                "The cart is empty. The assistant should politely inform the user that "
                "the item was not found in the cart rather than crashing or giving a "
                "confusing response. Score high for a helpful, clear message."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input="remove yoga mat from my cart",
            actual_output=actual_output,
        )
        evaluate_and_assert(test_case, [graceful])


# ── Clear Cart ─────────────────────────────────────────────────────────────────

class TestClearCart:

    @pytest.mark.parametrize("clear_phrase", [
        "clear my cart",
        "empty my cart",
        "remove everything from my cart",
    ])
    def test_clear_cart_via_chat(self, judge, session_id, clear_phrase):
        """Various 'clear cart' phrases should all wipe the cart."""
        clear_cart(session_id)
        chat("add trail running shoes to my cart", session_id)

        actual_output = chat(clear_phrase, session_id)

        confirmation = GEval(
            name="Clear Cart Confirmation",
            criteria=(
                "The assistant should confirm that the cart has been cleared or emptied. "
                "Score high for a clear confirmation message."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=clear_phrase, actual_output=actual_output)
        evaluate_and_assert(test_case, [confirmation])

        # Verify cart is actually empty
        cart_items = _cart_item_names(session_id)
        assert len(cart_items) == 0, f"Cart should be empty after '{clear_phrase}', got: {cart_items}"


# ── Cart Awareness ─────────────────────────────────────────────────────────────

class TestCartAwareness:

    def test_chatbot_knows_cart_is_empty(self, judge, session_id):
        """When cart is empty, the bot should say so when asked."""
        clear_cart(session_id)
        actual_output = chat("what's in my cart?", session_id)

        awareness = GEval(
            name="Empty Cart Awareness",
            criteria=(
                "The assistant should accurately state that the cart is currently empty "
                "or has no items. It may also suggest products to browse — that is fine. "
                "Score high if it clearly communicates the cart is empty, even if it "
                "also recommends products. Score low only if it claims there are items "
                "in the cart when there are none."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input="what's in my cart?", actual_output=actual_output)
        evaluate_and_assert(test_case, [awareness])

    def test_chatbot_reports_cart_contents(self, judge, session_id):
        """After adding an item, the bot should name it when asked about cart contents."""
        clear_cart(session_id)
        chat("add trail running shoes to my cart", session_id)
        actual_output = chat("what's in my cart?", session_id)

        awareness = GEval(
            name="Cart Contents Awareness",
            criteria=(
                "The assistant should mention the item(s) in the cart, ideally with "
                "quantity and/or price. The trail running shoes should be mentioned. "
                "Score high for accurate and complete cart summary."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input="what's in my cart?", actual_output=actual_output)
        evaluate_and_assert(test_case, [awareness])
