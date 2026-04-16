"""
MCP Server for E-Commerce Platform.
Exposes product query and order management tools for external clients.
Run with: python mcp_server.py
"""
import json
import sys
import os
import logging
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from database import init_db, seed_products
import crud

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp-server")


def send_response(response: dict):
    """Send a JSON-RPC response to stdout."""
    msg = json.dumps(response)
    header = f"Content-Length: {len(msg)}\r\n\r\n"
    sys.stdout.write(header + msg)
    sys.stdout.flush()


def read_request() -> dict | None:
    """Read a JSON-RPC request from stdin."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line or line == "\r\n" or line == "\n":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        return None

    body = sys.stdin.read(content_length)
    return json.loads(body)


TOOLS = [
    {
        "name": "search_products",
        "description": "Search for products by keyword or category. Returns matching products with details.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword to find products"},
                "category": {"type": "string", "description": "Filter by product category"},
            },
        },
    },
    {
        "name": "get_product",
        "description": "Get detailed information about a specific product by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "The product ID"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "add_to_cart",
        "description": "Add a product to the shopping cart.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "User session identifier"},
                "product_id": {"type": "integer", "description": "The product ID to add"},
                "quantity": {"type": "integer", "description": "Quantity to add", "default": 1},
            },
            "required": ["session_id", "product_id"],
        },
    },
    {
        "name": "get_cart",
        "description": "Get the current contents of a shopping cart.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "User session identifier"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "create_order",
        "description": "Create an order from the current cart contents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "User session identifier"},
                "customer_name": {"type": "string", "description": "Customer full name"},
                "customer_email": {"type": "string", "description": "Customer email address"},
                "shipping_address": {"type": "string", "description": "Shipping address"},
            },
            "required": ["session_id", "customer_name", "customer_email", "shipping_address"],
        },
    },
    {
        "name": "get_order",
        "description": "Get details of a specific order by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "The order ID"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "list_orders",
        "description": "List all orders, optionally filtered by session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Filter by user session (optional)"},
            },
        },
    },
]


def handle_tool_call(name: str, arguments: dict) -> Any:
    """Execute a tool and return the result."""
    try:
        if name == "search_products":
            results = crud.get_all_products(
                category=arguments.get("category"),
                search=arguments.get("query"),
            )
            return {"products": results, "count": len(results)}

        elif name == "get_product":
            product = crud.get_product(arguments["product_id"])
            if not product:
                return {"error": "Product not found"}
            return product

        elif name == "add_to_cart":
            cart = crud.add_to_cart(
                arguments["session_id"],
                arguments["product_id"],
                arguments.get("quantity", 1),
            )
            return cart

        elif name == "get_cart":
            return crud.get_cart(arguments["session_id"])

        elif name == "create_order":
            order = crud.create_order(
                arguments["session_id"],
                arguments["customer_name"],
                arguments["customer_email"],
                arguments["shipping_address"],
            )
            return order

        elif name == "get_order":
            order = crud.get_order(arguments["order_id"])
            if not order:
                return {"error": "Order not found"}
            return order

        elif name == "list_orders":
            return {"orders": crud.get_orders(session_id=arguments.get("session_id"))}

        else:
            return {"error": f"Unknown tool: {name}"}

    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"error": f"Internal error: {str(e)}"}


def handle_request(request: dict) -> dict:
    """Handle a JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "ecommerce-mcp-server",
                    "version": "1.0.0",
                },
            },
        }

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        logger.info(f"Tool call: {tool_name} with args: {arguments}")

        result = handle_tool_call(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                ],
            },
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def main():
    """Run the MCP server using stdio transport."""
    init_db()
    seed_products()
    logger.info("MCP Server started - listening on stdio")

    while True:
        try:
            request = read_request()
            if request is None:
                break

            response = handle_request(request)
            if response is not None:
                send_response(response)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
