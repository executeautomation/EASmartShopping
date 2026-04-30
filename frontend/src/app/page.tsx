"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchProducts, addToCart, type Product } from "@/lib/api";

const CATEGORY_ICONS: Record<string, string> = {
  Clothing: "👕", Sports: "🏃", Bags: "🎒",
  Electronics: "⚡", "Home & Kitchen": "🏡", Wellness: "🌿",
  "Computer Components": "🖥️",
};

function isImageUrl(s: string) {
  return s.startsWith("http");
}

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [adding, setAdding] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [searchMode, setSearchMode] = useState<"keyword" | "semantic">("keyword");

  // Load all products once to build category counts
  useEffect(() => {
    fetchProducts().then((all) => {
      const sorted = [...new Set(all.map((p) => p.category))].sort();
      setCategories(sorted);
      const counts: Record<string, number> = {};
      all.forEach((p) => { counts[p.category] = (counts[p.category] || 0) + 1; });
      setCategoryCounts(counts);
    }).catch(() => {});
  }, []);

  useEffect(() => { loadProducts(); }, [category, searchMode]);

  const loadProducts = async () => {
    try {
      let data: Product[];
      if (searchMode === "semantic" && search.trim()) {
        const res = await fetch(`/api/products/search/semantic?q=${encodeURIComponent(search.trim())}`);
        if (!res.ok) throw new Error("Semantic search failed");
        data = await res.json();
      } else {
        data = await fetchProducts(category || undefined, search || undefined);
      }
      setProducts(data);
    } catch { showToast("Failed to load products", false); }
  };

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };



  return (
    <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start" }}>

      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="sidebar" style={{
        width: "220px", flexShrink: 0,
        position: "sticky", top: "5.5rem",
        background: "var(--surface)", border: "1.5px solid var(--border)",
        borderRadius: "14px", overflow: "hidden",
        boxShadow: "var(--shadow-sm)",
      }}>
        <div style={{
          padding: "0.75rem 1rem",
          borderBottom: "1.5px solid var(--border)",
          background: "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
        }}>
          <p style={{ fontWeight: 700, fontSize: "0.8rem", color: "white", letterSpacing: "0.06em", textTransform: "uppercase" }}>
            Browse by Category
          </p>
        </div>

        {/* All Products */}
        <button onClick={() => setCategory("")} style={{
          width: "100%", display: "flex", alignItems: "center", gap: "0.6rem",
          padding: "0.75rem 1rem", border: "none", cursor: "pointer", textAlign: "left",
          background: !category ? "rgba(79,70,229,0.1)" : "transparent",
          borderLeft: !category ? "3px solid var(--primary)" : "3px solid transparent",
          transition: "all 120ms",
        }}>
          <span style={{ fontSize: "1.1rem" }}>🏪</span>
          <span style={{
            flex: 1, fontSize: "0.85rem", fontWeight: !category ? 700 : 500,
            color: !category ? "var(--primary)" : "var(--text)",
          }}>All Products</span>
          <span style={{
            fontSize: "0.7rem", fontWeight: 600,
            background: !category ? "var(--primary)" : "var(--surface-2)",
            color: !category ? "white" : "var(--text-3)",
            padding: "1px 7px", borderRadius: "99px",
          }}>
            {Object.values(categoryCounts).reduce((a, b) => a + b, 0)}
          </span>
        </button>

        {/* Divider */}
        <div style={{ height: "1px", background: "var(--border)", margin: "0 1rem" }} />

        {/* Category buttons */}
        {categories.map((c) => (
          <button key={c} onClick={() => setCategory(c)} style={{
            width: "100%", display: "flex", alignItems: "center", gap: "0.6rem",
            padding: "0.7rem 1rem", border: "none", cursor: "pointer", textAlign: "left",
            background: category === c ? "rgba(79,70,229,0.1)" : "transparent",
            borderLeft: category === c ? "3px solid var(--primary)" : "3px solid transparent",
            transition: "all 120ms",
          }}
            onMouseEnter={(e) => {
              if (category !== c) (e.currentTarget as HTMLButtonElement).style.background = "var(--surface-2)";
            }}
            onMouseLeave={(e) => {
              if (category !== c) (e.currentTarget as HTMLButtonElement).style.background = "transparent";
            }}
          >
            <span style={{ fontSize: "1.1rem" }}>{CATEGORY_ICONS[c] || "📦"}</span>
            <span style={{
              flex: 1, fontSize: "0.82rem", fontWeight: category === c ? 700 : 400,
              color: category === c ? "var(--primary)" : "var(--text)",
              lineHeight: "1.3",
            }}>{c}</span>
            <span style={{
              fontSize: "0.7rem", fontWeight: 600,
              background: category === c ? "var(--primary)" : "var(--surface-2)",
              color: category === c ? "white" : "var(--text-3)",
              padding: "1px 7px", borderRadius: "99px",
            }}>
              {categoryCounts[c] || 0}
            </span>
          </button>
        ))}
      </aside>

      {/* ── Main content ────────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 0 }}>

        {/* Toast */}
        {toast && (
          <div style={{
            position: "fixed", top: "5rem", right: "1.5rem", zIndex: 999,
            background: toast.ok ? "#10b981" : "#ef4444",
            color: "white", padding: "0.75rem 1.25rem",
            borderRadius: "12px", boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
            fontWeight: 500, fontSize: "0.9rem",
            animation: "slideIn 200ms ease",
          }}>
            {toast.ok ? "✅" : "⚠️"} {toast.msg}
          </div>
        )}

        {/* Hero header */}
        <div style={{ marginBottom: "1.5rem" }}>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, letterSpacing: "-0.03em", color: "var(--text)" }}>
            {category ? `${CATEGORY_ICONS[category] || "📦"} ${category}` : "🏪 Shop Everything"}
          </h1>
          <p style={{ color: "var(--text-2)", marginTop: "0.25rem", fontSize: "0.875rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            {products.length} product{products.length !== 1 ? "s" : ""}
            {category ? ` in ${category}` : ` across ${categories.length} categories`}
            {searchMode === "semantic" && search && (
              <span style={{
                fontSize: "0.7rem", fontWeight: 700,
                background: "linear-gradient(135deg, #7c3aed, #4f46e5)",
                color: "white", padding: "2px 8px", borderRadius: "99px",
              }}>✨ Powered by AI</span>
            )}
          </p>
        </div>

        {/* Search bar */}
        <form onSubmit={(e) => { e.preventDefault(); loadProducts(); }} style={{
          display: "flex", gap: "0.5rem", marginBottom: "1.5rem",
        }}>
          <input
            type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search${category ? ` in ${category}` : " all products"}…`}
            style={{ flex: 1, fontSize: "0.9rem" }}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearchMode(m => m === "keyword" ? "semantic" : "keyword")}
              style={{
                padding: "0.5rem 0.9rem",
                background: searchMode === "semantic" ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "var(--surface-2)",
                color: searchMode === "semantic" ? "white" : "var(--text-2)",
                borderRadius: "20px", fontWeight: 600, fontSize: "0.78rem",
                border: `1.5px solid ${searchMode === "semantic" ? "#7c3aed" : "var(--border)"}`,
                cursor: "pointer", whiteSpace: "nowrap",
                transition: "all 150ms",
              }}
            >
              {searchMode === "keyword" ? "🔍 Keyword" : "🧠 AI Search"}
            </button>
          )}
          <button type="submit" style={{
            padding: "0.6rem 1.2rem", background: "var(--primary)", color: "white",
            borderRadius: "8px", fontWeight: 600, fontSize: "0.875rem",
            transition: "background 150ms",
          }}>Search</button>
          {search && (
            <button type="button" onClick={() => { setSearch(""); loadProducts(); }} style={{
              padding: "0.6rem 0.9rem", background: "var(--surface-2)", color: "var(--text-2)",
              borderRadius: "8px", fontWeight: 600, fontSize: "0.875rem",
              border: "1.5px solid var(--border)",
            }}>✕</button>
          )}
        </form>

        {/* Product grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: "1.25rem",
        }}>
          {products.map((product) => {
            const isAdding = adding === `${product.id}`;

            return (
              <div key={product.id} style={{
                background: "var(--surface)", borderRadius: "16px",
                border: "1.5px solid var(--border)",
                overflow: "hidden",
                boxShadow: "var(--shadow-sm)",
                transition: "transform 200ms, box-shadow 200ms",
                display: "flex", flexDirection: "column",
              }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLDivElement).style.transform = "translateY(-3px)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--shadow)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--shadow-sm)";
                }}
              >
                {/* Image area — links to detail page */}
                <Link href={`/products/${product.id}`} style={{ display: "block", textDecoration: "none" }}>
                  <div style={{
                    background: "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)",
                    height: "200px",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "3.5rem",
                    position: "relative",
                    overflow: "hidden",
                  }}>
                    {product.image_url.startsWith("http") ? (
                      <img
                        src={product.image_url}
                        alt={product.name}
                        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                        onError={(e) => {
                          const parent = (e.currentTarget as HTMLImageElement).parentElement!;
                          (e.currentTarget as HTMLImageElement).style.display = "none";
                          const fb = document.createElement("span");
                          fb.textContent = CATEGORY_ICONS[product.category] || "📦";
                          fb.style.fontSize = "3.5rem";
                          parent.appendChild(fb);
                        }}
                      />
                    ) : (
                      product.image_url
                    )}
                    <span style={{
                      position: "absolute", top: "10px", left: "10px",
                      background: "rgba(255,255,255,0.85)", backdropFilter: "blur(4px)",
                      padding: "3px 10px", borderRadius: "99px",
                      fontSize: "0.7rem", fontWeight: 600, color: "var(--primary)",
                      border: "1px solid rgba(79,70,229,0.2)",
                    }}>
                      {CATEGORY_ICONS[product.category] || "📦"} {product.category}
                    </span>
                  </div>
                </Link>

                {/* Content */}
                <div style={{ padding: "1rem", flex: 1, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <Link href={`/products/${product.id}`} style={{ textDecoration: "none" }}>
                    <h3 style={{ fontWeight: 700, fontSize: "0.95rem", lineHeight: "1.4", color: "var(--text)" }}>
                      {product.name}
                    </h3>
                  </Link>

                  {/* Rating */}
                  {product.rating > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <div style={{ display: "flex", gap: "1px" }}>
                        {[1, 2, 3, 4, 5].map((star) => {
                          const fill = Math.min(1, Math.max(0, product.rating - (star - 1)));
                          return (
                            <span key={star} style={{ position: "relative", fontSize: "0.8rem", lineHeight: 1 }}>
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
                      <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#92400e" }}>
                        {product.rating.toFixed(1)}
                      </span>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-3)" }}>
                        ({product.review_count.toLocaleString()})
                      </span>
                    </div>
                  )}

                  {/* Manufacturer */}
                  {product.manufacturer && (
                    <p style={{ fontSize: "0.7rem", color: "var(--text-3)", fontWeight: 500 }}>
                      By <span style={{ color: "var(--text-2)", fontWeight: 600 }}>{product.manufacturer}</span>
                    </p>
                  )}

                  <p style={{ color: "var(--text-2)", fontSize: "0.8rem", lineHeight: "1.5", flex: 1 }}>
                    {product.description.substring(0, 80)}…
                  </p>

                  {/* Price + actions */}
                  <div style={{ marginTop: "auto", paddingTop: "0.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.6rem" }}>
                      <span style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--primary)" }}>
                        ${product.price.toFixed(2)}
                      </span>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-3)" }}>
                        {product.stock > 20 ? "In stock" : product.stock > 0 ? `Only ${product.stock} left` : "Out of stock"}
                      </span>
                    </div>

                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      {/* View Details */}
                      <Link href={`/products/${product.id}`} style={{
                        flex: 1, display: "block", textAlign: "center",
                        padding: "0.5rem 0.75rem",
                        background: "var(--surface-2)",
                        color: "var(--text-2)",
                        borderRadius: "8px", fontWeight: 600, fontSize: "0.78rem",
                        border: "1.5px solid var(--border)",
                        transition: "all 150ms",
                      }}>
                        View Details
                      </Link>

                      {/* Quick Add — only for products with no options */}
                      {product.options.length === 0 && (
                        <button
                          onClick={() => {
                            setAdding(`${product.id}`);
                            addToCart(product.id, 1, {})
                              .then(() => {
                                setToast({ msg: `Added "${product.name}" to cart!`, ok: true });
                                setTimeout(() => setToast(null), 3000);
                              })
                              .catch(() => {
                                setToast({ msg: "Failed to add to cart", ok: false });
                                setTimeout(() => setToast(null), 3000);
                              })
                              .finally(() => setAdding(null));
                          }}
                          disabled={isAdding || product.stock === 0}
                          style={{
                            padding: "0.5rem 0.75rem",
                            background: product.stock === 0 ? "var(--surface-2)" : "var(--primary)",
                            color: product.stock === 0 ? "var(--text-3)" : "white",
                            borderRadius: "8px", fontWeight: 600, fontSize: "0.78rem",
                            border: `1.5px solid ${product.stock === 0 ? "var(--border)" : "var(--primary)"}`,
                            cursor: product.stock === 0 ? "not-allowed" : "pointer",
                            whiteSpace: "nowrap",
                            transition: "all 150ms",
                          }}
                        >
                          {isAdding ? "…" : "🛒"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {products.length === 0 && (
          <div style={{ textAlign: "center", padding: "4rem 2rem", color: "var(--text-3)" }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔍</div>
            <p style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-2)" }}>No products found</p>
            <p style={{ marginTop: "0.4rem" }}>Try adjusting your search or selecting a different category</p>
          </div>
        )}
      </div>

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
