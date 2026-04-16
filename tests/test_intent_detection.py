"""
test_intent_detection.py — Pure unit tests for all chatbot intent detectors.

These tests import the `_detect_*` functions directly from rag.py and verify
them with plain `assert` statements — no LLM judge, no backend server needed.

Run in isolation:
  pytest test_intent_detection.py -v
"""

import sys
import os
import pytest

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from rag import (
    _detect_add_to_cart,
    _detect_update_quantity,
    _detect_remove_from_cart,
    _detect_clear_cart,
    _detect_bundle_request,
    _detect_bundle_confirm,
    _detect_reorder,
    _detect_comparison,
)


# ── Add to Cart ────────────────────────────────────────────────────────────────

class TestDetectAddToCart:

    @pytest.mark.parametrize("phrase", [
        "add the water bottle to my cart",
        "add it to cart",
        "buy the trail running shoes",
        "i want to buy headphones",
        "i'd like to buy a yoga mat",
        "i want to order the keyboard",
        "i need some resistance bands",
        "i want a water bottle",
        "get me the bluetooth speaker",
        "give me trail running shoes",
        "i'll take the hoodie",
    ])
    def test_positive_add_phrases(self, phrase):
        assert _detect_add_to_cart(phrase.lower()), f"Should detect add-to-cart: '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "what headphones do you have",
        "compare water bottles",
        "how much does it cost",
        "show me all products",
        "remove the shoes from my cart",
        "recommend a headphone",
        "tell me about the speaker",
    ])
    def test_negative_add_phrases(self, phrase):
        assert not _detect_add_to_cart(phrase.lower()), f"Should NOT detect add-to-cart: '{phrase}'"


# ── Update Quantity ────────────────────────────────────────────────────────────

class TestDetectUpdateQuantity:

    @pytest.mark.parametrize("phrase,expected_qty", [
        ("change quantity to 3",          3),
        ("update to 5",                   5),
        ("set quantity to 4",             4),
        ("make it 1",                     1),
        ("reduce to 2",                   2),
        ("quantity to 3",                 3),
    ])
    def test_positive_update_phrases(self, phrase, expected_qty):
        detected, qty = _detect_update_quantity(phrase.lower())
        assert detected, f"Should detect update-quantity: '{phrase}'"
        if expected_qty is not None:
            assert qty == expected_qty, f"Expected qty={expected_qty}, got {qty} for '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "add shoes to cart",
        "remove the bag",
        "what do you recommend",
    ])
    def test_negative_update_phrases(self, phrase):
        detected, _ = _detect_update_quantity(phrase.lower())
        assert not detected, f"Should NOT detect update-quantity: '{phrase}'"


# ── Remove from Cart ───────────────────────────────────────────────────────────

class TestDetectRemoveFromCart:

    @pytest.mark.parametrize("phrase", [
        "remove the water bottle from my cart",
        "delete the headphones",
        "take out the shoes",
        "i don't want the bag anymore",
        "drop the keyboard from my cart",
    ])
    def test_positive_remove_phrases(self, phrase):
        assert _detect_remove_from_cart(phrase.lower()), f"Should detect remove: '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "add headphones to cart",
        "clear my cart",
        "show me running shoes",
    ])
    def test_negative_remove_phrases(self, phrase):
        assert not _detect_remove_from_cart(phrase.lower()), f"Should NOT detect remove: '{phrase}'"


# ── Clear Cart ─────────────────────────────────────────────────────────────────

class TestDetectClearCart:

    @pytest.mark.parametrize("phrase", [
        "clear my cart",
        "empty my cart",
        "remove everything from the cart",
        "remove all items",
        "wipe my cart",
        "start over",
    ])
    def test_positive_clear_phrases(self, phrase):
        assert _detect_clear_cart(phrase.lower()), f"Should detect clear-cart: '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "remove the water bottle",
        "add shoes to cart",
        "what's in my cart",
    ])
    def test_negative_clear_phrases(self, phrase):
        assert not _detect_clear_cart(phrase.lower()), f"Should NOT detect clear-cart: '{phrase}'"


# ── Bundle Request ─────────────────────────────────────────────────────────────

class TestDetectBundleRequest:

    @pytest.mark.parametrize("phrase", [
        "build me a gaming pc",
        "build a gaming setup",
        "gaming pc",
        "create a home office setup",
        "home office setup",
        "put together a workout bundle",
        "bundle for fitness",
        "recommend a bundle for sports",
        "full setup for gaming",
        "complete setup for streaming",
        "what do i need for a gaming pc",
    ])
    def test_positive_bundle_phrases(self, phrase):
        assert _detect_bundle_request(phrase.lower()), f"Should detect bundle: '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "add shoes to cart",
        "show me headphones",
        "compare water bottles",
        "what yoga gear do you have",
    ])
    def test_negative_bundle_phrases(self, phrase):
        assert not _detect_bundle_request(phrase.lower()), f"Should NOT detect bundle: '{phrase}'"


# ── Bundle Confirm ─────────────────────────────────────────────────────────────

class TestDetectBundleConfirm:

    @pytest.mark.parametrize("phrase", [
        "yes",
        "yes please",
        "sure",
        "go ahead",
        "add them all",
        "add all to cart",
        "sounds good",
        "yes add them",
        "add to cart",
        "do it",
        "great",
        "perfect",
        "add the bundle",
    ])
    def test_positive_confirm_phrases(self, phrase):
        assert _detect_bundle_confirm(phrase.lower()), f"Should detect bundle-confirm: '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "no thanks",
        "cancel",
        "show me something else",
        "build me a gaming pc",
    ])
    def test_negative_confirm_phrases(self, phrase):
        assert not _detect_bundle_confirm(phrase.lower()), f"Should NOT detect bundle-confirm: '{phrase}'"


# ── Reorder ────────────────────────────────────────────────────────────────────

class TestDetectReorder:

    @pytest.mark.parametrize("phrase", [
        "reorder my last order",
        "order again",
        "buy again",
        "same as last time",
        "same as before",
        "last order",
        "what did i order",
        "my order history",
        "repeat my order",
        "repeat last order",
        "what did i buy",
    ])
    def test_positive_reorder_phrases(self, phrase):
        assert _detect_reorder(phrase.lower()), f"Should detect reorder: '{phrase}'"

    @pytest.mark.parametrize("phrase", [
        "add shoes to cart",
        "show me headphones",
    ])
    def test_negative_reorder_phrases(self, phrase):
        assert not _detect_reorder(phrase.lower()), f"Should NOT detect reorder: '{phrase}'"


# ── Comparison ─────────────────────────────────────────────────────────────────

class TestDetectComparison:

    @pytest.mark.parametrize("phrase,expect_a,expect_b", [
        ("compare stainless steel water bottle vs sports water bottle", "stainless steel water bottle", "sports water bottle"),
        ("which is better, headphones or speaker",                      "headphones",                   "speaker"),
        ("difference between trail running shoes and yoga leggings",    "trail running shoes",          "yoga leggings"),
        ("headphones versus speaker",                                   "headphones",                   "speaker"),
    ])
    def test_positive_comparison_phrases(self, phrase, expect_a, expect_b):
        detected, prod_a, prod_b = _detect_comparison(phrase.lower())
        assert detected, f"Should detect comparison in: '{phrase}'"
        # At least one of the expected product names should be in the extracted strings
        combined = f"{prod_a} {prod_b}".lower()
        assert expect_a.split()[0] in combined or expect_b.split()[0] in combined, (
            f"Expected '{expect_a}' or '{expect_b}' in extracted products, got: '{prod_a}' / '{prod_b}'"
        )

    @pytest.mark.parametrize("phrase", [
        "add shoes to cart",
        "show me headphones",
        "bundle me sports gear",
        "reorder my last order",
    ])
    def test_negative_comparison_phrases(self, phrase):
        detected, _, _ = _detect_comparison(phrase.lower())
        assert not detected, f"Should NOT detect comparison in: '{phrase}'"
