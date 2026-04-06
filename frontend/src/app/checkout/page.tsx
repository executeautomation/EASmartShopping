"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchCart, createOrder, type Cart } from "@/lib/api";

export default function CheckoutPage() {
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", email: "", address: "" });

  useEffect(() => {
    fetchCart().then(setCart).catch(() => setError("Failed to load cart")).finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.address) {
      setError("Please fill in all fields");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const order = await createOrder(form.name, form.email, form.address);
      router.push(`/orders?success=${order.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create order");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div style={{ textAlign: "center", padding: "3rem" }}>Loading...</div>;
  if (!cart?.items.length) return (
    <div style={{ textAlign: "center", padding: "3rem" }}>
      <p>Your cart is empty. Add some items before checking out.</p>
    </div>
  );

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "2rem", fontWeight: "bold", marginBottom: "1.5rem" }}>📦 Checkout</h1>

      {error && (
        <div style={{ padding: "0.75rem", background: "#fef2f2", color: "#dc2626", borderRadius: "0.5rem", marginBottom: "1rem", border: "1px solid #fecaca" }}>
          {error}
        </div>
      )}

      {/* Order Summary */}
      <div style={{ background: "#f9fafb", padding: "1rem", borderRadius: "0.75rem", marginBottom: "1.5rem", border: "1px solid #e5e7eb" }}>
        <h2 style={{ fontWeight: "600", marginBottom: "0.75rem" }}>Order Summary</h2>
        {cart.items.map((item) => (
          <div key={item.id} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem 0", borderBottom: "1px solid #e5e7eb" }}>
            <span>{item.product.name} × {item.quantity}</span>
            <span style={{ fontWeight: "500" }}>${(item.product.price * item.quantity).toFixed(2)}</span>
          </div>
        ))}
        <div style={{ display: "flex", justifyContent: "space-between", padding: "0.75rem 0 0", fontWeight: "bold", fontSize: "1.1rem" }}>
          <span>Total</span>
          <span style={{ color: "#2563eb" }}>${cart.total.toFixed(2)}</span>
        </div>
      </div>

      {/* Checkout Form */}
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: "500" }}>Full Name</label>
          <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="John Doe"
            style={{ width: "100%", padding: "0.6rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.5rem", outline: "none", boxSizing: "border-box" }} />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: "500" }}>Email</label>
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="john@example.com"
            style={{ width: "100%", padding: "0.6rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.5rem", outline: "none", boxSizing: "border-box" }} />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: "500" }}>Shipping Address</label>
          <textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })}
            placeholder="123 Main St, City, State, ZIP"
            rows={3}
            style={{ width: "100%", padding: "0.6rem 1rem", border: "1px solid #d1d5db", borderRadius: "0.5rem", outline: "none", resize: "vertical", boxSizing: "border-box" }} />
        </div>
        <button type="submit" disabled={submitting}
          style={{
            padding: "0.75rem", background: submitting ? "#93c5fd" : "#2563eb",
            color: "white", border: "none", borderRadius: "0.5rem",
            cursor: submitting ? "not-allowed" : "pointer", fontWeight: "600", fontSize: "1rem",
          }}>
          {submitting ? "Placing Order..." : `Place Order - $${cart.total.toFixed(2)}`}
        </button>
      </form>
    </div>
  );
}
