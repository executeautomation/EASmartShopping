# EA SmartKart — DeepEval Test Suite

Evaluates all chatbot and RAG features using [DeepEval v3.9.5](https://deepeval.com).

## Prerequisites

| Requirement | Detail |
|-------------|--------|
| Python 3.9+ | Same venv as the backend |
| DeepEval | `pip install deepeval==3.9.5` |
| Ollama running | `ollama serve` |
| Chat model pulled | `ollama pull gemma4:e2b` (or whatever is set in `backend/config.yaml`) |
| **Backend running** | `cd backend && uvicorn main:app --port 8000` (required for all tests except `test_intent_detection.py`) |

---

## Installation

```bash
# From the project root — reuse the backend virtual environment
cd backend
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

pip install deepeval==3.9.5
```

---

## Running Tests

### All tests (with DeepEval HTML report)
```bash
cd tests
deepeval test run .
```

### All tests (plain pytest, no report upload)
```bash
cd tests
pytest . -v
```

### Only intent-detection unit tests (no server or Ollama needed)
```bash
cd tests
pytest test_intent_detection.py -v
```

### Run a specific test file
```bash
pytest test_rag_retrieval.py -v
pytest test_chatbot_bundle.py -v
```

### Run a specific test by name
```bash
pytest -k "test_gaming_pc_bundle_no_sports_items" -v
```

---

## Test Files

| File | Feature Tested | Server? | LLM Judge? |
|------|---------------|---------|------------|
| `test_intent_detection.py` | All `_detect_*` functions (unit tests) | ✗ | ✗ |
| `test_rag_retrieval.py` | RAG retrieval quality, faithfulness | ✓ | ✓ |
| `test_chatbot_recommendations.py` | Product recommendations, context retention | ✓ | ✓ |
| `test_chatbot_cart_ops.py` | Add/remove/update/clear cart via chat | ✓ | ✓ |
| `test_chatbot_bundle.py` | Bundle recommender, item removal, relevance | ✓ | ✓ |
| `test_chatbot_comparison.py` | Product comparison table quality | ✓ | ✓ |
| `test_chatbot_reorder.py` | Reorder last order feature | ✓ | ✓ |
| `test_chatbot_conversational.py` | Multi-turn context, edge cases | ✓ | ✓ |

---

## Metrics Used

| Metric | Purpose |
|--------|---------|
| `ContextualRelevancyMetric` | Are retrieved product chunks relevant to the query? |
| `FaithfulnessMetric` | Does the response stay faithful to retrieved product data? |
| `AnswerRelevancyMetric` | Is the chatbot response relevant to the user input? |
| `GEval` (custom criteria) | Flexible LLM-as-judge for cart confirmation, bundle quality, comparison completeness, etc. |

---

## Evaluation Model

By default, tests use the **local Ollama model** as the DeepEval judge (no OpenAI key required).

```bash
# Override judge model
EVAL_MODEL=llama3.1:8b pytest test_rag_retrieval.py -v

# Use OpenAI GPT-4.1 for higher-quality judging (requires OPENAI_API_KEY)
OPENAI_API_KEY=sk-... pytest . -v
# Then set model= to a string in each metric, e.g. model="gpt-4.1"
```

> **Note:** Smaller local models (gemma4:e2b) may produce lower-quality metric scores
> compared to GPT-4-class models. If tests fail unexpectedly, try a larger judge model
> or increase thresholds slightly for local evaluation.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | EA SmartKart backend URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `EVAL_MODEL` | `gemma4:e2b` | Local Ollama model used as DeepEval judge |

---

## Example Output

```
Running 8 test suites...

test_intent_detection.py ..............................................  PASSED
test_rag_retrieval.py .....                                           PASSED
test_chatbot_recommendations.py .....                                 PASSED
test_chatbot_cart_ops.py ..........                                   PASSED
test_chatbot_bundle.py .......                                        PASSED
test_chatbot_comparison.py ......                                     PASSED
test_chatbot_reorder.py .....                                         PASSED
test_chatbot_conversational.py .........                              PASSED

✅ 75 tests passed
```
