"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchProduct, fetchSimilarProducts, addToCart, type Product } from "@/lib/api";

const CATEGORY_ICONS: Record<string, string> = {
  Clothing: "👕", Sports: "🏃", Bags: "🎒",
  Electronics: "⚡", "Home & Kitchen": "🏡", Wellness: "🌿",
  "Computer Components": "🖥️",
};

const COLOR_MAP: Record<string, string> = {
  Black: "#111827", "Midnight Black": "#111827", "Charcoal Black": "#1f2937",
  White: "#f9fafb", "Pearl White": "#f1f5f9", "Matte White": "#f8fafc", "Arctic White": "#ffffff",
  Navy: "#1e3a5f", "Navy Blue": "#1e3a5f", "Midnight Navy": "#1e3a5f",
  Gray: "#6b7280", "Slate Gray": "#64748b", "Space Gray": "#374151",
  Burgundy: "#7f1d1d", "Rose Gold": "#c2856b", "Rose Blush": "#fbb6ce",
  Blue: "#2563eb", "Ocean Blue": "#0284c7", "Pacific Blue": "#0369a1", "Slate Blue": "#475569",
  Green: "#16a34a", "Forest Green": "#15803d", "Sage Green": "#84cc16",
  Coral: "#f97316", Red: "#ef4444", "Product Red": "#dc2626",
  Teal: "#0d9488", Purple: "#9333ea", "Deep Plum": "#6b21a8",
  Sand: "#d4b896", Tan: "#c9a47b", "Cognac Brown": "#92400e", Brown: "#78350f",
  Terracotta: "#c2440e", Olive: "#65a30d", "Olive Drab": "#4d7c0f",
  Rust: "#c2410c", Natural: "#d4b896", "Natural Canvas": "#d4b896",
};

function isImageUrl(s: string) { return s.startsWith("http"); }
function isColorOption(name: string) {
  return name.toLowerCase().includes("color") || name.toLowerCase() === "wash" || name.toLowerCase() === "band color";
}
function toColor(val: string): string | null {
  for (const [k, v] of Object.entries(COLOR_MAP)) {
    if (val.toLowerCase().includes(k.toLowerCase())) return v;
  }
  return null;
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div style={{ display: "flex", gap: "2px" }}>
      {[1, 2, 3, 4, 5].map((star) => {
        const fill = Math.min(1, Math.max(0, rating - (star - 1)));
        return (
          <span key={star} style={{ position: "relative", fontSize: "1.1rem", lineHeight: 1 }}>
            <span style={{ color: "#d1d5db" }}>★</span>
            <span style={{
              position: "absolute", left: 0, top: 0,
              width: `${fill * 100}%`, overflow: "hidden",
              color: "#f59e0b",
            }}>★</span>
          </span>
        );
      })}
    </div>
  );
}

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [product, setProduct] = useState<Product | null>(null);
  const [similar, setSimilar] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [activeTab, setActiveTab] = useState<"description" | "specs">("description");

  useEffect(() => {
    setLoading(true);
    fetchProduct(id)
      .then((p) => {
        setProduct(p);
        setLoading(false);
        fetchSimilarProducts(p.id).then(setSimilar).catch(() => {});
      })
      .catch(() => { setNotFound(true); setLoading(false); });
  }, [id]);

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const setOption = (optName: string, value: string) => {
    setSelections((prev) => ({ ...prev, [optName]: value }));
  };

  const allOptionsSelected = () => {
    if (!product?.options.length) return true;
    return product.options.every((opt) => !!selections[opt.name]);
  };

  const handleAddToCart = async () => {
    if (!product) return;
    if (!allOptionsSelected()) { showToast("Please select all options first", false); return; }
    setAdding(true);
    try {
      await addToCart(product.id, quantity, selections);
      showToast(`Added "${product.name}" to cart!`, true);
    } catch { showToast("Failed to add to cart", false); }
    finally { setAdding(false); }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <div style={{ textAlign: "center", color: "var(--text-3)" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⏳</div>
          <p style={{ fontSize: "1rem", fontWeight: 500 }}>Loading product…</p>
        </div>
      </div>
    );
  }

  if (notFound || !product) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 2rem", color: "var(--text-3)" }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>😕</div>
        <p style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-2)" }}>Product not found</p>
        <Link href="/" style={{
          display: "inline-block", marginTop: "1.5rem",
          padding: "0.6rem 1.5rem", background: "var(--primary)", color: "white",
          borderRadius: "8px", fontWeight: 600, fontSize: "0.9rem",
        }}>← Back to Shop</Link>
      </div>
    );
  }

  const specEntries = Object.entries(product.specs || {});

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", top: "5rem", right: "1.5rem", zIndex: 999,
          background: toast.ok ? "#10b981" : "#ef4444",
          color: "white", padding: "0.75rem 1.25rem",
          borderRadius: "12px", boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
          fontWeight: 500, fontSize: "0.9rem",
        }}>
          {toast.ok ? "✅" : "⚠️"} {toast.msg}
        </div>
      )}

      {/* Breadcrumb */}
      <nav style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "1.5rem", fontSize: "0.82rem", color: "var(--text-3)" }}>
        <Link href="/" style={{ color: "var(--primary)", fontWeight: 500 }}>Shop</Link>
        <span>›</span>
        <Link href={`/?category=${encodeURIComponent(product.category)}`} style={{ color: "var(--primary)", fontWeight: 500 }}>
          {product.category}
        </Link>
        <span>›</span>
        <span style={{ color: "var(--text-2)", fontWeight: 500 }}>{product.name}</span>
      </nav>

      {/* Main layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3rem", alignItems: "start" }}>

        {/* ── Left: Image ── */}
        <div style={{
          background: "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)",
          borderRadius: "20px",
          minHeight: "420px",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "8rem",
          position: "sticky", top: "5.5rem",
          border: "1.5px solid var(--border)",
          overflow: "hidden",
        }}>
          {isImageUrl(product.image_url) ? (
            <img
              src={product.image_url}
              alt={product.name}
              style={{ width: "100%", height: "420px", objectFit: "cover", display: "block" }}
            />
          ) : (
            product.image_url || CATEGORY_ICONS[product.category] || "📦"
          )}
        </div>

        {/* ── Right: Details ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

          {/* Category badge */}
          <div>
            <span style={{
              display: "inline-flex", alignItems: "center", gap: "0.3rem",
              background: "var(--primary-light)", color: "var(--primary)",
              padding: "4px 12px", borderRadius: "99px",
              fontSize: "0.75rem", fontWeight: 700,
            }}>
              {CATEGORY_ICONS[product.category] || "📦"} {product.category}
            </span>
          </div>

          {/* Name */}
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, lineHeight: "1.3", color: "var(--text)" }}>
            {product.name}
          </h1>

          {/* Rating */}
          {product.rating > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <StarRating rating={product.rating} />
              <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#92400e" }}>
                {product.rating.toFixed(1)}
              </span>
              <span style={{ color: "var(--text-3)", fontSize: "0.85rem" }}>
                ({product.review_count.toLocaleString()} reviews)
              </span>
            </div>
          )}

          {/* Manufacturer */}
          {product.manufacturer && (
            <p style={{ fontSize: "0.85rem", color: "var(--text-3)" }}>
              Manufactured by <span style={{ fontWeight: 600, color: "var(--text-2)" }}>{product.manufacturer}</span>
            </p>
          )}

          {/* Price */}
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
            <span style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--primary)" }}>
              ${product.price.toFixed(2)}
            </span>
            <span style={{
              fontSize: "0.8rem", fontWeight: 600,
              color: product.stock === 0 ? "var(--danger)" : product.stock <= 5 ? "#d97706" : "var(--success)",
              background: product.stock === 0 ? "var(--danger-light)" : product.stock <= 5 ? "#fef3c7" : "var(--success-light)",
              padding: "3px 10px", borderRadius: "99px",
            }}>
              {product.stock === 0 ? "Out of Stock" : product.stock <= 5 ? `Only ${product.stock} left!` : `${product.stock} in stock`}
            </span>
          </div>

          <hr style={{ border: "none", borderTop: "1.5px solid var(--border)" }} />

          {/* Options */}
          {product.options.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {product.options.map((opt) => {
                const sel = selections[opt.name];
                return (
                  <div key={opt.name}>
                    <p style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-2)", marginBottom: "0.5rem" }}>
                      {opt.name}
                      {sel && <span style={{ color: "var(--primary)", marginLeft: "0.5rem", fontWeight: 500 }}>· {sel}</span>}
                    </p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                      {opt.values.map((val) => {
                        const hex = isColorOption(opt.name) ? toColor(val) : null;
                        const selected = sel === val;
                        if (hex) {
                          return (
                            <button key={val} title={val} onClick={() => setOption(opt.name, val)} style={{
                              width: "32px", height: "32px", borderRadius: "50%",
                              background: hex, cursor: "pointer",
                              border: selected ? "3px solid var(--primary)" : "2px solid var(--border)",
                              outline: selected ? "2px solid white" : "none",
                              outlineOffset: "-4px",
                              boxShadow: selected ? "0 0 0 3px var(--primary)" : "var(--shadow-sm)",
                              transform: selected ? "scale(1.15)" : "scale(1)",
                              transition: "all 150ms",
                            }} />
                          );
                        }
                        return (
                          <button key={val} onClick={() => setOption(opt.name, val)} style={{
                            padding: "6px 14px", borderRadius: "8px", fontSize: "0.82rem", fontWeight: 500,
                            cursor: "pointer",
                            background: selected ? "var(--primary)" : "var(--surface-2)",
                            color: selected ? "white" : "var(--text-2)",
                            border: `1.5px solid ${selected ? "var(--primary)" : "var(--border)"}`,
                            transition: "all 150ms",
                          }}>{val}</button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Quantity + Add to Cart */}
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            {/* Quantity stepper */}
            <div style={{
              display: "flex", alignItems: "center",
              border: "1.5px solid var(--border)", borderRadius: "10px",
              overflow: "hidden", background: "var(--surface)",
            }}>
              <button
                onClick={() => setQuantity(q => Math.max(1, q - 1))}
                style={{
                  width: "38px", height: "44px",
                  background: "var(--surface-2)", color: "var(--text-2)",
                  fontSize: "1.1rem", fontWeight: 700,
                  borderRight: "1.5px solid var(--border)",
                }}
              >−</button>
              <span style={{ width: "42px", textAlign: "center", fontWeight: 700, fontSize: "0.95rem" }}>
                {quantity}
              </span>
              <button
                onClick={() => setQuantity(q => Math.min(product.stock, q + 1))}
                style={{
                  width: "38px", height: "44px",
                  background: "var(--surface-2)", color: "var(--text-2)",
                  fontSize: "1.1rem", fontWeight: 700,
                  borderLeft: "1.5px solid var(--border)",
                }}
              >+</button>
            </div>

            {/* Add to Cart */}
            <button
              onClick={handleAddToCart}
              disabled={adding || product.stock === 0}
              style={{
                flex: 1, padding: "0.75rem 1.5rem",
                background: product.stock === 0 ? "var(--surface-2)"
                  : !allOptionsSelected() ? "var(--surface-2)"
                  : "var(--primary)",
                color: product.stock === 0 || !allOptionsSelected() ? "var(--text-3)" : "white",
                borderRadius: "10px", fontWeight: 700, fontSize: "0.95rem",
                border: `1.5px solid ${product.stock === 0 || !allOptionsSelected() ? "var(--border)" : "var(--primary)"}`,
                cursor: product.stock === 0 ? "not-allowed" : "pointer",
                transition: "all 150ms",
              }}
            >
              {adding ? "Adding…"
                : product.stock === 0 ? "Out of Stock"
                : !allOptionsSelected() ? "Select options above"
                : `🛒 Add ${quantity > 1 ? `${quantity} ×` : ""} to Cart`}
            </button>
          </div>
        </div>
      </div>

      {/* ── Description / Specs tabs ── */}
      <div style={{ marginTop: "3rem" }}>
        <div style={{ display: "flex", borderBottom: "2px solid var(--border)", marginBottom: "1.5rem" }}>
          {(["description", "specs"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "0.65rem 1.5rem",
                fontWeight: 600, fontSize: "0.9rem",
                background: "transparent", cursor: "pointer",
                color: activeTab === tab ? "var(--primary)" : "var(--text-3)",
                borderBottom: `2px solid ${activeTab === tab ? "var(--primary)" : "transparent"}`,
                marginBottom: "-2px",
                transition: "all 150ms",
                textTransform: "capitalize",
              }}
            >
              {tab === "description" ? "📄 Description" : "🔧 Specifications"}
              {tab === "specs" && specEntries.length > 0 && (
                <span style={{
                  marginLeft: "0.4rem", fontSize: "0.7rem", fontWeight: 700,
                  background: "var(--surface-2)", color: "var(--text-3)",
                  padding: "1px 6px", borderRadius: "99px",
                }}>{specEntries.length}</span>
              )}
            </button>
          ))}
        </div>

        {activeTab === "description" && (
          <p style={{ color: "var(--text-2)", lineHeight: "1.8", fontSize: "0.95rem", maxWidth: "720px" }}>
            {product.description}
          </p>
        )}

        {activeTab === "specs" && (
          specEntries.length > 0 ? (
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "0.75rem", maxWidth: "800px",
            }}>
              {specEntries.map(([key, value]) => (
                <div key={key} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "0.6rem 1rem",
                  background: "var(--surface)", border: "1.5px solid var(--border)",
                  borderRadius: "10px",
                }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-3)", textTransform: "capitalize" }}>
                    {String(key).replace(/_/g, " ")}
                  </span>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text)", textAlign: "right", maxWidth: "55%" }}>
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--text-3)", fontSize: "0.9rem" }}>No specifications available.</p>
          )
        )}
      </div>

      {/* ── You might also like ── */}
      {similar.length > 0 && (
        <div style={{ marginTop: "3rem" }}>
          <h2 style={{ fontWeight: 700, fontSize: "1.2rem", marginBottom: "1.25rem", color: "var(--text)" }}>
            You might also like
          </h2>
          <div style={{ display: "flex", gap: "1rem", overflowX: "auto", paddingBottom: "0.5rem" }}>
            {similar.slice(0, 6).map((sim) => (
              <Link key={sim.id} href={`/products/${sim.id}`} style={{
                flexShrink: 0, width: "180px",
                background: "var(--surface)", border: "1.5px solid var(--border)",
                borderRadius: "14px", overflow: "hidden",
                boxShadow: "var(--shadow-sm)",
                transition: "transform 150ms, box-shadow 150ms",
                display: "flex", flexDirection: "column",
              }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(-3px)";
                  (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLAnchorElement).style.transform = "translateY(0)";
                  (e.currentTarget as HTMLAnchorElement).style.boxShadow = "var(--shadow-sm)";
                }}
              >
                <div style={{
                  background: "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)",
                  height: "120px",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "2.5rem",
                }}>
                  {isImageUrl(sim.image_url) ? (
                    <img src={sim.image_url} alt={sim.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  ) : sim.image_url || CATEGORY_ICONS[sim.category] || "📦"}
                </div>
                <div style={{ padding: "0.75rem", flex: 1 }}>
                  <p style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text)", lineHeight: "1.3", marginBottom: "0.3rem" }}>
                    {sim.name.substring(0, 32)}{sim.name.length > 32 ? "…" : ""}
                  </p>
                  {sim.rating > 0 && (
                    <p style={{ fontSize: "0.68rem", color: "#92400e", fontWeight: 600, marginBottom: "0.25rem" }}>
                      ★ {sim.rating.toFixed(1)} ({sim.review_count.toLocaleString()})
                    </p>
                  )}
                  <p style={{ fontSize: "0.85rem", fontWeight: 800, color: "var(--primary)" }}>
                    ${sim.price.toFixed(2)}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
