const API_BASE = "/api";

export interface ProductOption {
  name: string;
  values: string[];
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  image_url: string;  // emoji in new products
  stock: number;
  options: ProductOption[];
  created_at: string;
}

export interface CartItem {
  id: number;
  product_id: number;
  quantity: number;
  selected_options: Record<string, string>;
  product: Product;
}

export interface Cart {
  session_id: string;
  items: CartItem[];
  total: number;
}

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  price: number;
  selected_options: Record<string, string>;
}

export interface Order {
  id: number;
  session_id: string;
  customer_name: string;
  customer_email: string;
  shipping_address: string;
  total: number;
  status: string;
  created_at: string;
  items: OrderItem[];
}

export interface ChatResponse {
  response: string;
  cart_updated: boolean;
  products_mentioned: { id: number; name: string; price: number }[];
}

export interface BundleItem {
  product_id: number;
  name: string;
  price: number;
  image: string;
  category: string;
  options: { name: string; values: string[] }[];
}

export function getSessionId(): string {
  if (typeof window === "undefined") return "server";
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = "sess_" + Math.random().toString(36).substring(2, 15);
    localStorage.setItem("session_id", id);
  }
  return id;
}

export async function fetchProducts(category?: string, search?: string): Promise<Product[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (search) params.set("search", search);
  const res = await fetch(`${API_BASE}/products?${params}`);
  if (!res.ok) throw new Error("Failed to fetch products");
  return res.json();
}

export async function fetchProduct(id: number): Promise<Product> {
  const res = await fetch(`${API_BASE}/products/${id}`);
  if (!res.ok) throw new Error("Product not found");
  return res.json();
}

export async function fetchCart(): Promise<Cart> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/cart/${sid}`);
  if (!res.ok) throw new Error("Failed to fetch cart");
  return res.json();
}

export async function addToCart(
  productId: number,
  quantity: number = 1,
  selectedOptions: Record<string, string> = {}
): Promise<Cart> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/cart/${sid}/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, quantity, selected_options: selectedOptions }),
  });
  if (!res.ok) throw new Error("Failed to add to cart");
  return res.json();
}

export async function updateCartItem(productId: number, quantity: number): Promise<Cart> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/cart/${sid}/update`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, quantity }),
  });
  if (!res.ok) throw new Error("Failed to update cart");
  return res.json();
}

export async function removeFromCart(productId: number): Promise<Cart> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/cart/${sid}/remove/${productId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to remove from cart");
  return res.json();
}

export async function createOrder(
  customerName: string,
  customerEmail: string,
  shippingAddress: string
): Promise<Order> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sid,
      customer_name: customerName,
      customer_email: customerEmail,
      shipping_address: shippingAddress,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create order");
  }
  return res.json();
}

export async function fetchOrders(): Promise<Order[]> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/orders?session_id=${sid}`);
  if (!res.ok) throw new Error("Failed to fetch orders");
  return res.json();
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sid }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function fetchSimilarProducts(productId: number): Promise<Product[]> {
  const res = await fetch(`${API_BASE}/products/${productId}/similar?limit=4`);
  if (!res.ok) return [];
  return res.json();
}

export async function addBundleToCart(
  items: { product_id: number; selected_options: Record<string, string> }[]
): Promise<Cart> {
  const sid = getSessionId();
  const res = await fetch(`${API_BASE}/cart/${sid}/bundle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error("Failed to add bundle to cart");
  return res.json();
}

export async function clearPendingOptions(): Promise<void> {
  const sid = getSessionId();
  await fetch(`${API_BASE}/chat/${sid}/pending`, { method: "DELETE" });
}
