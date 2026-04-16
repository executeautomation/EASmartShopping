import json
import logging
from database import get_connection

logger = logging.getLogger(__name__)


def get_all_products(category: str = None, search: str = None) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    products = []
    for row in rows:
        p = dict(row)
        p["options"] = json.loads(p.get("options") or "[]")
        products.append(p)
    return products


def get_product(product_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    p = dict(row)
    p["options"] = json.loads(p.get("options") or "[]")
    return p


def get_cart(session_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ci.id, ci.product_id, ci.quantity, ci.selected_options,
               p.name, p.description, p.price, p.category, p.image_url, p.stock, p.options, p.created_at
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.session_id = ?
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()

    items = []
    total = 0.0
    for row in rows:
        row = dict(row)
        item = {
            "id": row["id"],
            "product_id": row["product_id"],
            "quantity": row["quantity"],
            "selected_options": json.loads(row.get("selected_options") or "{}"),
            "product": {
                "id": row["product_id"],
                "name": row["name"],
                "description": row["description"],
                "price": row["price"],
                "category": row["category"],
                "image_url": row["image_url"],
                "stock": row["stock"],
                "options": json.loads(row.get("options") or "[]"),
                "created_at": row["created_at"],
            },
        }
        items.append(item)
        total += row["price"] * row["quantity"]

    return {"session_id": session_id, "items": items, "total": round(total, 2)}


def add_to_cart(session_id: str, product_id: int, quantity: int = 1, selected_options: dict = None) -> dict:
    if selected_options is None:
        selected_options = {}
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    if not product:
        conn.close()
        raise ValueError(f"Product {product_id} not found")

    if dict(product)["stock"] < quantity:
        conn.close()
        raise ValueError(f"Insufficient stock for product {product_id}")

    selected_options_json = json.dumps(selected_options, sort_keys=True)

    cursor.execute("""
        INSERT INTO cart_items (session_id, product_id, quantity, selected_options)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id, product_id, selected_options) DO UPDATE SET quantity = quantity + ?
    """, (session_id, product_id, quantity, selected_options_json, quantity))

    conn.commit()
    conn.close()
    return get_cart(session_id)


def update_cart_item(session_id: str, product_id: int, quantity: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    if quantity <= 0:
        cursor.execute(
            "DELETE FROM cart_items WHERE session_id = ? AND product_id = ?",
            (session_id, product_id),
        )
    else:
        cursor.execute(
            "UPDATE cart_items SET quantity = ? WHERE session_id = ? AND product_id = ?",
            (quantity, session_id, product_id),
        )

    conn.commit()
    conn.close()
    return get_cart(session_id)


def remove_from_cart(session_id: str, product_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM cart_items WHERE session_id = ? AND product_id = ?",
        (session_id, product_id),
    )
    conn.commit()
    conn.close()
    return get_cart(session_id)


def clear_cart(session_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart_items WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    return get_cart(session_id)


def create_order(session_id: str, customer_name: str, customer_email: str, shipping_address: str) -> dict:
    cart = get_cart(session_id)
    if not cart["items"]:
        raise ValueError("Cart is empty")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO orders (session_id, customer_name, customer_email, shipping_address, total)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, customer_name, customer_email, shipping_address, cart["total"]))

    order_id = cursor.lastrowid

    for item in cart["items"]:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, product_name, quantity, price, selected_options)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, item["product_id"], item["product"]["name"], item["quantity"], item["product"]["price"],
              json.dumps(item.get("selected_options", {}))))

        cursor.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (item["quantity"], item["product_id"]),
        )

    cursor.execute("DELETE FROM cart_items WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

    return get_order(order_id)


def get_order(order_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order_row = cursor.fetchone()
    if not order_row:
        conn.close()
        return None

    order = dict(order_row)

    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    raw_items = [dict(row) for row in cursor.fetchall()]
    for oi in raw_items:
        oi["selected_options"] = json.loads(oi.get("selected_options") or "{}")
    order["items"] = raw_items

    conn.close()
    return order


def get_orders(session_id: str = None) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    if session_id:
        cursor.execute("SELECT * FROM orders WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
    else:
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")

    orders = []
    for row in cursor.fetchall():
        order = dict(row)
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))
        raw_items = [dict(r) for r in cursor.fetchall()]
        for oi in raw_items:
            oi["selected_options"] = json.loads(oi.get("selected_options") or "{}")
        order["items"] = raw_items
        orders.append(order)

    conn.close()
    return orders
