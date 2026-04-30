"""
conftest.py — Local conftest for tests/new/ subfolder.

Pytest automatically inherits fixtures (judge, session_id) from ../conftest.py
via its standard parent-directory conftest discovery.

This file:
  1. Ensures backend/ is on sys.path so test files can import rag.py, crud.py directly.
  2. Loads the parent conftest as a named module and re-exports its helper functions
     so test files in this directory can use the same import style:

        from conftest import chat, chat_full, get_cart, ...

  Fixtures (judge, session_id) are inherited automatically — do NOT redeclare them here.
"""

import sys
import os
import importlib.util

_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_DIR, "..", "..", "backend"))
_PARENT_CONFTEST_PATH = os.path.abspath(os.path.join(_DIR, "..", "conftest.py"))

# Ensure backend modules (rag.py, crud.py, database.py) are importable
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Load parent conftest as a private module to access its helper functions
# without interfering with pytest fixture registration (fixtures are discovered
# by pytest through the normal conftest hierarchy, not through this import).
_spec = importlib.util.spec_from_file_location("_parent_conftest", _PARENT_CONFTEST_PATH)
_pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pc)

# Re-export constants and helpers for use in test files
BACKEND_URL: str = _pc.BACKEND_URL
EVAL_MODEL: str = _pc.EVAL_MODEL
OllamaJudge = _pc.OllamaJudge

new_session = _pc.new_session
chat = _pc.chat
chat_full = _pc.chat_full
get_cart = _pc.get_cart
clear_cart = _pc.clear_cart
rag_search = _pc.rag_search
evaluate_and_assert = _pc.evaluate_and_assert
