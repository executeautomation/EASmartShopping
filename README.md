# ShopSmart - Full-Stack E-Commerce Platform

A full-stack e-commerce application featuring a Next.js frontend, Python FastAPI backend, RAG-powered chatbot, and an MCP server for programmatic access.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI Backend │────▶│   SQLite DB  │
│   Frontend   │     │   (REST API)     │     └──────────────┘
│  :3000       │     │   :8000          │
└──────────────┘     │                  │     ┌──────────────┐
                     │  /api/chat ──────│────▶│ LangChain RAG│
                     │                  │     │  + ChromaDB  │
                     └──────────────────┘     └──────────────┘

┌──────────────┐
│  MCP Server  │──── stdio transport ──── External Clients
│  (Python)    │
└──────────────┘
```

## Components

1. **Next.js Frontend** - Product catalog, shopping cart, checkout, order history
2. **FastAPI Backend** - REST API for products, cart, orders, and chat
3. **RAG System** - LangChain + ChromaDB vector store for product Q&A
4. **Chatbot** - AI shopping assistant that can answer questions and add items to cart
5. **MCP Server** - Model Context Protocol server for programmatic access

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

## Setup & Running

### 1. Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

The backend will:
- Create the SQLite database automatically
- Seed 12 sample products
- Build the ChromaDB vector store for RAG

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:3000 to view the application.

### 3. MCP Server

```bash
# From the project root
python mcp_server.py
```

The MCP server uses stdio transport. Configure it in your MCP client:

```json
{
  "mcpServers": {
    "ecommerce": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/ecommercewebsite"
    }
  }
}
```

## API Endpoints

### Products

```bash
# List all products
curl http://localhost:8000/api/products

# Search products
curl "http://localhost:8000/api/products?search=headphones"

# Filter by category
curl "http://localhost:8000/api/products?category=Electronics"

# Get single product
curl http://localhost:8000/api/products/1
```

### Cart

```bash
# Get cart
curl http://localhost:8000/api/cart/my-session

# Add to cart
curl -X POST http://localhost:8000/api/cart/my-session/add \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'

# Update quantity
curl -X PUT http://localhost:8000/api/cart/my-session/update \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 3}'

# Remove from cart
curl -X DELETE http://localhost:8000/api/cart/my-session/remove/1

# Clear cart
curl -X DELETE http://localhost:8000/api/cart/my-session/clear
```

### Orders

```bash
# Create order (from cart contents)
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "shipping_address": "123 Main St, City, ST 12345"
  }'

# Get order by ID
curl http://localhost:8000/api/orders/1

# List orders for a session
curl "http://localhost:8000/api/orders?session_id=my-session"
```

### Chatbot

```bash
# Ask about products
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What headphones do you have?", "session_id": "my-session"}'

# Add to cart via chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Add the wireless headphones to my cart", "session_id": "my-session"}'
```

### Health Check

```bash
curl http://localhost:8000/api/health
```

## MCP Server Tools

| Tool | Description |
|------|-------------|
| `search_products` | Search products by keyword or category |
| `get_product` | Get product details by ID |
| `add_to_cart` | Add a product to the shopping cart |
| `get_cart` | View cart contents |
| `create_order` | Place an order from cart |
| `get_order` | Get order details |
| `list_orders` | List all orders |

## Project Structure

```
ecommercewebsite/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── database.py           # SQLite database setup & seed data
│   ├── crud.py               # Database operations
│   ├── schemas.py            # Pydantic models
│   ├── rag.py                # LangChain RAG system
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx    # Root layout with navbar & chat
│   │   │   ├── page.tsx      # Product catalog
│   │   │   ├── cart/page.tsx  # Shopping cart
│   │   │   ├── checkout/page.tsx  # Checkout form
│   │   │   └── orders/page.tsx    # Order history
│   │   ├── components/
│   │   │   ├── Navbar.tsx    # Navigation bar
│   │   │   └── ChatWidget.tsx # AI chatbot widget
│   │   └── lib/
│   │       └── api.ts        # API client functions
│   ├── next.config.js        # Proxies /api to backend
│   └── package.json
├── mcp_server.py             # MCP server (stdio transport)
└── README.md
```

## Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Backend**: Python, FastAPI, SQLite, Pydantic
- **RAG**: LangChain, ChromaDB (vector store), FakeEmbeddings (demo)
- **MCP**: JSON-RPC 2.0 over stdio

## Notes

- The RAG system uses `FakeEmbeddings` for demo purposes (no API key required). For production, replace with `OpenAIEmbeddings` or another provider in `rag.py`.
- The frontend proxies API requests to the backend via Next.js rewrites (`next.config.js`).
- Session IDs are generated client-side and stored in localStorage.
- The SQLite database file (`ecommerce.db`) is created in the backend directory.
