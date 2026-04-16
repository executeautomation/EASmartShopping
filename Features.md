# EA SmartKart — Feature Reference

## 🛍️ Store & Product Browsing

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Product Listing Page** | Homepage grid of all products with images, price, category badge, and description snippet. |
| 2 | **Category Sidebar Filter** | Sticky left sidebar listing every category with item counts; click to filter the grid instantly. |
| 3 | **Keyword Search** | Real-time text filter on product name and description across all categories. |
| 4 | **Semantic / AI Search** | Toggle to "AI Search" mode; uses vector embeddings (nomic-embed-text + ChromaDB) to find products by meaning, not just keywords — e.g. *"something to keep me hydrated while running"*. |
| 5 | **"You Might Also Like"** | Each product card lazily loads up to 3 semantically similar products via the `/api/products/{id}/similar` endpoint; shown as clickable chips below the description. |
| 6 | **Color Swatch Picker** | Products with a Color option render round swatches (hex-mapped) instead of plain text buttons; selected swatch is highlighted with a ring. |
| 7 | **Option Chip Selector** | Non-color options (Size, Pack Size, Case Size, etc.) render as styled chip buttons on the product card; all options must be selected before Add to Cart becomes active. |
| 8 | **Quick Add to Cart** | One-click "Add to Cart" on any product card; shows a green/red toast notification for 3 seconds on success or error. |
| 9 | **Navbar Cart Badge** | Live item-count badge on the 🛒 icon; updates immediately after any cart mutation (including chatbot adds) via a custom `cart-updated` browser event. |

---

## 🛒 Cart & Checkout

| # | Feature | Description |
|---|---------|-------------|
| 10 | **Cart Page** | View all cart items with product image, selected options, unit price, quantity stepper, remove button, and running total. |
| 11 | **Quantity Stepper** | Inline +/− controls on the cart page to update item quantities without leaving the page. |
| 12 | **Remove Item** | Per-item delete button on the cart page. |
| 13 | **Checkout Page** | Summary of cart items + totals with a "Place Order" action that creates an order record. |
| 14 | **Orders Page** | Full order history showing order ID, date, status badge (pending/completed), itemised list, and total. |

---

## 🤖 AI Shopping Assistant (ChatWidget)

> Open the chat bubble (bottom-right corner of every page) to use all features below.

| # | Feature | Prompt Example |
|---|---------|----------------|
| 15 | **Streaming Chat** | Any message — responses stream token-by-token in real time via SSE. | 
| 16 | **Product Recommendations** | *"What's a good laptop bag for travel?"* — RAG retrieves relevant products and the LLM explains them. |
| 17 | **Add Single Item to Cart** | *"Add the Sports Water Bottle to my cart"* — bot detects intent, queues the item, and shows an option-picker card if variants exist. |
| 18 | **Interactive Option Picker** | Triggered automatically when adding a product with variants — chip buttons appear in-chat for each option (size, colour, etc.) so you never have to type them. |
| 19 | **Update Cart Quantity** | *"Change the quantity of Trail Running Shoes to 3"* — bot updates the cart directly. |
| 20 | **Remove Item from Cart** | *"Remove the Laptop Backpack from my cart"* — bot removes the item and confirms. |
| 21 | **Clear Entire Cart** | *"Empty my cart"* / *"Clear everything"* — bot wipes the cart and confirms. |
| 22 | **Product Comparison** | *"Compare the Stainless Steel Water Bottle vs the Sports Water Bottle"* — LLM produces a side-by-side comparison. |
| 23 | **Interactive Comparison Table** | Whenever the LLM returns a markdown table, it is auto-rendered as a styled grid with alternating rows, highlighted recommendation row, and **Add to Cart** buttons per column. |
| 24 | **Bundle Recommender** | *"Build me a gaming PC"* / *"Bundle me a home office setup"* / *"Bundle me sports gear"* — RAG finds complementary items, the LLM summarises them, and an interactive bundle card appears. |
| 25 | **Interactive Bundle Card** | Inline card shows each bundle item with image, price, and option chips; individual items can be toggled out with the × button; a dynamic total and "Add N Items to Cart" button completes the purchase. |
| 26 | **Remove Item from Pending Bundle (chat)** | *"I don't want the Leather Tote Bag"* — while a bundle is pending, the bot removes that item from the card and updates the total. |
| 27 | **Superseded Bundle Lock** | When a new bundle is generated, all previous bundle cards in the conversation are locked with a "🔒 Bundle superseded" notice so only the latest one is actionable. |
| 28 | **Reorder Last Order** | *"Reorder my last order"* / *"Buy the same things again"* — bot fetches order history and re-adds items to the cart. |
| 29 | **Cart Awareness** | *"What's in my cart?"* / *"How much is in my cart?"* — bot reads the live cart state and answers accurately. |
| 30 | **Conversation Memory** | The assistant maintains the last 8 turns of context (configurable in `config.yaml`) so follow-up questions like *"make it cheaper"* or *"add the second one"* work correctly. |
| 31 | **Resizable Chat Window** | Drag the ↔ grip (top-left corner of the chat panel) to resize width and height freely (min 360×460, max 720×88vh). |

---

## ⚙️ Backend & Infrastructure

| # | Feature | Description |
|---|---------|-------------|
| 32 | **RAG with ChromaDB** | All product names + descriptions are embedded at startup (nomic-embed-text via Ollama) into a ChromaDB vector store; similarity search powers recommendations, bundles, and semantic search. |
| 33 | **Local LLM via Ollama + LangChain** | Chat responses are generated by a local Ollama model (default: `gemma4:e2b`) through LangChain's streaming interface — no cloud API keys required. |
| 34 | **Configurable LLM (`config.yaml`)** | `backend/config.yaml` exposes `chat_model`, `embed_model`, `temperature`, `max_tokens`, `reasoning` (chain-of-thought toggle), and `max_history_turns` — all changeable without touching code; env-var overrides are also supported. |
| 35 | **Session-based Cart & Orders** | Cart and order data is tied to a browser-generated `session_id` (stored in `localStorage`) so no login is required. |
| 36 | **SQLite Database** | Products, cart items, and orders are persisted in `backend/ecommerce.db` — zero-config, file-based storage. |
| 37 | **FastAPI REST API** | Full CRUD endpoints for products, cart, orders, and chat; semantic search and bundle endpoints included; automatic OpenAPI docs at `/docs`. |
| 38 | **`.gitignore`** | Both Python (venv, `__pycache__`, `.env`, ChromaDB data) and Node.js (`node_modules`, `.next`, build artefacts) entries are covered. |
