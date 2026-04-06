import json
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import init_db, seed_products
from schemas import (
    CartItemCreate, CartResponse, ChatMessage, ChatResponse,
    OrderCreate, Order, Product, ProductCreate,
)
import crud
from rag import generate_chat_response, stream_chat_response, build_vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up e-commerce API...")
    init_db()
    seed_products()
    try:
        build_vector_store()
        logger.info("Vector store built successfully")
    except Exception as e:
        logger.warning(f"Could not build vector store: {e}")
    # Warm up the LLM so the first real request isn't slow
    try:
        from rag import get_llm
        get_llm().invoke("hi")
        logger.info("LLM warmed up successfully")
    except Exception as e:
        logger.warning(f"LLM warm-up failed (non-fatal): {e}")
    yield
    logger.info("Shutting down e-commerce API...")


app = FastAPI(
    title="E-Commerce API",
    description="Full-stack e-commerce platform with RAG-powered chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Products ───────────────────────────────────────────────

@app.get("/api/products", response_model=list[Product])
def list_products(
    category: str | None = Query(None),
    search: str | None = Query(None),
):
    logger.info(f"GET /api/products category={category} search={search}")
    return crud.get_all_products(category=category, search=search)


@app.get("/api/products/search/semantic", response_model=list[Product])
def semantic_search(q: str = Query(..., description="Semantic search query")):
    """Semantic product search using ChromaDB vector similarity."""
    from rag import search_products_rag
    if not q or not q.strip():
        return []
    raw = search_products_rag(q.strip(), k=12)
    results = []
    seen = set()
    for item in raw:
        pid = item["product_id"]
        if pid in seen:
            continue
        seen.add(pid)
        product = crud.get_product(pid)
        if product:
            results.append(product)
    return results


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    product = crud.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/products/{product_id}/similar", response_model=list[Product])
def get_similar_products(product_id: int, limit: int = 4):
    """Return similar products using vector similarity, excluding the product itself."""
    from rag import search_products_rag

    product = crud.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = f"{product['name']} {product['category']} {product['description'][:120]}"

    similar_raw = search_products_rag(query, k=limit + 2)

    similar_ids = [
        p["product_id"] for p in similar_raw
        if p["product_id"] != product_id
    ][:limit]

    results = []
    for pid in similar_ids:
        p = crud.get_product(pid)
        if p:
            results.append(p)
    return results


# ─── Cart ────────────────────────────────────────────────────

@app.get("/api/cart/{session_id}", response_model=CartResponse)
def get_cart(session_id: str):
    return crud.get_cart(session_id)


@app.post("/api/cart/{session_id}/add", response_model=CartResponse)
def add_to_cart(session_id: str, item: CartItemCreate):
    try:
        return crud.add_to_cart(session_id, item.product_id, item.quantity, item.selected_options)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/cart/{session_id}/update", response_model=CartResponse)
def update_cart(session_id: str, item: CartItemCreate):
    return crud.update_cart_item(session_id, item.product_id, item.quantity)


@app.delete("/api/cart/{session_id}/remove/{product_id}", response_model=CartResponse)
def remove_from_cart(session_id: str, product_id: int):
    return crud.remove_from_cart(session_id, product_id)


@app.delete("/api/cart/{session_id}/clear", response_model=CartResponse)
def clear_cart(session_id: str):
    return crud.clear_cart(session_id)


class BundleCartItem(BaseModel):
    product_id: int
    selected_options: dict = {}

class BundleCartCreate(BaseModel):
    items: list[BundleCartItem]

@app.post("/api/cart/{session_id}/bundle", response_model=CartResponse)
def add_bundle_to_cart(session_id: str, bundle: BundleCartCreate):
    """Add a pre-selected bundle to cart at once and clear the pending bundle state."""
    from rag import _pending_bundle
    errors = []
    for item in bundle.items:
        try:
            crud.add_to_cart(session_id, item.product_id, 1, item.selected_options)
        except ValueError as e:
            errors.append(str(e))
    # Clear pending bundle so chat confirm flow doesn't double-add
    _pending_bundle.pop(session_id, None)
    cart = crud.get_cart(session_id)
    if errors:
        logger.warning(f"Bundle add partial errors for {session_id}: {errors}")
    return cart


@app.delete("/api/chat/{session_id}/pending")
def clear_pending(session_id: str):
    """Clear any pending option-collection state for this session (used when UI adds directly)."""
    from rag import _pending_add, _pending_bundle
    _pending_add.pop(session_id, None)
    _pending_bundle.pop(session_id, None)
    return {"cleared": True}


# ─── Orders ─────────────────────────────────────────────────

@app.post("/api/orders", response_model=Order)
def create_order(order: OrderCreate):
    try:
        return crud.create_order(
            order.session_id, order.customer_name,
            order.customer_email, order.shipping_address,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: int):
    order = crud.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/api/orders", response_model=list[Order])
def list_orders(session_id: str | None = Query(None)):
    return crud.get_orders(session_id=session_id)


# ─── Chatbot ────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
def chat(message: ChatMessage):
    logger.info(f"Chat message from {message.session_id}: {message.message}")
    try:
        result = generate_chat_response(message.message, message.session_id)
        return result
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat message")


@app.post("/api/chat/stream")
async def chat_stream(message: ChatMessage):
    """SSE streaming endpoint — yields tokens as they are generated by the LLM."""
    logger.info(f"Stream chat from {message.session_id}: {message.message}")

    async def event_generator():
        try:
            async for event in stream_chat_response(message.message, message.session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Health ──────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "e-commerce-api"}
