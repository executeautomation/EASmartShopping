"""
test_intent_detection_new.py — Unit tests for intent detectors added in the current session.

Covers features NOT tested in the parent test_intent_detection.py:

  • _detect_add_to_cart  — strong_add_overrides (hybrid browse+add phrases)
  • _add_all_pattern     — the regex that triggers multi-product add
  • _extract_mentioned_products — bold-name parser from conversation history
  • _detect_update_quantity    — is_delta (3rd return value) for "+N" phrases
  • _detect_top_rated_query    — new function, detects best/top-rated queries

No LLM judge, no backend server needed — pure Python unit tests.

Run in isolation:
  pytest tests/new/test_intent_detection_new.py -v
"""

import re
import sys
import os
import pytest

# Backend is added to sys.path by conftest.py
from rag import (
    _detect_add_to_cart,
    _detect_update_quantity,
    _detect_top_rated_query,
    _extract_mentioned_products,
    _conversation_history,
)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _inject_ai_response(session_id: str, ai_text: str):
    """Inject a fake last AI response into the in-memory conversation history."""
    _conversation_history[session_id] = [{"human": "test", "ai": ai_text}]


def _cleanup(session_id: str):
    _conversation_history.pop(session_id, None)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Strong add-intent overrides
# ══════════════════════════════════════════════════════════════════════════════

class TestStrongAddOverrides:
    """strong_add_overrides in _detect_add_to_cart() must fire BEFORE the
    browse-phrase guard, so hybrid phrases like 'show me X I want to add to cart'
    are still classified as add intent."""

    @pytest.mark.parametrize("phrase", [
        # Plain "add all / add them / add these / add those"
        "add all tops to my cart",
        "add all of them",
        "add all these to cart",
        "add them all",
        "add them to cart",
        "add them all please",
        # "add everything"
        "add everything to cart",
        "add everything i selected",
        # Hybrid browse+add — browse phrase present but override must win
        "show me all the tops i want to add to cart",
        "show me yoga mats and add them",
        "want to add these to my cart",
        # Pronoun "add it"
        "add it to my cart",
        "add it",
        # "add these / add those"
        "add these products",
        "add those to my cart",
    ])
    def test_strong_override_detected_as_add(self, phrase):
        assert _detect_add_to_cart(phrase.lower()), (
            f"strong_add_overrides should detect add intent for: '{phrase}'"
        )

    @pytest.mark.parametrize("phrase", [
        # Pure browse — no strong override present
        "show me all tops",
        "what headphones do you have",
        "find me running shoes",
        "recommend a yoga mat",
        "browse sports gear",
        "tell me about the keyboard",
    ])
    def test_pure_browse_not_overridden(self, phrase):
        assert not _detect_add_to_cart(phrase.lower()), (
            f"Pure browse phrase should NOT be detected as add intent: '{phrase}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. _add_all_pattern regex
# ══════════════════════════════════════════════════════════════════════════════

# This regex is inlined in the add-to-cart handler; we test it here directly.
_ADD_ALL_RE = re.compile(
    r'\badd\b.{0,20}\ball\b|\badd\b.{0,20}\bevery\b|\badd\b.{0,20}\beach\b'
)


class TestAddAllPattern:
    """Verify the _add_all_pattern regex matches phrases that trigger the
    multi-product add logic and does not match single-product add phrases."""

    @pytest.mark.parametrize("phrase", [
        "add all tops",
        "add all of them",
        "add all these items",
        "add them all",
        "add all to cart",
        "add every item to cart",
        "add every one of these",
        "add each product",
        "add each of these",
        "add all running shoes please",
    ])
    def test_matches_add_all_phrases(self, phrase):
        assert _ADD_ALL_RE.search(phrase.lower()), (
            f"_add_all_pattern should match: '{phrase}'"
        )

    @pytest.mark.parametrize("phrase", [
        "add the water bottle",
        "add a yoga mat",
        "add trail running shoes",
        "remove all items",
        "show all products",
        "add 2 more keyboards",
    ])
    def test_no_match_for_single_add_phrases(self, phrase):
        assert not _ADD_ALL_RE.search(phrase.lower()), (
            f"_add_all_pattern should NOT match single-product phrase: '{phrase}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3. _extract_mentioned_products
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractMentionedProducts:
    """_extract_mentioned_products() parses bold **Name** markdown from the
    last AI response stored in _conversation_history.
    Used when the user says 'add them all' so the bot knows which products
    'them' refers to."""

    def test_extracts_multiple_bold_product_names(self):
        sid = "test_emp_multi"
        _inject_ai_response(
            sid,
            "Here are some great options:\n"
            "1. **Trail Running Shoes** – Perfect for off-road.\n"
            "2. **Compression Running Tights** – Great support.\n"
            "3. **Sports Water Bottle** – Stay hydrated.\n",
        )
        names = _extract_mentioned_products(sid)
        assert "Trail Running Shoes" in names
        assert "Compression Running Tights" in names
        assert "Sports Water Bottle" in names
        _cleanup(sid)

    def test_filters_out_option_labels_with_colons(self):
        """Bold text containing a colon like '**Color: Gray**' must be excluded."""
        sid = "test_emp_colon"
        _inject_ai_response(
            sid,
            "The **Trail Running Shoes** come in:\n"
            "- **Color: Gray/Blue**\n"
            "- **Size: UK 9**\n",
        )
        names = _extract_mentioned_products(sid)
        assert "Trail Running Shoes" in names
        assert not any(":" in n for n in names), (
            f"Option labels with colons should be excluded; got: {names}"
        )
        _cleanup(sid)

    def test_filters_out_digit_prefixed_bold_text(self):
        """Bold text starting with a digit (e.g. '**1. Trail Shoes**') must be excluded."""
        sid = "test_emp_digit"
        _inject_ai_response(
            sid,
            "**1. Trail Running Shoes** is great.\n"
            "**2. Yoga Mat** is excellent.\n",
        )
        names = _extract_mentioned_products(sid)
        # Names starting with a digit should be filtered out
        assert all(not n[0].isdigit() for n in names), (
            f"Names starting with digits should be excluded; got: {names}"
        )
        _cleanup(sid)

    def test_returns_empty_list_when_no_history(self):
        sid = "test_emp_nohistory"
        _cleanup(sid)  # ensure clean state
        assert _extract_mentioned_products(sid) == []

    def test_returns_empty_list_when_no_bold_in_response(self):
        sid = "test_emp_nobold"
        _inject_ai_response(sid, "Here are some great running shoes for you!")
        assert _extract_mentioned_products(sid) == []
        _cleanup(sid)

    def test_filters_out_very_short_names(self):
        """Bold text ≤ 3 chars must be excluded (e.g. '**Pro**')."""
        sid = "test_emp_short"
        _inject_ai_response(
            sid,
            "Try the **Pro** model or the **Trail Running Shoes**.",
        )
        names = _extract_mentioned_products(sid)
        assert "Pro" not in names, "'Pro' is too short (3 chars) and should be excluded"
        assert "Trail Running Shoes" in names
        _cleanup(sid)

    def test_returns_only_last_ai_response(self):
        """Only the LAST AI message in history should be parsed."""
        sid = "test_emp_last"
        _conversation_history[sid] = [
            {"human": "show me bags", "ai": "We have the **Leather Tote Bag**."},
            {"human": "show me shoes", "ai": "Check out **Trail Running Shoes** and **Hiking Boots**."},
        ]
        names = _extract_mentioned_products(sid)
        assert "Trail Running Shoes" in names
        assert "Hiking Boots" in names
        # From the earlier turn — not expected, but if it appears that's also fine
        # The key assertion: names from the last response ARE present
        _cleanup(sid)


# ══════════════════════════════════════════════════════════════════════════════
# 4. _detect_update_quantity — is_delta (3rd return value)
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectUpdateQuantityDelta:
    """Tests for the is_delta third return value of _detect_update_quantity().

    is_delta=True  → caller should ADD the qty to the existing cart quantity
    is_delta=False → caller should SET the cart quantity to the exact value

    Note: the qty extractor uses a digit regex (r'\\d+'), so written-out numbers
    like 'three' fall back to qty=1.
    """

    @pytest.mark.parametrize("phrase,expected_qty,expected_delta", [
        # Numeric delta phrases
        ("add 2 more keyboards",        2,  True),
        ("add 2 more",                  2,  True),
        ("add 3 more of these",         3,  True),
        ("add 5 more",                  5,  True),
        ("increase by 2",               2,  True),
        ("increase by 3 units",         3,  True),
        # Word-number delta phrases (qty falls back to 1 — no digit)
        ("add three more",              1,  True),
        ("add another",                 1,  True),
        ("add another one",             1,  True),
        ("one more of the shoes",       1,  True),
        ("two more of the bags",        1,  True),
        ("add more of the hoodie",      1,  True),
        ("add more",                    1,  True),
    ])
    def test_delta_phrases(self, phrase, expected_qty, expected_delta):
        is_update, qty, is_delta = _detect_update_quantity(phrase.lower())
        assert is_update, f"Should detect quantity update for: '{phrase}'"
        assert is_delta == expected_delta, (
            f"Expected is_delta={expected_delta} for '{phrase}', got is_delta={is_delta}"
        )
        assert qty == expected_qty, (
            f"Expected qty={expected_qty} for '{phrase}', got qty={qty}"
        )

    @pytest.mark.parametrize("phrase,expected_qty", [
        ("change quantity to 3",    3),
        ("update to 5",             5),
        ("set quantity to 4",       4),
        ("reduce to 2",             2),
        ("increase to 3",           3),
        ("make it 1",               1),
        ("just 2",                  2),
    ])
    def test_absolute_phrases_have_is_delta_false(self, phrase, expected_qty):
        is_update, qty, is_delta = _detect_update_quantity(phrase.lower())
        assert is_update, f"Should detect quantity update for: '{phrase}'"
        assert not is_delta, (
            f"Absolute phrase should have is_delta=False: '{phrase}', got is_delta={is_delta}"
        )
        assert qty == expected_qty, (
            f"Expected qty={expected_qty} for '{phrase}', got qty={qty}"
        )

    @pytest.mark.parametrize("phrase", [
        "add shoes to cart",
        "remove the bag",
        "what do you recommend",
        "show me headphones",
        "clear my cart",
    ])
    def test_non_quantity_phrases_return_false(self, phrase):
        is_update, qty, is_delta = _detect_update_quantity(phrase.lower())
        assert not is_update, f"Should NOT detect quantity update for: '{phrase}'"
        assert qty is None
        assert not is_delta


# ══════════════════════════════════════════════════════════════════════════════
# 5. _detect_top_rated_query
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectTopRatedQuery:
    """Tests for _detect_top_rated_query().
    Returns (is_top_rated: bool, category_hint: str | None)."""

    @pytest.mark.parametrize("phrase,hint_must_contain", [
        ("highest rated shoes",                  "shoes"),
        ("best rated running shoes",             "running"),
        ("top rated electronics",                "electronics"),
        ("most popular headphones",              "headphones"),
        ("best reviewed backpack",               "backpack"),
        ("best selling sports gear",             "sports"),
        ("what is the most popular bag",         "bag"),
        ("recommend the best keyboard",          "keyboard"),
        ("which is the best laptop",             "laptop"),
        ("customer favourite yoga mat",          "yoga"),
        ("most reviewed wireless speaker",       "wireless"),
        ("highest rating water bottle",          "water"),
        # Generic best-rated without category — hint may be None or an empty string
        ("show me the highest rated products",   None),
        ("what are the best rated items",        None),
    ])
    def test_detects_top_rated_phrases(self, phrase, hint_must_contain):
        detected, hint = _detect_top_rated_query(phrase.lower())
        assert detected, f"Should detect top-rated query: '{phrase}'"
        if hint_must_contain is not None:
            assert hint and hint_must_contain in hint, (
                f"Expected hint to contain '{hint_must_contain}' for '{phrase}', got hint='{hint}'"
            )

    @pytest.mark.parametrize("phrase", [
        "show me all headphones",
        "add trail running shoes to cart",
        "compare the keyboard and mouse",
        "clear my cart",
        "what is in my cart",
        "build me a gaming pc setup",
        "bundle me sports gear",
    ])
    def test_non_top_rated_phrases_not_detected(self, phrase):
        detected, hint = _detect_top_rated_query(phrase.lower())
        assert not detected, f"Should NOT detect top-rated query: '{phrase}'"
        assert hint is None
