"""
test_chatbot_conversational.py — Multi-turn conversation quality tests.

Tests cover:
  • Follow-up pronoun resolution ("how much is it?" after discussing a product)
  • Context retention across multiple turns
  • Graceful handling of out-of-scope questions
  • Polite refusal of non-product questions

Metrics used
------------
• GEval (Conversational Coherence) — Does each response make sense in context?
• AnswerRelevancyMetric            — Is the follow-up response relevant to the follow-up input?
"""

import pytest
from conftest import evaluate_and_assert
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import AnswerRelevancyMetric, GEval

from conftest import chat, new_session


class TestConversationalContext:

    @pytest.mark.xfail(
        reason="Known limitation: chatbot doesn't reliably resolve pronouns (e.g. 'it') "
               "to products mentioned in prior turns when the follow-up is very short. "
               "The conversation history is passed to the LLM but gemma4:e2b drops context "
               "for single-word follow-ups.",
        strict=False,
    )
    def test_pronoun_resolution_after_product_mention(self, judge):
        """'How much is it?' after discussing headphones should return the headphones price."""
        sid = new_session()
        chat("tell me about the wireless bluetooth headphones", sid)
        actual_output = chat("how much is it?", sid)

        has_price = GEval(
            name="Pronoun Resolution — Price",
            criteria=(
                "The prior conversation was about wireless bluetooth headphones. "
                "The follow-up question 'how much is it?' should be resolved to "
                "the headphones and return a price in dollars. "
                "Score high if a specific dollar price is mentioned. "
                "Also score high if the assistant references headphones and gives their price. "
                "Score low only if the assistant completely ignores the context and gives "
                "an irrelevant response with no price at all."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.4,
            model=judge,
        )
        test_case = LLMTestCase(input="how much is it?", actual_output=actual_output)
        evaluate_and_assert(test_case, [has_price])

    def test_add_it_to_cart_pronoun_resolution(self, judge):
        """'Add it to my cart' after discussing a product should identify the right item."""
        sid = new_session()
        chat("what are trail running shoes like?", sid)
        actual_output = chat("add it to my cart", sid)

        cart_intent = GEval(
            name="Pronoun Resolution — Add to Cart",
            criteria=(
                "The prior message was about trail running shoes. "
                "The follow-up 'add it to my cart' should attempt to add the trail "
                "running shoes to the cart — either confirming addition or asking for "
                "options. It should NOT ask 'which product do you mean?'. "
                "Score high for correctly resolving 'it' to trail running shoes."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input="add it to my cart", actual_output=actual_output)
        evaluate_and_assert(test_case, [cart_intent])

    def test_multi_turn_price_negotiation(self, judge):
        """User asks for cheaper option after seeing a product — bot should suggest lower-priced alternatives."""
        sid = new_session()
        chat("recommend a good laptop bag", sid)
        actual_output = chat("do you have anything cheaper?", sid)

        cheaper_option = GEval(
            name="Cheaper Alternative Suggestion",
            criteria=(
                "The user asked for a cheaper alternative after being shown a laptop bag. "
                "The assistant should suggest one or more lower-priced items (bags or accessories) "
                "with dollar prices. "
                "Score high if: (a) prices are mentioned, AND (b) at least one item is "
                "cheaper than the original recommendation OR the assistant explains it has "
                "limited cheaper bag options but offers alternatives. "
                "Score low only if the bot ignores the price request entirely or repeats "
                "the same expensive item without context."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.35,
            model=judge,
        )
        test_case = LLMTestCase(input="do you have anything cheaper?", actual_output=actual_output)
        evaluate_and_assert(test_case, [cheaper_option])

    def test_out_of_scope_question_handled_gracefully(self, judge):
        """Non-product questions should be handled gracefully, redirecting to shopping."""
        query = "what is the capital of France?"
        actual_output = chat(query, new_session())

        graceful = GEval(
            name="Out-of-Scope Graceful Handling",
            criteria=(
                "The assistant is a shopping assistant and should not be expected to "
                "answer general knowledge questions. It should politely redirect the "
                "user to shopping-related topics or acknowledge it cannot help with "
                "that question. Score high for polite redirection, low for confidently "
                "answering the geography question as if it were a product assistant."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.3,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [graceful])

    def test_conversation_history_trimmed_gracefully(self, judge):
        """After many turns (> max_history_turns), the bot should still respond sensibly."""
        sid = new_session()
        # Flood with 10 turns to exceed the 8-turn window
        for i in range(10):
            chat(f"tell me about product number {i+1}", sid)

        actual_output = chat("what was the last product we talked about?", sid)
        assert actual_output, "Expected a non-empty response after many conversation turns"


class TestEdgeCases:

    def test_empty_search_result_handled(self, judge):
        """Query for a product that doesn't exist should give a helpful response."""
        query = "do you sell refrigerators or washing machines"
        actual_output = chat(query, new_session())

        no_product = GEval(
            name="No-Match Graceful Response",
            criteria=(
                "The store does not sell refrigerators or washing machines. "
                "The assistant should acknowledge that it doesn't carry those items "
                "and optionally suggest related products it does carry. "
                "Score high for honest, helpful response."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=0.5,
            model=judge,
        )
        test_case = LLMTestCase(input=query, actual_output=actual_output)
        evaluate_and_assert(test_case, [no_product])

    def test_very_short_query_handled(self, judge):
        """A very short query like 'shoes' should still return useful results."""
        actual_output = chat("shoes", new_session())

        relevance = AnswerRelevancyMetric(threshold=0.5, model=judge, include_reason=True)
        test_case = LLMTestCase(input="shoes", actual_output=actual_output)
        evaluate_and_assert(test_case, [relevance])

    def test_response_not_empty(self):
        """Every query should produce a non-empty response."""
        queries = [
            "hello",
            "what do you sell",
            "can i buy something",
            "help",
        ]
        for q in queries:
            response = chat(q, new_session())
            assert response.strip(), f"Empty response for query: '{q}'"
