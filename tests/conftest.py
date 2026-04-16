"""
conftest.py — Shared fixtures and helpers for EA SmartKart DeepEval test suite.

Setup
-----
The tests require:
  1. The backend running:  cd backend && uvicorn main:app --port 8000
  2. Ollama running with the chat model available (see backend/config.yaml)

Run tests:
  cd tests
  deepeval test run .          # full suite with DeepEval report
  pytest .                     # plain pytest (no report upload)
  pytest -k "rag" -v           # run only RAG tests
"""

import sys
import os
import json
import uuid
import asyncio
import pytest
import requests
from typing import Optional, Type
from pydantic import BaseModel

# ── Add backend to sys.path so we can import rag.py / crud.py directly ────────
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from deepeval.models.base_model import DeepEvalBaseLLM

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ── Ollama judge LLM for DeepEval metrics ─────────────────────────────────────
# DeepEval uses GPT-4 by default. We wrap the local Ollama model so tests
# run without any OpenAI API key.  Set EVAL_MODEL env var to override.
EVAL_MODEL = os.environ.get("EVAL_MODEL", "gemma4:e2b")


class OllamaJudge(DeepEvalBaseLLM):
    """DeepEval-compatible wrapper around a local Ollama model."""

    def __init__(self, model: str = EVAL_MODEL):
        from langchain_ollama import ChatOllama
        self._model_name = model
        self._llm = ChatOllama(
            model=model,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )

    def load_model(self):
        return self._llm

    def get_model_name(self) -> str:
        return f"ollama/{self._model_name}"

    def generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None) -> str:
        if schema is not None:
            return self.generate_with_schema(prompt, schema=schema)
        response = self._llm.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None) -> str:
        if schema is not None:
            return await self.a_generate_with_schema(prompt, schema=schema)
        response = await self._llm.ainvoke(prompt)
        return response.content

    def generate_with_schema(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema: "
            f"{schema.model_json_schema() if schema else '{}'}"
        )
        raw = self._llm.invoke(structured_prompt).content
        # Strip markdown code fences if present
        raw = raw.strip().strip("```json").strip("```").strip()
        try:
            data = json.loads(raw)
            return schema(**data) if schema else raw
        except Exception:
            return raw

    async def a_generate_with_schema(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema: "
            f"{schema.model_json_schema() if schema else '{}'}"
        )
        raw = (await self._llm.ainvoke(structured_prompt)).content
        raw = raw.strip().strip("```json").strip("```").strip()
        try:
            data = json.loads(raw)
            return schema(**data) if schema else raw
        except Exception:
            return raw


# ── Backend helpers ────────────────────────────────────────────────────────────

def new_session() -> str:
    """Generate a unique test session ID."""
    return f"test_{uuid.uuid4().hex[:12]}"


def chat(message: str, session_id: str) -> str:
    """
    Call the streaming chat endpoint and collect the full assistant response.
    Returns the concatenated text content.
    """
    resp = requests.post(
        f"{BACKEND_URL}/api/chat/stream",
        json={"message": message, "session_id": session_id},
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()

    full_text = ""
    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8") if isinstance(line, bytes) else line
        if not decoded.startswith("data: "):
            continue
        payload = decoded[6:].strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
            if data.get("type") == "chunk":
                full_text += data.get("content", "")
        except json.JSONDecodeError:
            pass
    return full_text.strip()


def chat_full(message: str, session_id: str) -> dict:
    """
    Like chat() but returns the full done-event payload alongside the text,
    so tests can inspect bundle_items, pending_options, cart_updated, etc.
    """
    resp = requests.post(
        f"{BACKEND_URL}/api/chat/stream",
        json={"message": message, "session_id": session_id},
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()

    full_text = ""
    done_data: dict = {}
    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8") if isinstance(line, bytes) else line
        if not decoded.startswith("data: "):
            continue
        payload = decoded[6:].strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
            if data.get("type") == "chunk":
                full_text += data.get("content", "")
            elif data.get("type") == "done":
                done_data = data
        except json.JSONDecodeError:
            pass

    return {"text": full_text.strip(), "done": done_data}


def get_cart(session_id: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}/api/cart/{session_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def clear_cart(session_id: str):
    requests.delete(f"{BACKEND_URL}/api/cart/{session_id}/clear", timeout=10)


def rag_search(query: str, k: int = 5) -> list[dict]:
    """Call the semantic search endpoint and return product results."""
    resp = requests.get(
        f"{BACKEND_URL}/api/products/search/semantic",
        params={"q": query},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Shared evaluate helper (pushes to Confident AI) ───────────────────────────

from deepeval import evaluate as _deval_evaluate
from deepeval.evaluate import AsyncConfig as _AsyncConfig

_ASYNC_CFG = _AsyncConfig(run_async=False)  # local Ollama can't handle parallel calls


def evaluate_and_assert(test_case, metrics: list, identifier: str = ""):
    """
    Run deepeval.evaluate() — uploads results to Confident AI — then assert
    all metrics passed.  Use this instead of assert_test() everywhere so that
    every test result appears in the Confident AI dashboard.
    """
    result = _deval_evaluate(
        test_cases=[test_case],
        metrics=metrics,
        identifier=identifier or getattr(test_case, "input", ""),
        async_config=_ASYNC_CFG,
    )
    failed = [
        f"{r.name} (score={r.score:.2f}, threshold={r.threshold}, reason={r.reason})"
        for tc_result in result.test_results
        for r in tc_result.metrics_data
        if not r.success
    ]
    assert not failed, "Metrics failed:\n  " + "\n  ".join(failed)


# ── Shared pytest fixtures ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def judge():
    """A single OllamaJudge instance shared across the test session."""
    return OllamaJudge()


@pytest.fixture
def session_id():
    """A fresh session ID per test."""
    return new_session()
