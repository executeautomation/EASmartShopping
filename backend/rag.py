import os
import re
import json
import logging

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from database import get_connection
from config import (
    OLLAMA_BASE_URL, CHAT_MODEL, EMBED_MODEL,
    TEMPERATURE, MAX_TOKENS, REASONING,
    MAX_HISTORY_TURNS, VAGUE_QUERY_MAX_WORDS,
)

logger = logging.getLogger(__name__)

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
# Pronouns that signal a follow-up referring to a previously-discussed product
_FOLLOW_UP_PRONOUNS = {"it", "its", "this", "that", "these", "those", "they", "them", "their", "one"}

# Per-session conversation history stored in memory
_conversation_history: dict[str, list[dict]] = {}

# Per-session pending add context: set when chatbot asks for missing options.
# Schema: { session_id: [{"product_id": int, "name": str, "price": float, "options": [...], "quantity": int}] }
_pending_add: dict[str, list[dict]] = {}

# Per-session pending bundle: stores pre-selected bundle items waiting for confirmation.
# Schema: { session_id: [{"product_id": int, "name": str, "price": float, "options": [...]}] }
_pending_bundle: dict[str, list[dict]] = {}


def _contextual_rag_query(query: str, session_id: str) -> str:
    """For follow-up queries that reference a prior product via pronouns
    (e.g. 'how much is it?', 'add it to cart', 'is it waterproof?'),
    prepend the last AI response so RAG retrieves the correct product.

    Queries that name a product explicitly ('what about the keyboard?',
    'add a yoga mat') are passed through unchanged.
    """
    words = query.lower().split()
    has_pronoun = bool(set(words) & _FOLLOW_UP_PRONOUNS)

    if not has_pronoun:
        return query  # explicit query — don't augment

    history = _conversation_history.get(session_id, [])
    if not history:
        return query

    # Ground the search in the last AI response (first 300 chars = product name + key facts)
    last_ai = history[-1].get("ai", "")[:300]
    return f"{last_ai} {query}"


_QUESTION_STOP_WORDS = {
    "what", "which", "who", "where", "when", "how", "why",
    "do", "does", "did", "can", "could", "would", "should", "is", "are", "was", "were",
    "you", "your", "have", "has", "i", "me", "my",
    "a", "an", "the", "any", "all", "some", "tell", "show", "list",
    "please", "got", "get", "give", "find", "look", "looking",
}


def _normalize_browse_query(query: str) -> str:
    """Strip question/filler words so 'What shoes do you have?' → 'shoes',
    giving the vector search a cleaner, more focused signal.
    Falls back to original query if stripping leaves nothing useful.
    """
    words = re.sub(r'[?!.,]', '', query.lower()).split()
    keywords = [w for w in words if w not in _QUESTION_STOP_WORDS and len(w) > 1]
    return " ".join(keywords) if keywords else query



_ADD_STRIP_WORDS = {
    "add", "can", "you", "please", "could", "a", "an", "the", "some",
    "to", "my", "cart", "i", "want", "buy", "order", "purchase",
    "put", "in", "get", "me", "need", "like", "give", "let", "have",
    "take", "also", "too", "also", "for",
}


def _rag_query_for_add(query: str, session_id: str) -> str:
    """Strip action/filler words from an add-to-cart query so RAG focuses on
    the product name. Falls back to contextual augmentation if only pronouns remain.
    Example: 'can you add 15 bamboo cutter' → 'bamboo cutter'
             'add it to cart'               → contextual (has pronoun)
    """
    words = query.lower().split()
    # Keep numeric quantities so RAG can still match e.g. "3 pack resistance bands"
    product_words = [w for w in words if w not in _ADD_STRIP_WORDS]
    stripped = " ".join(product_words).strip()
    if not stripped or bool(set(stripped.split()) & _FOLLOW_UP_PRONOUNS):
        return _contextual_rag_query(query, session_id)
    return stripped


def get_embeddings():
    """Real semantic embeddings via Ollama nomic-embed-text."""
    return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def get_llm():
    """LangChain ChatOllama — keep_alive=-1 keeps the model hot in memory.
    reasoning=False disables Qwen3 thinking mode so tokens stream immediately.
    """
    return ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,
        keep_alive=-1,
        num_predict=MAX_TOKENS,
        reasoning=REASONING,
    )


def build_vector_store():
    """Build ChromaDB vector store from product catalog using real embeddings.
    Always starts fresh — wipes any existing collection so restarts don't
    accumulate duplicate documents.
    """
    import shutil
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()

    documents = []
    for p in products:
        opts = json.loads(p.get("options") or "[]")
        options_text = ""
        if opts:
            options_lines = []
            for opt in opts:
                options_lines.append(f"  {opt['name']}: {', '.join(opt['values'])}")
            options_text = "\nAvailable options:\n" + "\n".join(options_lines)
        text = (
            f"Product: {p['name']}\n"
            f"Category: {p['category']}\n"
            f"Price: ${p['price']:.2f}\n"
            f"Description: {p['description']}\n"
            f"Stock: {p['stock']} units available"
            f"{options_text}\n"
            f"Product ID: {p['id']}"
        )
        doc = Document(
            page_content=text,
            metadata={"product_id": p["id"], "name": p["name"], "category": p["category"], "price": p["price"]},
        )
        documents.append(doc)

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )

    logger.info(f"Built vector store with {len(documents)} products")
    return vectorstore


def get_vector_store():
    """Load existing ChromaDB or build a fresh one."""
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=get_embeddings())
    return build_vector_store()


def search_products_rag(query: str, k: int = 5) -> list[dict]:
    """Semantic product search using real Ollama embeddings."""
    vectorstore = get_vector_store()
    results = vectorstore.similarity_search(query, k=k)

    products = []
    seen_ids = set()
    for doc in results:
        pid = doc.metadata.get("product_id")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            products.append({
                "product_id": pid,
                "name": doc.metadata.get("name", ""),
                "category": doc.metadata.get("category", ""),
                "price": doc.metadata.get("price", 0),
                "content": doc.page_content,
            })

    return products


def _parse_options_from_query(query_lower: str, product: dict) -> tuple[dict, list[str]]:
    """Try to match option values from the query against a product's options.
    Returns (matched_options_dict, missing_option_names).

    Matching passes (in order):
      1. Exact full-value substring ("all white" in query → 'All White')
         Short values (≤2 chars) use whole-word matching to avoid "m" in "mat" → 'M'
      2. Word→size-letter aliases ("large" → 'L', "medium" → 'M', etc.)
      3. Single-char whole-word tokens ("M", "S", "L")
      4. Token-level match with special rules for "/" compound values:
         - "/" values (e.g. "Black/White"): primary part MUST match
         - Space-separated values (e.g. "UK 11"): any numeric or 3+-char token matches
    """
    options = product.get("options") or []
    if not options:
        return {}, []

    # Normalise "uk9" → "uk 9" so "UK 9" tokens can match
    normalised = re.sub(r'\b(uk|us|eu|size)(\d+)\b', r'\1 \2', query_lower)
    query_words = set(re.split(r'[\s/,\-]+', normalised))

    _SIZE_WORDS = {
        "xsmall": "XS", "extra small": "XS",
        "small": "S",
        "medium": "M",
        "large": "L",
        "xlarge": "XL", "extra large": "XL",
        "xxlarge": "XXL", "double extra large": "XXL",
    }

    matched = {}
    missing = []
    for opt in options:
        opt_name = opt["name"]
        found_val = None
        opt_values_set = set(opt["values"])

        # Pass 1: exact full-value substring match
        # Short values (≤2 chars) require whole-word match to avoid "m" substring in "mat"
        for val in opt["values"]:
            val_lower = val.lower()
            if len(val_lower) <= 2:
                if re.search(r'\b' + re.escape(val_lower) + r'\b', normalised):
                    found_val = val
                    break
            elif val_lower in normalised:
                found_val = val
                break

        # Pass 2: word→size-letter aliases ("large" → 'L')
        if not found_val and opt_name == "Size":
            for word, letter in _SIZE_WORDS.items():
                if re.search(r'\b' + re.escape(word) + r'\b', normalised) and letter in opt_values_set:
                    found_val = letter
                    break

        # Pass 3: single-char whole-word tokens ("M", "S", "L")
        if not found_val:
            for val in opt["values"]:
                if len(val) == 1 and val.lower() in query_words:
                    found_val = val
                    break

        # Pass 4: token-level partial match
        # For slash-compound values (e.g. "Black/White") the PRIMARY colour must appear.
        # For space-separated values (e.g. "UK 11") any digit or 3+-char alpha token matches.
        if not found_val:
            best_score = 0
            best_val = None
            for val in opt["values"]:
                val_lower = val.lower()
                if '/' in val_lower:
                    primary_tokens = re.split(r'[\s\-]+', val_lower.split('/')[0])
                    primary_match = any(len(t) > 2 and t in query_words for t in primary_tokens)
                    if not primary_match:
                        continue
                    score = 2
                    sec_tokens = re.split(r'[\s\-]+', val_lower.split('/')[-1])
                    if any(len(t) > 2 and t in query_words for t in sec_tokens):
                        score += 1
                else:
                    val_tokens = re.split(r'[\s/,\-]+', val_lower)
                    score = sum(
                        2 if t.isdigit() and t in query_words else
                        1 if len(t) > 2 and t in query_words else 0
                        for t in val_tokens if t
                    )
                if score > best_score:
                    best_score = score
                    best_val = val
            if best_val:
                found_val = best_val

        if found_val:
            matched[opt_name] = found_val
        else:
            missing.append(opt_name)
    return matched, missing


_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a couple": 2, "a pair": 2, "a few": 3,
}


def _parse_quantity(query_lower: str) -> int:
    """Extract intended quantity from a query.
    Word numbers ('two', 'three') take priority over digit sequences
    so 'add two size 9 shoes' → 2, not 9.
    """
    for word, val in _WORD_NUMBERS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', query_lower):
            return val
    # Fall back to first digit found that looks like a count (not a size like 9 or 10)
    # Heuristic: if preceded by "size", "uk", "us" or followed by "inch" treat as spec, not qty
    for m in re.finditer(r'\b(\d+)\b', query_lower):
        start = m.start()
        prefix = query_lower[max(0, start - 6):start].strip()
        if any(prefix.endswith(p) for p in ("size", "uk", "us", "inch", "cm", "mm", "l", "xl")):
            continue
        val = int(m.group(1))
        if 1 <= val <= 99:
            return val
    return 1


def _split_multi_add(query_lower: str) -> list[str]:
    """Split a multi-item add request into individual item strings.

    Handles two patterns:
      A) shared product at end: 'black uk6 and navy uk8 of running shoes'
         → ['black uk6 running shoes', 'navy uk8 running shoes']
      B) product per part: 'black uk11 trail running shoes and white uk8 trail running shoes'
         → ['black uk11 trail running shoes', 'white uk8 trail running shoes']
    """
    # Strip leading action phrase from the whole query
    cleaned = re.sub(
        r'^(?:add|can you add|could you add|please add|i want to add|buy|get me|purchase'
        r'|i need|i want|i\'d like|give me|let me have|i\'ll take)\s+',
        '', query_lower
    ).strip()

    parts = re.split(r'\s+and\s+', cleaned)
    if len(parts) <= 1:
        return [query_lower]

    # Pattern A: detect shared product via "of <product>" at end of any part
    shared_product = None
    cleaned_parts = []
    for part in parts:
        m = re.search(r'\bof\s+([a-z][a-z\s]+)$', part.strip())
        if m:
            shared_product = m.group(1).strip()
            cleaned_parts.append(re.sub(r'\bof\s+[a-z][a-z\s]+$', '', part).strip())
        else:
            cleaned_parts.append(part.strip())

    result = []
    for part in cleaned_parts:
        item = part.strip()
        # If shared product found and this part doesn't already contain the product words,
        # append it so RAG can find the right product
        if shared_product:
            # Check if the shared product name is already in this part
            shared_words = set(shared_product.split())
            part_words = set(item.split())
            if not (shared_words & part_words):
                item = f"{item} {shared_product}"
        result.append(item.strip())

    return result


def _rerank_by_name_match(sub_query: str, candidates: list) -> list:
    """Re-rank add candidates so the product whose name best matches the query ranks first.

    Vector similarity alone can rank 'Running Shoes' above 'Trail Running Shoes'
    for a query that literally says 'trail running shoes'. This corrects that by
    counting how many words of the product name appear in the query.
    """
    q = re.sub(r'[^a-z0-9\s]', '', sub_query.lower())
    q_words = set(q.split())

    def _score(c: dict) -> int:
        name = re.sub(r'[^a-z0-9\s]', '', c["name"].lower())
        # Full name substring: longer name = more specific match wins
        if name in q:
            return 1000 + len(name)
        name_words = set(name.split())
        return len(name_words & q_words)

    return sorted(candidates, key=_score, reverse=True)


def _detect_add_to_cart(query_lower: str) -> bool:
    """Detect explicit add-to-cart intent from user message."""
    browse_phrases = [
        "show me", "what do you have", "what are", "list", "browse",
        "find me all", "all your", "do you have", "do you sell",
        "what kind", "what type", "recommend", "suggest", "tell me about",
    ]
    if any(p in query_lower for p in browse_phrases):
        return False
    add_phrases = [
        "add to cart", "add it to cart", "add to my cart",
        "add the", "add a", "add an", "add some",
        "can you add", "could you add", "please add", "i want to add",
        "buy the", "buy a", "buy an", "purchase the", "purchase a",
        "i want to buy", "i'd like to buy",
        "i want to order", "order the", "order a",
        "put in cart", "put in my cart",
        "i need", "i want", "i'd like", "get me",
        "give me", "let me have", "i'll take",
    ]
    return (
        any(p in query_lower for p in add_phrases)
        or re.search(r"\badd\s+\d+\s+\w+", query_lower) is not None
        or re.match(r"^add\s+\d*\s*\w+", query_lower) is not None
    )


def _cart_item_matches_query(item: dict, query_lower: str) -> bool:
    """Check if a cart item's product name matches the query.
    Uses prefix matching to handle plurals (t-shirt/t-shirts, bag/bags, etc.)
    and short common words (≤2 chars) are ignored to avoid false matches.
    """
    name_words = {w for w in item["product"]["name"].lower().split() if len(w) > 2}
    query_words = {w for w in query_lower.split() if len(w) > 2}
    # Exact intersection first
    if name_words & query_words:
        return True
    # Prefix match: query word starts with a name word or vice versa
    for nw in name_words:
        for qw in query_words:
            if qw.startswith(nw) or nw.startswith(qw):
                return True
    return False


def _detect_update_quantity(query_lower: str) -> tuple[bool, int | None]:
    """Return (is_quantity_update, new_quantity).
    Matches phrases like: 'reduce to 1', 'change quantity to 3', 'update to 2',
    'make it 2', 'set quantity to 1', 'only want 1', 'just 1', 'decrease to 2'.
    Returns (False, None) if not a quantity update.
    """
    update_phrases = [
        "reduce to", "reduce it to", "change to", "change quantity to",
        "update to", "update quantity to", "set to", "set quantity to",
        "make it", "make that", "only want", "just want", "decrease to",
        "lower to", "bring it down to", "quantity to", "qty to",
    ]
    matched = any(p in query_lower for p in update_phrases)
    if not matched:
        return False, None
    qty_match = re.search(r'\b(\d+)\b', query_lower)
    if qty_match:
        return True, int(qty_match.group(1))
    return False, None


def _detect_remove_from_cart(query_lower: str) -> bool:
    remove_phrases = ["remove", "delete", "take out", "don't want", "dont want",
                      "get rid of", "drop the", "drop it"]
    return any(p in query_lower for p in remove_phrases)


def _detect_clear_cart(query_lower: str) -> bool:
    clear_phrases = ["clear my cart", "empty my cart", "clear cart", "empty cart",
                     "remove everything", "remove all", "start over", "wipe my cart"]
    return any(p in query_lower for p in clear_phrases)


def _detect_bundle_request(query_lower: str) -> bool:
    phrases = [
        "build me", "build a", "recommend a bundle", "suggest a bundle",
        "complete setup", "full setup", "starter kit", "bundle for",
        "what do i need for", "what should i get for", "setup for",
        "recommend a complete", "suggest a complete", "full kit",
        "gaming setup", "gaming pc", "home office setup", "workout bundle",
    ]
    return any(p in query_lower for p in phrases)


def _detect_bundle_confirm(query_lower: str) -> bool:
    """Detect user confirmation to add a pending bundle to cart."""
    phrases = [
        "yes", "sure", "go ahead", "do it", "sounds good", "perfect", "great",
        "add them", "add all", "add them all", "add everything", "add to cart",
        "add them to cart", "add it all", "add the bundle", "yes please",
        "add those", "add those to cart", "put them in", "add all of them",
    ]
    return any(p in query_lower for p in phrases)


def _detect_reorder(query_lower: str) -> bool:
    phrases = [
        "reorder", "order again", "buy again", "same as last time",
        "same as before", "last order", "previous order", "order the same",
        "what did i order", "what did i buy", "my order history",
        "repeat my order", "repeat last order",
    ]
    return any(p in query_lower for p in phrases)


def _get_order_history(session_id: str) -> list[dict]:
    """Fetch the last 3 orders for this session from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id, o.created_at, o.total, o.status,
               oi.product_id, oi.product_name, oi.quantity, oi.price,
               oi.selected_options
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.session_id = ?
        ORDER BY o.created_at DESC
        LIMIT 30
    """, (session_id,))
    rows = cur.fetchall()
    conn.close()

    orders = {}
    for row in rows:
        oid = row[0]
        if oid not in orders:
            orders[oid] = {
                "order_id": oid,
                "created_at": row[1],
                "total": row[2],
                "status": row[3],
                "items": [],
            }
        opts = json.loads(row[8]) if row[8] else {}
        orders[oid]["items"].append({
            "product_id": row[4],
            "name": row[5],
            "quantity": row[6],
            "price": row[7],
            "selected_options": opts,
        })
    return list(orders.values())[:3]


def _detect_comparison(query_lower: str) -> tuple[bool, str, str]:
    """Returns (is_comparison, product_a_hint, product_b_hint)."""
    compare_phrases = [
        "compare", "difference between", "vs ", "versus", "better",
        "which is better", "what's the difference", "which should i",
        "which one is", "help me choose between",
    ]
    is_compare = any(p in query_lower for p in compare_phrases)
    if not is_compare:
        return False, "", ""

    split_pattern = r'\s+(?:vs\.?|versus|and|or|between|,)\s+'
    parts = re.split(split_pattern, query_lower)

    stop = {"compare", "the", "a", "an", "between", "which", "is", "better", "should", "i", "buy", "get"}
    cleaned = []
    for p in parts:
        words = [w for w in p.split() if w not in stop]
        if words:
            cleaned.append(" ".join(words))

    if len(cleaned) >= 2:
        return True, cleaned[0].strip(), cleaned[1].strip()
    elif len(cleaned) == 1:
        return True, cleaned[0].strip(), ""
    return True, "", ""


def _build_cart_context(session_id: str) -> tuple[str, dict]:
    """Fetch the real cart and return a human-readable summary + raw cart dict."""
    from crud import get_cart
    cart = get_cart(session_id)
    if not cart["items"]:
        return "Customer's cart is currently empty.", cart
    lines = []
    for item in cart["items"]:
        opts = item.get("selected_options") or {}
        opts_str = (", ".join(f"{k}: {v}" for k, v in opts.items()))
        opts_str = f" [{opts_str}]" if opts_str else ""
        subtotal = item["product"]["price"] * item["quantity"]
        lines.append(
            f"  • {item['product']['name']}{opts_str} × {item['quantity']} "
            f"@ ${item['product']['price']:.2f} = ${subtotal:.2f}"
        )
    summary = (
        f"Customer's current cart ({len(cart['items'])} item(s), "
        f"total ${cart['total']:.2f}):\n" + "\n".join(lines)
    )
    return summary, cart


def _build_chat_messages(query: str, session_id: str) -> tuple[list, bool, list[dict], str]:
    """Shared setup: product search, cart action, prompt assembly.
    Returns (messages, cart_updated, relevant_products, user_content).
    user_content is the enriched human message (query + product context) — store
    this in history so future turns have the right product grounding even when
    follow-up queries are too vague for RAG to retrieve correctly on their own.
    """
    from crud import add_to_cart as cart_add, get_all_products, remove_from_cart as cart_remove, clear_cart as cart_clear, update_cart_item as cart_update_qty

    query_lower = query.lower()
    cart_updated = False
    cart_action_note = ""

    _is_qty_update, _new_qty = _detect_update_quantity(query_lower)

    # ── Cart mutation actions ─────────────────────────────────────────────────
    # 1. Bundle item removal — catches "remove X" / "don't want X" when a bundle is pending
    #    Must run before bundle_confirm and before cart remove so it edits the list, not the cart.
    if session_id in _pending_bundle and _pending_bundle[session_id]:
        removal_phrases = [
            "remove", "don't want", "dont want", "not the", "without", "exclude",
            "drop", "skip", "leave out", "no ", "take off", "take out",
        ]
        if any(p in query_lower for p in removal_phrases):
            bundle = _pending_bundle[session_id]
            removed = []
            kept = []
            for item in bundle:
                # Check if the item name (any word) appears near a removal phrase
                name_words = [w for w in re.sub(r"[^a-z0-9 ]", "", item["name"].lower()).split() if len(w) > 2]
                if any(w in query_lower for w in name_words):
                    removed.append(item["name"])
                else:
                    kept.append(item)
            if removed:
                _pending_bundle[session_id] = kept
                removed_str = ", ".join(removed)
                kept_str = "\n".join(f"  • {i['name']} — ${i['price']:.2f}" for i in kept)
                total_kept = sum(i["price"] for i in kept)
                cart_action_note = (
                    f"BUNDLE UPDATED: Removed {removed_str} from the bundle. "
                    f"Updated bundle ({len(kept)} items, ${total_kept:.2f}):\n{kept_str}\n"
                    f"Tell the user the item was removed and show the updated list. "
                    f"Ask if they'd like to add the remaining items or make further changes."
                )

    # 2. Bundle confirm — catches "yes/add them" before generic add_to_cart
    if not cart_action_note and session_id in _pending_bundle and _pending_bundle[session_id] and _detect_bundle_confirm(query_lower):
        bundle_items = _pending_bundle.pop(session_id)
        action_notes = []
        any_added = False

        for item in bundle_items:
            # Extract options for this specific item from the user's message
            # e.g. "Intel LGA1700 for the CPU, 32GB DDR5-6000 for the RAM"
            selected_options, missing = _parse_options_from_query(query_lower, item)

            if not missing:
                try:
                    cart_add(session_id, item["product_id"], 1, selected_options)
                    opts_text = (f" ({', '.join(f'{k}: {v}' for k, v in selected_options.items())})"
                                 if selected_options else "")
                    action_notes.append(f"CART ACTION COMPLETED: Added {item['name']}{opts_text} (${item['price']:.2f}).")
                    any_added = True
                except ValueError as e:
                    action_notes.append(f"CART ACTION FAILED: {item['name']} — {e}")
            else:
                # Queue to pending_add for option collection
                _pending_add.setdefault(session_id, []).append({
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "price": item["price"],
                    "options": item["options"],
                    "quantity": 1,
                    "already_selected": selected_options,
                })
                opts_summary = "; ".join(
                    f"{o['name']}: {', '.join(o['values'])}"
                    for o in item["options"] if o["name"] in missing
                )
                action_notes.append(
                    f"NEED OPTIONS: Cannot add {item['name']} yet. Please ask customer to choose: {opts_summary}"
                )

        if any_added:
            cart_updated = True
        cart_action_note = " | ".join(action_notes)

    elif not cart_action_note and _detect_clear_cart(query_lower):
        try:
            cart_clear(session_id)
            cart_updated = True
            cart_action_note = "CART ACTION COMPLETED: Cart has been cleared successfully."
        except Exception as e:
            cart_action_note = f"CART ACTION FAILED: {e}"

    elif _is_qty_update:
        _, cart_data = _build_cart_context(session_id)
        updated = False
        for item in cart_data.get("items", []):
            if _cart_item_matches_query(item, query_lower):
                try:
                    if _new_qty is not None and _new_qty <= 0:
                        cart_remove(session_id, item["product_id"])
                        cart_action_note = f"CART ACTION COMPLETED: Removed {item['product']['name']} from cart (quantity set to 0)."
                    else:
                        cart_update_qty(session_id, item["product_id"], _new_qty)
                        cart_action_note = (
                            f"CART ACTION COMPLETED: Updated {item['product']['name']} quantity to {_new_qty}."
                        )
                    cart_updated = True
                    updated = True
                except Exception as e:
                    cart_action_note = f"CART ACTION FAILED: {e}"
                break
        if not updated and not cart_action_note:
            cart_action_note = "CART ACTION FAILED: Could not find that item in the cart to update."

    elif _detect_remove_from_cart(query_lower):
        _, cart_data = _build_cart_context(session_id)
        removed = False
        for item in cart_data.get("items", []):
            if _cart_item_matches_query(item, query_lower):
                try:
                    cart_remove(session_id, item["product_id"])
                    cart_updated = True
                    cart_action_note = (
                        f"CART ACTION COMPLETED: Removed {item['product']['name']} from cart."
                    )
                    removed = True
                except Exception as e:
                    cart_action_note = f"CART ACTION FAILED: {e}"
                break
        if not removed and not cart_action_note:
            cart_action_note = "CART ACTION FAILED: Could not find that item in the cart."

    elif _detect_add_to_cart(query_lower):
        from crud import get_product
        sub_items = _split_multi_add(query_lower)
        action_notes = []
        any_added = False

        for sub in sub_items:
            rag_query = _rag_query_for_add(sub, session_id)
            add_candidates = search_products_rag(rag_query, k=3)
            add_candidates = _rerank_by_name_match(sub, add_candidates)
            if not add_candidates:
                action_notes.append(f"CART ACTION FAILED: No matching product found for '{sub}'.")
                continue
            try:
                quantity = _parse_quantity(sub)
                best = add_candidates[0]
                full_product = get_product(best["product_id"])
                selected_options, missing = _parse_options_from_query(sub, full_product)

                if missing:
                    opts_summary = "; ".join(
                        f"{o['name']}: {', '.join(o['values'])}"
                        for o in (full_product.get("options") or [])
                        if o["name"] in missing
                    )
                    # Store pending context so the next reply can complete the add
                    _pending_add.setdefault(session_id, []).append({
                        "product_id": best["product_id"],
                        "name": best["name"],
                        "price": best["price"],
                        "image": full_product.get("image_url") or "",
                        "options": full_product.get("options") or [],
                        "quantity": quantity,
                        "already_selected": selected_options,
                    })
                    action_notes.append(
                        f"NEED OPTIONS: Cannot add {best['name']} yet. "
                        f"Please ask the customer to choose: {opts_summary}"
                    )
                else:
                    qty_text = f"{quantity}x " if quantity > 1 else ""
                    opts_text = (
                        f" ({', '.join(f'{k}: {v}' for k, v in selected_options.items())})"
                        if selected_options else ""
                    )
                    cart_add(session_id, best["product_id"], quantity, selected_options)
                    any_added = True
                    action_notes.append(
                        f"CART ACTION COMPLETED: Added {qty_text}{best['name']}{opts_text} "
                        f"(${best['price']:.2f} each) to cart successfully."
                    )
            except ValueError as e:
                action_notes.append(f"CART ACTION FAILED: {e}")

        if any_added:
            cart_updated = True
        cart_action_note = " | ".join(action_notes)

    # ── Resolve pending add: user replied with missing options ────────────────
    elif session_id in _pending_add and _pending_add[session_id]:
        action_notes = []
        any_added = False
        remaining_pending = []

        for pending in _pending_add[session_id]:
            # Try to find a product-specific section in the reply, e.g.
            # "running shoes: black uk8" or "trail shoes - navy uk9"
            # Fall back to the whole message if no product mention found.
            product_name_lower = pending["name"].lower()
            # Also match shortened product names (first word, or "trail" for "trail running shoes")
            name_tokens = product_name_lower.split()
            # Build a pattern that matches any contiguous subset of the product name
            search_patterns = [product_name_lower] + name_tokens
            parse_context = query_lower  # default: whole message
            for pat in search_patterns:
                if len(pat) < 4:
                    continue
                m = re.search(
                    r'\b' + re.escape(pat) + r'[s]?\s*[:–\-,]?\s*([^.!?\n]+)',
                    query_lower
                )
                if m:
                    parse_context = m.group(1).strip()
                    break

            # Also handle "and [options]" sub-items within the section
            # e.g. "black uk8 and gray uk10" → try to split into individual sub-items
            sub_contexts = re.split(r'\s+and\s+', parse_context)

            for sub_ctx in sub_contexts:
                fake_product = {"options": pending["options"]}
                selected_options, missing_opts = _parse_options_from_query(sub_ctx, fake_product)
                merged = {**pending.get("already_selected", {}), **selected_options}
                still_missing = [o["name"] for o in pending["options"] if o["name"] not in merged]

                if not still_missing:
                    try:
                        qty_text = f"{1}x " if 1 > 1 else ""
                        opts_text = (
                            f" ({', '.join(f'{k}: {v}' for k, v in merged.items())})"
                            if merged else ""
                        )
                        cart_add(session_id, pending["product_id"], 1, merged)
                        any_added = True
                        action_notes.append(
                            f"CART ACTION COMPLETED: Added {pending['name']}{opts_text} "
                            f"(${pending['price']:.2f} each) to cart successfully."
                        )
                    except ValueError as e:
                        action_notes.append(f"CART ACTION FAILED: {e}")
                else:
                    # Still missing — keep one pending entry and ask again
                    pending["already_selected"] = merged
                    remaining_pending.append(dict(pending))
                    opts_summary = "; ".join(
                        f"{o['name']}: {', '.join(o['values'])}"
                        for o in pending["options"]
                        if o["name"] in still_missing
                    )
                    action_notes.append(
                        f"NEED OPTIONS: Still cannot add {pending['name']}. "
                        f"Still need: {opts_summary}"
                    )
                    break  # only add one pending per product

        _pending_add[session_id] = remaining_pending
        if not remaining_pending:
            del _pending_add[session_id]

        if any_added:
            cart_updated = True
        cart_action_note = " | ".join(action_notes)

    elif _detect_comparison(query_lower)[0]:
        _, hint_a, hint_b = _detect_comparison(query_lower)
        from crud import get_product

        products_a = _rerank_by_name_match(hint_a, search_products_rag(hint_a, k=3)) if hint_a else []
        products_b = _rerank_by_name_match(hint_b, search_products_rag(hint_b, k=3)) if hint_b else []

        compare_parts = []

        if products_a:
            pa = get_product(products_a[0]["product_id"])
            if pa:
                opts_a = "; ".join(
                    f"{o['name']}: {', '.join(o['values'])}" for o in (pa.get("options") or [])
                )
                compare_parts.append(
                    f"PRODUCT A — {pa['name']} | ${pa['price']:.2f} | {pa['category']}\n"
                    f"Description: {pa['description']}\n"
                    f"Options: {opts_a or 'None'}\n"
                    f"Stock: {pa['stock']}"
                )

        if products_b:
            pb = get_product(products_b[0]["product_id"])
            if pb:
                opts_b = "; ".join(
                    f"{o['name']}: {', '.join(o['values'])}" for o in (pb.get("options") or [])
                )
                compare_parts.append(
                    f"PRODUCT B — {pb['name']} | ${pb['price']:.2f} | {pb['category']}\n"
                    f"Description: {pb['description']}\n"
                    f"Options: {opts_b or 'None'}\n"
                    f"Stock: {pb['stock']}"
                )

        if compare_parts:
            cart_action_note = (
                "COMPARISON REQUEST: Generate a clear side-by-side comparison of these products. "
                "Include price, key features, pros/cons, and a recommendation. Use a simple comparison format.\n\n"
                + "\n\n".join(compare_parts)
            )
        else:
            cart_action_note = "COMPARISON REQUEST: Could not find the products to compare. Ask the customer to clarify which products they want to compare."

    elif _detect_reorder(query_lower):
        order_history = _get_order_history(session_id)
        if not order_history:
            cart_action_note = "REORDER INFO: This customer has no previous orders. Let them know and offer to help find products."
        else:
            history_lines = []
            for order in order_history:
                items_str = ", ".join(
                    f"{i['quantity']}x {i['name']}" + (
                        f" ({', '.join(f'{k}: {v}' for k, v in i['selected_options'].items())})"
                        if i['selected_options'] else ""
                    )
                    for i in order['items']
                )
                history_lines.append(
                    f"Order #{order['order_id']} on {order['created_at'][:10]} "
                    f"(${order['total']:.2f}, {order['status']}): {items_str}"
                )
            history_text = "\n".join(history_lines)

            wants_reorder = any(p in query_lower for p in ["reorder", "order again", "buy again", "add them", "add it", "yes"])

            if wants_reorder and order_history:
                from crud import add_to_cart as cart_add
                last_order = order_history[0]
                added = []
                for item in last_order["items"]:
                    try:
                        cart_add(session_id, item["product_id"], item["quantity"], item["selected_options"])
                        added.append(item["name"])
                        cart_updated = True
                    except Exception:
                        pass
                if added:
                    cart_action_note = (
                        f"REORDER COMPLETED: Re-added {len(added)} items from Order #{last_order['order_id']} to cart: "
                        + ", ".join(added)
                    )
                else:
                    cart_action_note = f"REORDER INFO: Found previous orders but couldn't re-add items. Order history:\n{history_text}"
            else:
                cart_action_note = f"REORDER INFO: Customer's order history:\n{history_text}\nAsk which order they'd like to reorder, or offer to reorder the most recent one."

    elif _detect_bundle_request(query_lower):
        from crud import get_all_products, get_product
        all_products = get_all_products()

        budget_match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:budget|dollars?|usd)?', query_lower)
        budget = float(budget_match.group(1).replace(',', '')) if budget_match else None

        # Use RAG to find the most relevant products for this bundle query
        bundle_candidates = search_products_rag(query, k=12)
        bundle_candidates = [get_product(c["product_id"]) for c in bundle_candidates]
        bundle_candidates = [p for p in bundle_candidates if p]  # filter None

        # Apply budget filter (single item shouldn't exceed 60% of budget)
        if budget:
            bundle_candidates = [p for p in bundle_candidates if p['price'] <= budget * 0.6]

        # Deduplicate by product type (first 2 words of name, lowercased).
        # This lets multiple "Computer Components" items (CPU, GPU, RAM, SSD…) all
        # appear together while still preventing near-duplicate products.
        _stop = {"the", "a", "an", "for", "with", "and", "or", "of"}
        def _type_key(name: str) -> str:
            words = [w for w in re.sub(r"[^a-z0-9 ]", "", name.lower()).split() if w not in _stop]
            return " ".join(words[:2])

        seen_types: dict[str, dict] = {}
        for p in bundle_candidates:
            key = _type_key(p['name'])
            if key not in seen_types or p['price'] < seen_types[key]['price']:
                seen_types[key] = p

        # Build selected bundle (max 6 items, in RAG relevance order)
        seen_ids = {p['id'] for p in seen_types.values()}
        selected = [p for p in bundle_candidates if p['id'] in seen_ids][:6]

        if selected:
            # Store as pending bundle for this session (include image for frontend UI)
            _pending_bundle[session_id] = [
                {
                    "product_id": p['id'],
                    "name": p['name'],
                    "price": p['price'],
                    "image": p.get('image_url') or "",
                    "options": p.get('options') or [],
                    "category": p['category'],
                }
                for p in selected
            ]

            items_text = "\n".join(
                f"  • {p['name']} ({p['category']}) — ${p['price']:.2f}"
                + (f" [needs: {', '.join(o['name'] for o in (p.get('options') or []))}]" if p.get('options') else "")
                for p in selected
            )
            total = sum(p['price'] for p in selected)
            budget_note = f"Budget: ${budget:.0f}" if budget else ""
            cart_action_note = (
                f"BUNDLE READY: Python has pre-selected these {len(selected)} items for the bundle "
                f"(stored and ready to add to cart when user confirms).\n"
                f"{budget_note}\n"
                f"Bundle items:\n{items_text}\n"
                f"Bundle total: ${total:.2f}\n"
                f"Present these items as a simple bullet list with names and prices — "
                f"DO NOT generate a comparison table. "
                f"Tell the customer an interactive card will appear below where they can select options (size, brand, etc.) and add all items to cart with one click. "
                f"Keep your response short and friendly."
            )
        else:
            cart_action_note = "BUNDLE REQUEST: No suitable products found for this bundle. Ask the customer to clarify what they're looking for."


    # ── RAG product search (context-augmented for vague follow-ups) ───────────
    rag_query = _contextual_rag_query(query, session_id)
    # For browse queries with no pronouns, also try a keyword-stripped version
    # so "What shoes do you have?" searches "shoes" not the full noisy sentence
    if rag_query == query:
        rag_query = _normalize_browse_query(query)
    relevant_products = search_products_rag(rag_query, k=5)

    if relevant_products:
        context_parts = []
        for p in relevant_products[:5]:
            desc = p["content"].split("Description: ")[-1].split("\n")[0]
            opts_section = ""
            if "Available options:" in p["content"]:
                opts_raw = p["content"].split("Available options:\n")[-1].split("Product ID:")[0].strip()
                opts_section = f" | Options: {opts_raw.replace(chr(10), '; ')}"
            context_parts.append(
                f"- {p['name']} | {p['category']} | ${p['price']:.2f}{opts_section} | {desc}"
            )
        product_context = "\n".join(context_parts)
    else:
        all_prods = get_all_products()
        cats = list(set(p["category"] for p in all_prods))
        product_context = f"No closely matching products. Available categories: {', '.join(cats)}"

    # ── Real cart state (always fetched fresh) ───────────────────────────────
    cart_context, _ = _build_cart_context(session_id)

    # ── Prompt assembly ──────────────────────────────────────────────────────
    system_prompt = (
        "You are a knowledgeable, friendly shopping assistant for an online e-commerce store. "
        "Your job is to help customers find products, compare options, answer questions about items, "
        "and provide thoughtful recommendations. "
        "You are given the customer's REAL current cart contents — always use this for any cart-related questions. "
        "Never guess or invent cart contents; only report what is shown in the cart context. "
        "When a cart action has been completed, naturally acknowledge it in your response. "
        "When asked for a bundle or setup, suggest 3-6 complementary products from the catalog, list them with prices, give a total, and ask if they want them all added to cart. "
        "When asked to compare products, give a clear side-by-side comparison with price, features, pros/cons, and a final recommendation. "
        "Be conversational, helpful, and concise (under 150 words). "
        "Format prices with a $ sign. Do not make up products that are not in the catalog context."
    )

    user_content = f"Customer: {query}"
    if cart_action_note:
        user_content += f"\n\n[System: {cart_action_note}]"
    user_content += f"\n\n{cart_context}"
    user_content += f"\n\nRelevant products from catalog:\n{product_context}"

    history = _conversation_history.get(session_id, [])
    messages = [SystemMessage(content=system_prompt)]
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append(HumanMessage(content=turn["human"]))
        messages.append(AIMessage(content=turn["ai"]))
    messages.append(HumanMessage(content=user_content))

    return messages, cart_updated, relevant_products, user_content


def generate_chat_response(query: str, session_id: str) -> dict:
    """Generate a response using RAG retrieval + Ollama LLM with conversation memory."""
    messages, cart_updated, relevant_products, user_content = _build_chat_messages(query, session_id)

    llm = get_llm()
    ai_message = llm.invoke(messages)
    response_text = ai_message.content.strip()

    # Store enriched user_content (with product context) so future follow-up
    # queries have the right product grounding in conversation history.
    _conversation_history.setdefault(session_id, []).append({"human": user_content, "ai": response_text})

    return {
        "response": response_text,
        "cart_updated": cart_updated,
        "products_mentioned": [
            {"id": p["product_id"], "name": p["name"], "price": p["price"]}
            for p in relevant_products[:3]
        ],
    }


async def stream_chat_response(query: str, session_id: str):
    """Async generator that streams LLM tokens as SSE-ready dicts via LangChain.
    ChatOllama with reasoning=False disables Qwen3 thinking mode so chunk.content
    carries real tokens from the first response token.

    Yields:
        {"type": "chunk", "content": "<token>"}  — one per LLM token
        {"type": "done", "cart_updated": bool, "products_mentioned": [...]}
    """
    messages, cart_updated, relevant_products, user_content = _build_chat_messages(query, session_id)

    llm = get_llm()
    full_response = ""

    async for chunk in llm.astream(messages):
        # With reasoning=False, chunk.content carries answer tokens directly
        text = chunk.content
        if text:
            full_response += text
            yield {"type": "chunk", "content": text}

    # Store enriched user_content in history (not raw query) so vague follow-ups
    # in future turns still have the right product context to draw from.
    _conversation_history.setdefault(session_id, []).append({"human": user_content, "ai": full_response})

    # If a bundle was just pre-selected, include it so the frontend can render
    # an interactive option-picker card (user won't need to type options).
    pending = _pending_bundle.get(session_id) or []

    # If products are waiting on option selection, send them for interactive UI
    pending_options = _pending_add.get(session_id) or []

    yield {
        "type": "done",
        "cart_updated": cart_updated,
        "products_mentioned": [
            {"id": p["product_id"], "name": p["name"], "price": p["price"]}
            for p in relevant_products[:3]
        ],
        "bundle_items": pending if pending else None,
        "pending_options": pending_options if pending_options else None,
    }
