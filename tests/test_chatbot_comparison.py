"""
test_chatbot_comparison.py — Evaluate the product comparison feature.

The comparison feature detects "compare X vs Y" intent, fetches both products
from RAG, and asks the LLM to produce a structured side-by-side comparison.

Metrics used
------------
• GEval (Comparison Completeness) — Does the response cover price, features, pros/cons, recommendation?
• GEval (Comparison Accuracy)     — Are stated facts consistent with product data?
• FaithfulnessMetric              — Does the comparison not introduce hallucinated specs?
• AnswerRelevancyMetric           — Is the response relevant to the comparison request?
"""

import pytest
from conftest import evaluate_and_assert
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, GEval

from conftest import chat, rag_search, new_session


def _retrieval_context_for_comparison(product_a: str, product_b: str) -> list[str]:
    """Fetch RAG context for both products being compared."""
    ctx = []
    for query in [product_a, product_b]:
        results = rag_search(query, k=2)
        for p in results:
            ctx.append(
                f"{p['name']} ({p['category']}, ${p['price']:.2f}): {p.get('description', '')}"
            )
    return ctx


class TestProductComparison:

    @pytest.mark.parametrize("query,product_a,product_b", [
        (
            "compare the stainless steel water bottle vs the sports water bottle",
            "stainless steel water bottle",
            "sports water bottle",
        ),
        (
            "which is better, wireless bluetooth headphones or bluetooth speaker?",
            "wireless bluetooth headphones",
            "bluetooth speaker",
        ),
        (
            "compare trail running shoes vs yoga leggings for fitness",
            "trail running shoes",
            "yoga leggings",
        ),
    ])
    def test_comparison_response_is_relevant(self, judge, query, product_a, product_b):
        """Comparison response must be relevant to the user's query."""
        actual_output = chat(query, new_session())

        metric = AnswerRelevancyMetric(threshold=0.6, model=judge, include_reason=True)
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [metric])

    def test_comparison_includes_key_sections(self, judge):
        """
        A good comparison should cover: price, features, and a recommendation.
        """
        query = "compare the stainless steel water bottle vs the sports water bottle"
        actual_output = chat(query, new_session())

        completeness = GEval(
            name="Comparison Completeness",
            criteria=(
                "A complete product comparison should include: "
                "(1) pricing for both products, "
                "(2) key features or specs for each, "
                "(3) a recommendation or verdict. "
                "Score high if all three sections are present, lower for each missing section."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.6,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [completeness])

    def test_comparison_faithful_to_product_data(self, judge):
        """Comparison facts should align with actual product data from the store."""
        query = "compare the stainless steel water bottle vs the sports water bottle"
        actual_output = chat(query, new_session())
        retrieval_ctx = _retrieval_context_for_comparison(
            "stainless steel water bottle", "sports water bottle"
        )

        faithfulness = GEval(
            name="Faithfulness",
            criteria=(
                "The response only includes product attributes (price, features, material, "
                "dimensions) that are present in the retrieval_context. It does not invent "
                "specs, model numbers, or features not mentioned in the context."
            ),
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
            threshold=0.6,
            model=judge,
        )
        test_case = LLMTestCase(
            input=query,
            actual_output=actual_output,
            retrieval_context=retrieval_ctx,
        )
        evaluate_and_assert(test_case, [faithfulness], identifier="comparison_faithfulness")

    def test_comparison_has_clear_recommendation(self, judge):
        """The comparison response should end with or include a clear recommendation."""
        query = "which is better for long trips, the stainless steel water bottle or sports water bottle?"
        actual_output = chat(query, new_session())

        recommendation = GEval(
            name="Has Recommendation",
            criteria=(
                "The assistant should make a concrete recommendation — naming one product "
                "as better suited for the stated use case (long trips). "
                "A wishy-washy 'both are good' without guidance should score low. "
                "Score high if a specific, reasoned recommendation is given."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [recommendation])

    def test_comparison_of_same_category_products(self, judge):
        """Comparing two products in the same category should yield a structured table or list."""
        query = "compare DDR4 RAM vs DDR5 RAM"
        actual_output = chat(query, new_session())

        structure = GEval(
            name="Comparison Structure",
            criteria=(
                "When comparing two similar products, the response should be structured "
                "(e.g. a table or clearly labelled sections), not just a paragraph. "
                "Score high for organised, scannable format."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [structure])

    def test_ambiguous_comparison_asks_for_clarification(self, judge):
        """If only one product is mentioned, the bot should ask which product to compare it against."""
        query = "compare the sports water bottle"
        actual_output = chat(query, new_session())

        clarification = GEval(
            name="Clarification for Ambiguous Comparison",
            criteria=(
                "The user only named one product. The assistant should ask for the "
                "second product to compare it against, or compare it against similar "
                "products in the store. "
                "Score high if it handles the ambiguity gracefully."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [clarification])
