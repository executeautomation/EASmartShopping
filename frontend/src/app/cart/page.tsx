"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCart, updateCartItem, removeFromCart, type Cart } from "@/lib/api";

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadCart(); }, []);

  const loadCart = async () => {
    try { setCart(await fetchCart()); }
    catch { console.error("Failed to load cart"); }
    finally { setLoading(false); }
  };

  const handleUpdateQuantity = async (productId: number, quantity: number) => {
    try { setCart(await updateCartItem(productId, quantity)); }
    catch { console.error("Failed to update quantity"); }
  };

  const handleRemove = async (productId: number) => {
    try { setCart(await removeFromCart(productId)); }
    catch { console.error("Failed to remove item"); }
  };

  if (loading) return (
    <div style={{ textAlign: "center", padding: "4rem", color: "var(--text-2)" }}>
      <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🛒</div>Loading your cart…
    </div>
  );

  return (
    <div style={{ maxWidth: "860px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 800, marginBottom: "0.25rem", letterSpacing: "-0.02em" }}>
        Shopping Cart
      </h1>
      {cart?.items.length ? (
        <p style={{ color: "var(--text-2)", marginBottom: "1.75rem", fontSize: "0.9rem" }}>
          {cart.items.reduce((s, i) => s + i.quantity, 0)} item{cart.items.length !== 1 ? "s" : ""}
        </p>
      ) : null}

      {!cart?.items.length ? (
        <div style={{
          textAlign: "center", padding: "4rem", background: "var(--surface)",
          borderRadius: "16px", border: "1.5px solid var(--border)",
        }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🛒</div>
          <p style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-2)", marginBottom: "1.25rem" }}>
            Your cart is empty
          </p>
          <Link href="/" style={{
            padding: "0.65rem 1.5rem", background: "var(--primary)", color: "white",
            borderRadius: "10px", fontWeight: 600, fontSize: "0.9rem",
            display: "inline-block",
          }}>Browse Products</Link>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: "1.5rem", alignItems: "start" }}>
          {/* Items */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {cart.items.map((item) => (
              <div key={item.id} style={{
                display: "flex", gap: "1rem", padding: "1.25rem",
                background: "var(--surface)", border: "1.5px solid var(--border)",
                borderRadius: "14px", boxShadow: "var(--shadow-sm)",
                alignItems: "flex-start",
              }}>
                {/* Product image */}
                <div style={{
                  width: "80px", height: "80px", borderRadius: "10px", flexShrink: 0,
                  background: "linear-gradient(135deg, #eef2ff, #e0e7ff)",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: "2rem",
                  overflow: "hidden",
                }}>
                  {item.product.image_url?.startsWith("http") ? (
                    <img
                      src={item.product.image_url}
                      alt={item.product.name}
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                        (e.currentTarget as HTMLImageElement).parentElement!.textContent = "📦";
                      }}
                    />
                  ) : (
                    item.product.image_url || "📦"
                  )}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3 style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: "0.25rem" }}>
                    {item.product.name}
                  </h3>
                  {/* Selected options badges */}
                  {item.selected_options && Object.keys(item.selected_options).length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginBottom: "0.5rem" }}>
                      {Object.entries(item.selected_options).map(([k, v]) => (
                        <span key={k} style={{
                          background: "var(--primary-light)", color: "var(--primary)",
                          border: "1px solid rgba(79,70,229,0.2)",
                          borderRadius: "99px", padding: "2px 8px", fontSize: "0.7rem", fontWeight: 600,
                        }}>{k}: {v}</span>
                      ))}
                    </div>
                  )}
                  <p style={{ color: "var(--primary)", fontWeight: 700, fontSize: "1rem" }}>
                    ${item.product.price.toFixed(2)}
                  </p>
                </div>

                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <button onClick={() => handleUpdateQuantity(item.product_id, item.quantity - 1)}
                      style={{
                        width: "30px", height: "30px", borderRadius: "8px",
                        background: "var(--surface-2)", border: "1.5px solid var(--border)",
                        fontWeight: 700, fontSize: "1rem", color: "var(--text-2)",
                      }}>−</button>
                    <span style={{ minWidth: "1.8rem", textAlign: "center", fontWeight: 700, fontSize: "0.9rem" }}>
                      {item.quantity}
                    </span>
                    <button onClick={() => handleUpdateQuantity(item.product_id, item.quantity + 1)}
                      style={{
                        width: "30px", height: "30px", borderRadius: "8px",
                        background: "var(--surface-2)", border: "1.5px solid var(--border)",
                        fontWeight: 700, fontSize: "1rem", color: "var(--text-2)",
                      }}>+</button>
                  </div>
                  <span style={{ fontWeight: 800, color: "var(--text)", fontSize: "0.95rem" }}>
                    ${(item.product.price * item.quantity).toFixed(2)}
                  </span>
                  <button onClick={() => handleRemove(item.product_id)}
                    style={{
                      background: "none", border: "none", color: "var(--text-3)",
                      fontSize: "0.8rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.2rem",
                    }}>
                    🗑 Remove
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Order summary */}
          <div style={{
            background: "var(--surface)", border: "1.5px solid var(--border)",
            borderRadius: "16px", padding: "1.5rem", boxShadow: "var(--shadow-sm)",
            position: "sticky", top: "80px",
          }}>
            <h2 style={{ fontWeight: 700, marginBottom: "1.25rem" }}>Order Summary</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginBottom: "1.25rem" }}>
              {cart.items.map((item) => (
                <div key={item.id} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                  <span style={{ color: "var(--text-2)" }}>{item.product.name} × {item.quantity}</span>
                  <span style={{ fontWeight: 600 }}>${(item.product.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>
            <div style={{ borderTop: "1.5px solid var(--border)", paddingTop: "1rem", marginBottom: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, fontSize: "1.1rem" }}>
                <span>Total</span>
                <span style={{ color: "var(--primary)" }}>${cart.total.toFixed(2)}</span>
              </div>
            </div>
            <Link href="/checkout" style={{
              display: "block", textAlign: "center", padding: "0.8rem",
              background: "var(--primary)", color: "white",
              borderRadius: "10px", fontWeight: 700, fontSize: "0.95rem",
            }}>
              Proceed to Checkout →
            </Link>
            <Link href="/" style={{
              display: "block", textAlign: "center", padding: "0.6rem",
              color: "var(--text-2)", fontSize: "0.85rem", marginTop: "0.75rem",
            }}>
              ← Continue Shopping
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
