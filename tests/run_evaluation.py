"""
run_evaluation.py — Run EA SmartKart evaluations and push results to Confident AI.

Usage:
    cd tests
    source ../backend/venv/bin/activate
    python run_evaluation.py
"""

import os
import sys

# Load .env.local for CONFIDENT_AI_API_KEY
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env.local"))
except ImportError:
    pass

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

import deepeval
from deepeval import evaluate
from deepeval.evaluate import AsyncConfig
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import ContextualRelevancyMetric, GEval

from conftest import OllamaJudge, chat, rag_search, new_session

ASYNC_CFG = AsyncConfig(run_async=False)
judge = OllamaJudge()

def _retrieval_context(query, k=6):
    results = rag_search(query)
    return [
        f"{p['name']} ({p['category']}, ${p['price']:.2f}): {p.get('description', '')}"
        for p in results[:k]
    ]

print("🔍 Building test cases...")

test_cases = []

# ── RAG Contextual Relevancy ──────────────────────────────────────────────────
rag_queries = [
    ("wireless headphones",   "Electronics"),
    ("yoga mat",              "Sports"),
    ("leather tote bag",      "Bags"),
    ("gaming pc components",  "Computer Components"),
    ("ceramic coffee mug",    "Home & Kitchen"),
]

relevancy_metric = ContextualRelevancyMetric(threshold=0.3, model=judge, include_reason=True)

for query, category in rag_queries:
    ctx = _retrieval_context(query)
    output = chat(query, new_session())
    tc = LLMTestCase(
        input=query,
        actual_output=output,
        retrieval_context=ctx,
        additional_metadata={"category": category, "test_suite": "RAG Retrieval"},
    )
    test_cases.append((tc, [relevancy_metric]))

# ── Faithfulness ──────────────────────────────────────────────────────────────
faithfulness_metric = GEval(
    name="Faithfulness",
    criteria=(
        "Evaluate whether the actual_output contains only facts supported by the "
        "retrieval_context. Penalise for fabricated specs or prices not in the context."
    ),
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
    threshold=0.5,
    model=judge,
)

faith_queries = [
    "tell me about the sports water bottle",
    "what are the features of the wireless bluetooth headphones",
    "describe the mechanical keyboard",
]

for query in faith_queries:
    ctx = _retrieval_context(query)
    output = chat(query, new_session())
    tc = LLMTestCase(
        input=query,
        actual_output=output,
        retrieval_context=ctx,
        additional_metadata={"test_suite": "RAG Faithfulness"},
    )
    test_cases.append((tc, [faithfulness_metric]))

# ── Recommendations ───────────────────────────────────────────────────────────
specificity_metric = GEval(
    name="Product Specificity",
    criteria=(
        "Evaluate whether the assistant names at least one specific product with a price. "
        "Score low for vague answers with no product names or prices."
    ),
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.5,
    model=judge,
)

rec_queries = [
    "what wireless headphones do you have and how much do they cost",
    "show me sports products",
    "what bags do you have",
]

for query in rec_queries:
    output = chat(query, new_session())
    tc = LLMTestCase(
        input=query,
        actual_output=output,
        additional_metadata={"test_suite": "Recommendations"},
    )
    test_cases.append((tc, [specificity_metric]))

print(f"✅ Built {len(test_cases)} test cases. Running evaluation...")

# ── Group 1: RAG tests (relevancy + faithfulness) ─────────────────────────────
rag_tcs   = [tc for tc, metrics in test_cases if "test_suite" in (tc.additional_metadata or {}) and tc.additional_metadata["test_suite"] in ("RAG Retrieval", "RAG Faithfulness")]
rag_metrics = list({type(m).__name__: m for _, metrics in test_cases for m in metrics if type(m).__name__ in ("ContextualRelevancyMetric", "GEval") and any(tc.retrieval_context for tc, _ in test_cases)}.values())

rag_tcs_relevancy  = [tc for tc, _ in test_cases if (tc.additional_metadata or {}).get("test_suite") == "RAG Retrieval"]
rag_tcs_faith      = [tc for tc, _ in test_cases if (tc.additional_metadata or {}).get("test_suite") == "RAG Faithfulness"]
rec_tcs            = [tc for tc, _ in test_cases if (tc.additional_metadata or {}).get("test_suite") == "Recommendations"]

print(f"  → {len(rag_tcs_relevancy)} RAG Relevancy | {len(rag_tcs_faith)} Faithfulness | {len(rec_tcs)} Recommendations")

hyperparams = {
    "model": "gemma4:e2b",
    "embedding": "nomic-embed-text",
    "backend": "FastAPI + ChromaDB",
}

print("\n📊 Running RAG Contextual Relevancy...")
evaluate(
    test_cases=rag_tcs_relevancy,
    metrics=[relevancy_metric],
    hyperparameters=hyperparams,
    identifier="EA SmartKart — RAG Contextual Relevancy",
    async_config=ASYNC_CFG,
)

print("\n📊 Running RAG Faithfulness...")
evaluate(
    test_cases=rag_tcs_faith,
    metrics=[faithfulness_metric],
    hyperparameters=hyperparams,
    identifier="EA SmartKart — RAG Faithfulness",
    async_config=ASYNC_CFG,
)

print("\n📊 Running Recommendations Specificity...")
evaluate(
    test_cases=rec_tcs,
    metrics=[specificity_metric],
    hyperparameters=hyperparams,
    identifier="EA SmartKart — Product Recommendations",
    async_config=ASYNC_CFG,
)

print("\n🎯 Evaluation complete! Check your Confident AI dashboard:")
print("   https://app.confident-ai.com")
