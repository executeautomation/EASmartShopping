"""
test_chatbot_bundle_autodismiss.py — Tests for bundle auto-dismiss behaviour.

The existing test_chatbot_bundle.py only covers the case where a new bundle
request supersedes an old pending one. This file tests the new auto-dismiss
logic added this session:

  Dismiss triggers (while a bundle is pending):
    • A browse query  ("show me headphones", "find me a keyboard")
    • A question      ("what is the price of the keyboard?", "how many are left?")
    • An explicit rejection ("no", "nope", "cancel", "never mind")
    • A new add-to-cart     ("add trail running shoes")  ← also triggers dismiss

  Verify by inspecting the module-level _pending_bundle dict directly
  (no LLM judge needed for dismissal state).

  Additionally tests that after dismissal, a "yes add them" confirmation
  does NOT add the (now-dismissed) bundle to cart.

Requires:
  Backend running at http://localhost:8000
  Ollama running with chat model
"""

import pytest
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

from conftest import chat, chat_full, get_cart, clear_cart, new_session, evaluate_and_assert

# Import module-level state directly so we can verify dismissal without a
# second round-trip to the server.
from rag import _pending_bundle


# ── Helpers ────────────────────────────────────────────────────────────────────

def _has_pending_bundle(session_id: str) -> bool:
    return bool(_pending_bundle.get(session_id))


def _generate_bundle(session_id: str) -> dict:
    """Send a bundle request and return the full SSE result."""
    return chat_full("build me a gaming PC setup", session_id)


# ══════════════════════════════════════════════════════════════════════════════
# TestBundleAutoDismiss
# ══════════════════════════════════════════════════════════════════════════════

class TestBundleAutoDismiss:

    def test_bundle_dismissed_on_browse_query(self, session_id):
        """A browse query while a bundle is pending should clear _pending_bundle."""
        result = _generate_bundle(session_id)
        assert result["done"].get("bundle_items"), (
            "Bundle must be generated before testing dismissal"
        )
        assert _has_pending_bundle(session_id), (
            "Bundle should be in _pending_bundle after generation"
        )

        # Browse query triggers dismiss
        chat("show me headphones", session_id)

        assert not _has_pending_bundle(session_id), (
            "Bundle should have been dismissed after a browse query ('show me headphones')"
        )

    def test_bundle_dismissed_on_question(self, session_id):
        """A question (query ending with '?') while a bundle is pending
        should clear _pending_bundle."""
        _generate_bundle(session_id)
        assert _has_pending_bundle(session_id), "Bundle should be pending"

        chat("what is the price of the keyboard?", session_id)

        assert not _has_pending_bundle(session_id), (
            "Bundle should have been dismissed after a question"
        )

    @pytest.mark.parametrize("rejection_phrase", [
        "no",
        "nope",
        "cancel",
        "never mind",
        "forget it",
        "not interested",
        "dismiss",
    ])
    def test_bundle_dismissed_on_explicit_rejection(self, rejection_phrase):
        """Explicit rejection words/phrases should clear _pending_bundle."""
        sid = new_session()
        _generate_bundle(sid)
        assert _has_pending_bundle(sid), "Bundle should be pending"

        chat(rejection_phrase, sid)

        assert not _has_pending_bundle(sid), (
            f"Bundle should have been dismissed after rejection: '{rejection_phrase}'"
        )

    def test_bundle_dismissed_on_new_add_to_cart(self, session_id):
        """A new add-to-cart request while a bundle is pending should dismiss
        the bundle so the add-to-cart flow proceeds cleanly."""
        _generate_bundle(session_id)
        assert _has_pending_bundle(session_id), "Bundle should be pending"

        # A direct product add — not a bundle confirm
        chat("add trail running shoes to my cart", session_id)

        assert not _has_pending_bundle(session_id), (
            "Bundle should have been dismissed when user requested a new product add"
        )

    def test_bundle_not_dismissed_on_confirm(self, session_id):
        """A confirmation phrase ('yes', 'add them') should NOT dismiss the bundle
        — it should consume it (add items to cart)."""
        clear_cart(session_id)
        _generate_bundle(session_id)
        assert _has_pending_bundle(session_id), "Bundle should be pending"

        chat("yes add them all to cart", session_id)

        # Bundle should now be consumed (not pending), but this is via confirm — not dismiss
        # Cart should have items
        cart = get_cart(session_id)
        cart_items = cart.get("items", [])
        assert len(cart_items) >= 1, (
            "Confirming the bundle should add items to cart, "
            f"but cart is empty. Bundle was {'still pending' if _has_pending_bundle(session_id) else 'consumed'}."
        )

    def test_bundle_not_readded_after_dismiss_and_confirm(self, judge, session_id):
        """After a bundle is dismissed, a follow-up 'yes' should NOT add the
        old bundle items to cart (the bundle is gone)."""
        clear_cart(session_id)
        _generate_bundle(session_id)

        # Dismiss via browse
        chat("show me sports items", session_id)
        assert not _has_pending_bundle(session_id), "Bundle should be dismissed"

        # Now send a confirm — there is no pending bundle to confirm
        result = chat_full("yes add them all", session_id)
        actual_output = result["text"]

        # Cart should have 0 items OR 1 item (from the add-all fallback after dismiss)
        # but NOT 3-6 items (which would mean the old bundle was mistakenly added)
        cart = get_cart(session_id)
        cart_items = cart.get("items", [])
        assert len(cart_items) < 4, (
            f"After dismiss, 'yes add them all' should not re-add the old bundle. "
            f"Got {len(cart_items)} cart items: {[i['product']['name'] for i in cart_items]}"
        )

        no_stale_bundle = GEval(
            name="NoBundleAfterDismiss",
            criteria=(
                "The user dismissed a bundle and then said 'yes add them all'. "
                "The assistant should NOT respond as if it is confirming the addition of "
                "the previously dismissed bundle. It should either ask what to add, "
                "provide a new suggestion, or handle the ambiguous request gracefully. "
                "Score low if the assistant confirms adding 3 or more bundled items."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(input="yes add them all", actual_output=actual_output)
        evaluate_and_assert(test_case, [no_stale_bundle])
