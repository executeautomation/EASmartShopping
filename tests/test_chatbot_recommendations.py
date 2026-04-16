"""
test_chatbot_recommendations.py — Evaluate product recommendation quality.

Metrics used
------------
• AnswerRelevancyMetric  — Is the response relevant to what the user asked for?
• GEval (Helpfulness)   — Does the response provide actionable product info?
• GEval (Specificity)   — Does it name actual products with prices, not vague answers?
"""

import pytest
from conftest import evaluate_and_assert
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, GEval

from conftest import chat, new_session


class TestProductRecommendations:
    """The chatbot should surface relevant products when a user asks for suggestions."""

    @pytest.mark.parametrize("query,expected_category_hint", [
        ("I need something to listen to music wirelessly",    "headphones or speaker"),
        ("recommend a good laptop bag for work",              "bag or backpack"),
        ("what yoga gear do you have",                        "yoga or fitness"),
        ("I want to upgrade my home workout routine",         "resistance bands or yoga"),
        ("show me computer accessories",                      "keyboard or electronics"),
    ])
    def test_recommendation_is_relevant(self, judge, query, expected_category_hint):
        """Response must be relevant to the user's product request."""
        actual_output = chat(query, new_session())

        metric = AnswerRelevancyMetric(
            threshold=0.6,
            model=judge,
            include_reason=True,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [metric])

    @pytest.mark.parametrize("query", [
        "what wireless headphones do you have and how much do they cost",
        "show me sports products",
        "what bags do you have",
    ])
    def test_response_mentions_products_with_prices(self, judge, query):
        """Recommendation responses should name specific products and mention prices."""
        actual_output = chat(query, new_session())

        specificity = GEval(
            name="Product Specificity",
            criteria=(
                "Evaluate whether the assistant's response names at least one specific "
                "product with a price. A vague answer like 'we have great headphones' "
                "without naming any product or price should score low."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [specificity])

    def test_response_not_hallucinate_products(self, judge):
        """The bot should not invent product names that don't exist in the store."""
        query = "do you sell gaming chairs or standing desks"
        actual_output = chat(query, new_session())

        honesty = GEval(
            name="Honest Out-of-Stock Response",
            criteria=(
                "If the user asks for a product the store doesn't carry, the assistant "
                "should acknowledge it doesn't have that item (or suggest alternatives). "
                "It should NOT confidently claim to sell products it doesn't have. "
                "Score high if honest, score low if it fabricates availability."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [honesty])

    def test_follow_up_context_retention(self, judge):
        """
        After recommending headphones, asking 'how much does it cost?' should
        answer about the headphones — not give a generic response.
        """
        sid = new_session()
        chat("recommend wireless headphones", sid)  # prime context
        follow_up_output = chat("how much does it cost?", sid)

        context_quality = GEval(
            name="Context Retention",
            criteria=(
                "The second message is 'how much does it cost?' with no product named. "
                "The assistant should infer this refers to the previously discussed "
                "headphones and give a specific price. "
                "Score high if a price in dollars is mentioned, low if the response is "
                "generic or asks the user to clarify what product they mean."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(
            input="how much does it cost?",
            actual_output=follow_up_output,
        )
        evaluate_and_assert(test_case, [context_quality])
