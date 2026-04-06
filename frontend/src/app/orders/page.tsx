"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchOrders, type Order } from "@/lib/api";
import { Suspense } from "react";

function OrdersContent() {
  const searchParams = useSearchParams();
  const successId = searchParams.get("success");
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrders().then(setOrders).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: "3rem" }}>Loading orders...</div>;

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "2rem", fontWeight: "bold", marginBottom: "1.5rem" }}>📋 My Orders</h1>

      {successId && (
        <div style={{
          padding: "1rem", background: "#f0fdf4", color: "#16a34a",
          borderRadius: "0.5rem", marginBottom: "1.5rem", border: "1px solid #bbf7d0",
        }}>
          ✅ Order #{successId} placed successfully! Thank you for your purchase.
        </div>
      )}

      {orders.length === 0 ? (
        <div style={{ textAlign: "center", padding: "3rem", background: "#f9fafb", borderRadius: "0.75rem" }}>
          <p>No orders yet. Start shopping!</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {orders.map((order) => (
            <div key={order.id} style={{
              border: "1px solid #e5e7eb", borderRadius: "0.75rem",
              padding: "1.25rem", background: "white",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
                <div>
                  <span style={{ fontWeight: "bold" }}>Order #{order.id}</span>
                  <span style={{
                    marginLeft: "0.75rem", padding: "0.2rem 0.6rem",
                    background: order.status === "pending" ? "#fef3c7" : "#d1fae5",
                    color: order.status === "pending" ? "#92400e" : "#065f46",
                    borderRadius: "1rem", fontSize: "0.8rem",
                  }}>{order.status}</span>
                </div>
                <span style={{ color: "#6b7280", fontSize: "0.85rem" }}>
                  {new Date(order.created_at).toLocaleDateString()}
                </span>
              </div>
              <div style={{ marginBottom: "0.5rem" }}>
                {order.items.map((item, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.25rem 0", fontSize: "0.9rem" }}>
                    <span>{item.product_name} × {item.quantity}</span>
                    <span>${(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid #e5e7eb", paddingTop: "0.5rem", fontWeight: "bold" }}>
                <span>Total</span>
                <span style={{ color: "#2563eb" }}>${order.total.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function OrdersPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "3rem" }}>Loading...</div>}>
      <OrdersContent />
    </Suspense>
  );
}
