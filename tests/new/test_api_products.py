"""
test_api_products.py — API integration tests for product detail endpoints.

Covers:
  • GET /api/products/{id}         — product detail, all schema fields
  • GET /api/products/{id}/similar — similar products via vector search
  • Ratings fields: rating, review_count, specs (dict), manufacturer (str)

These fields were added in the previous session (39 enriched products).
No tests existed for them; this file closes that gap.

No LLM judge needed — all assertions are structural/contractual.

Requires:
  Backend running at http://localhost:8000
"""

import pytest
import requests

from conftest import BACKEND_URL


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_product(product_id: int) -> requests.Response:
    return requests.get(
        f"{BACKEND_URL}/api/products/{product_id}",
        timeout=15,
    )


def _get_similar(product_id: int, limit: int = 4) -> requests.Response:
    return requests.get(
        f"{BACKEND_URL}/api/products/{product_id}/similar",
        params={"limit": limit},
        timeout=30,
    )


def _first_product_id() -> int:
    """Return the id of the first product in the catalogue."""
    resp = requests.get(f"{BACKEND_URL}/api/products", params={"limit": 1}, timeout=10)
    resp.raise_for_status()
    products = resp.json()
    assert products, "No products in catalogue — database may be empty"
    return products[0]["id"]


def _all_product_ids(limit: int = 10) -> list[int]:
    """Return up to `limit` product IDs from the catalogue."""
    resp = requests.get(f"{BACKEND_URL}/api/products", timeout=10)
    resp.raise_for_status()
    return [p["id"] for p in resp.json()[:limit]]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Product Detail — GET /api/products/{id}
# ══════════════════════════════════════════════════════════════════════════════

class TestProductDetailAPI:

    def test_valid_id_returns_200(self):
        pid = _first_product_id()
        resp = _get_product(pid)
        assert resp.status_code == 200, (
            f"GET /api/products/{pid} returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_invalid_id_returns_404(self):
        resp = _get_product(999_999)
        assert resp.status_code == 404, (
            f"Expected 404 for non-existent product, got {resp.status_code}"
        )

    def test_response_is_a_dict(self):
        pid = _first_product_id()
        body = _get_product(pid).json()
        assert isinstance(body, dict), f"Expected a dict, got {type(body)}"

    def test_required_fields_present(self):
        """Every product detail response must include the core schema fields."""
        pid = _first_product_id()
        p = _get_product(pid).json()
        required = {"id", "name", "price", "category", "description", "stock", "options"}
        missing = required - set(p.keys())
        assert not missing, f"Product {pid} missing required fields: {missing}"

    def test_id_matches_requested_id(self):
        pid = _first_product_id()
        p = _get_product(pid).json()
        assert p["id"] == pid, (
            f"Returned product id {p['id']} does not match requested id {pid}"
        )

    def test_price_is_positive_float(self):
        pid = _first_product_id()
        p = _get_product(pid).json()
        assert isinstance(p["price"], (int, float)), "price must be numeric"
        assert p["price"] > 0, f"price must be positive, got {p['price']}"

    def test_stock_is_non_negative_int(self):
        pid = _first_product_id()
        p = _get_product(pid).json()
        assert isinstance(p["stock"], int), "stock must be an integer"
        assert p["stock"] >= 0, f"stock must be non-negative, got {p['stock']}"

    def test_options_is_a_list(self):
        pid = _first_product_id()
        p = _get_product(pid).json()
        assert isinstance(p["options"], list), (
            f"options must be a list, got {type(p['options'])}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Enriched fields — rating, review_count, specs, manufacturer
# ══════════════════════════════════════════════════════════════════════════════

class TestProductEnrichedFields:
    """Validates the fields added when the catalogue was enriched:
    rating, review_count, specs (dict), manufacturer (str)."""

    def test_rating_field_present_and_in_range(self):
        for pid in _all_product_ids(limit=10):
            p = _get_product(pid).json()
            assert "rating" in p, f"Product {pid} ('{p.get('name')}') missing 'rating'"
            assert 0.0 <= p["rating"] <= 5.0, (
                f"Rating {p['rating']} is out of 0–5 range for product {pid}"
            )

    def test_review_count_present_and_non_negative(self):
        for pid in _all_product_ids(limit=10):
            p = _get_product(pid).json()
            assert "review_count" in p, (
                f"Product {pid} ('{p.get('name')}') missing 'review_count'"
            )
            assert isinstance(p["review_count"], int), (
                f"review_count must be int for product {pid}, got {type(p['review_count'])}"
            )
            assert p["review_count"] >= 0, (
                f"review_count must be non-negative for product {pid}: {p['review_count']}"
            )

    def test_specs_field_is_dict(self):
        """specs must always be a dict (empty dict is fine, but never None or a string)."""
        for pid in _all_product_ids(limit=10):
            p = _get_product(pid).json()
            assert "specs" in p, f"Product {pid} ('{p.get('name')}') missing 'specs'"
            assert isinstance(p["specs"], dict), (
                f"specs must be a dict for product {pid}, got {type(p['specs'])}: {p['specs']}"
            )

    def test_manufacturer_field_is_string(self):
        """manufacturer must be a string (empty string is acceptable)."""
        for pid in _all_product_ids(limit=10):
            p = _get_product(pid).json()
            assert "manufacturer" in p, (
                f"Product {pid} ('{p.get('name')}') missing 'manufacturer'"
            )
            assert isinstance(p["manufacturer"], str), (
                f"manufacturer must be a str for product {pid}, "
                f"got {type(p['manufacturer'])}: {p['manufacturer']}"
            )

    def test_at_least_some_products_have_non_zero_rating(self):
        """After enrichment, at least some products should have a positive rating."""
        products = []
        resp = requests.get(f"{BACKEND_URL}/api/products", timeout=10)
        resp.raise_for_status()
        products = resp.json()

        rated = [p for p in products if p.get("rating", 0) > 0]
        assert len(rated) >= 5, (
            f"Expected at least 5 products with rating > 0 after enrichment, "
            f"got {len(rated)} out of {len(products)}"
        )

    def test_at_least_some_products_have_non_empty_specs(self):
        """After enrichment, at least some products should have non-empty specs."""
        resp = requests.get(f"{BACKEND_URL}/api/products", timeout=10)
        resp.raise_for_status()
        products = resp.json()

        with_specs = [p for p in products if p.get("specs")]
        assert len(with_specs) >= 5, (
            f"Expected at least 5 products with non-empty specs after enrichment, "
            f"got {len(with_specs)} out of {len(products)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3. Similar Products — GET /api/products/{id}/similar
# ══════════════════════════════════════════════════════════════════════════════

class TestSimilarProductsAPI:

    def test_returns_200_and_list(self):
        pid = _first_product_id()
        resp = _get_similar(pid)
        assert resp.status_code == 200, (
            f"GET /api/products/{pid}/similar returned {resp.status_code}: {resp.text[:200]}"
        )
        assert isinstance(resp.json(), list), "Expected a list of similar products"

    def test_invalid_product_returns_404(self):
        resp = _get_similar(999_999)
        assert resp.status_code == 404, (
            f"Expected 404 for similar products of non-existent product, got {resp.status_code}"
        )

    def test_source_product_excluded_from_results(self):
        """The product itself must not appear in its own similar products list."""
        pid = _first_product_id()
        similar = _get_similar(pid).json()
        returned_ids = [p["id"] for p in similar]
        assert pid not in returned_ids, (
            f"Product {pid} should not appear in its own similar products list. "
            f"Got ids: {returned_ids}"
        )

    def test_similar_products_respect_limit(self):
        """limit query param should cap the number of results."""
        pid = _first_product_id()
        for limit in (1, 2, 4):
            similar = _get_similar(pid, limit=limit).json()
            assert len(similar) <= limit, (
                f"Expected ≤ {limit} similar products, got {len(similar)}"
            )

    def test_similar_products_have_required_fields(self):
        """Each similar product must have the standard schema fields."""
        pid = _first_product_id()
        similar = _get_similar(pid, limit=4).json()
        required = {"id", "name", "price", "category"}
        for p in similar:
            missing = required - set(p.keys())
            assert not missing, (
                f"Similar product '{p.get('name')}' missing fields: {missing}"
            )

    def test_similar_products_are_not_duplicates(self):
        """No product should appear twice in the similar list."""
        pid = _first_product_id()
        similar = _get_similar(pid, limit=4).json()
        ids = [p["id"] for p in similar]
        assert len(ids) == len(set(ids)), (
            f"Duplicate products in similar list: {ids}"
        )
