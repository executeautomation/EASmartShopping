"use client";
import { useEffect, useState } from "react";
import { fetchProducts, fetchSimilarProducts, addToCart, type Product } from "@/lib/api";

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

function isImageUrl(s: string) {
  return s.startsWith("http");
}

function isColorOption(name: string) {
  return name.toLowerCase().includes("color") || name.toLowerCase() === "wash" || name.toLowerCase() === "band color";
}

function toColor(val: string): string | null {
  for (const [k, v] of Object.entries(COLOR_MAP)) {
    if (val.toLowerCase().includes(k.toLowerCase())) return v;
  }
  return null;
}

interface Selections { [optionName: string]: string }

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [adding, setAdding] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [selections, setSelections] = useState<Record<number, Selections>>({});
  const [searchMode, setSearchMode] = useState<"keyword" | "semantic">("keyword");
  const [similarProducts, setSimilarProducts] = useState<Record<number, Product[]>>({});

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

  const setOption = (productId: number, optName: string, value: string) => {
    setSelections((prev) => ({
      ...prev,
      [productId]: { ...(prev[productId] || {}), [optName]: value },
    }));
  };

  const allOptionsSelected = (product: Product) => {
    if (!product.options.length) return true;
    const sel = selections[product.id] || {};
    return product.options.every((opt) => !!sel[opt.name]);
  };

  const handleAddToCart = async (product: Product) => {
    const key = `${product.id}`;
    if (!allOptionsSelected(product)) {
      showToast("Please select all options first", false);
      return;
    }
    setAdding(key);
    try {
      await addToCart(product.id, 1, selections[product.id] || {});
      showToast(`Added "${product.name}" to cart!`, true);
    } catch { showToast("Failed to add to cart", false); }
    finally { setAdding(null); }
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
            const sel = selections[product.id] || {};
            const ready = allOptionsSelected(product);
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
                  if (!similarProducts[product.id]) {
                    fetchSimilarProducts(product.id).then(similar => {
                      if (similar.length > 0) {
                        setSimilarProducts(prev => ({...prev, [product.id]: similar}));
                      }
                    });
                  }
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--shadow-sm)";
                }}
              >
                {/* Image area */}
                <div style={{
                  background: "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)",
                  height: "200px",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "3.5rem",
                  position: "relative",
                  overflow: "hidden",
                }}>
                  {isImageUrl(product.image_url) ? (
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

                {/* Content */}
                <div style={{ padding: "1rem", flex: 1, display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  <h3 style={{ fontWeight: 700, fontSize: "0.95rem", lineHeight: "1.4", color: "var(--text)" }}>
                    {product.name}
                  </h3>
                  <p style={{ color: "var(--text-2)", fontSize: "0.8rem", lineHeight: "1.5", flex: 1 }}>
                    {product.description.substring(0, 90)}…
                  </p>

                  {/* You might also like */}
                  {similarProducts[product.id] && similarProducts[product.id].length > 0 && (
                    <div style={{ marginTop: "0.25rem" }}>
                      <p style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--text-3)", marginBottom: "0.3rem" }}>
                        You might also like:
                      </p>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                        {similarProducts[product.id].slice(0, 3).map((sim) => (
                          <button
                            key={sim.id}
                            onClick={() => setCategory(sim.category)}
                            style={{
                              padding: "2px 8px",
                              background: "var(--surface-2)",
                              border: "1px solid var(--border)",
                              borderRadius: "99px",
                              fontSize: "0.68rem",
                              fontWeight: 500,
                              color: "var(--text-2)",
                              cursor: "pointer",
                              whiteSpace: "nowrap",
                              transition: "all 120ms",
                            }}
                            onMouseEnter={(e) => {
                              (e.currentTarget as HTMLButtonElement).style.background = "rgba(79,70,229,0.1)";
                              (e.currentTarget as HTMLButtonElement).style.color = "var(--primary)";
                              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--primary)";
                            }}
                            onMouseLeave={(e) => {
                              (e.currentTarget as HTMLButtonElement).style.background = "var(--surface-2)";
                              (e.currentTarget as HTMLButtonElement).style.color = "var(--text-2)";
                              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
                            }}
                          >
                            {CATEGORY_ICONS[sim.category] || "📦"} {sim.name.substring(0, 20)}{sim.name.length > 20 ? "…" : ""} ${sim.price.toFixed(0)}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Options */}
                  {product.options.map((opt) => (
                    <div key={opt.name}>
                      <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-2)", marginBottom: "0.35rem" }}>
                        {opt.name}
                        {sel[opt.name] && <span style={{ color: "var(--primary)", marginLeft: "0.4rem" }}>· {sel[opt.name]}</span>}
                      </p>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                        {opt.values.map((val) => {
                          const hex = isColorOption(opt.name) ? toColor(val) : null;
                          const selected = sel[opt.name] === val;
                          if (hex) {
                            return (
                              <button key={val} title={val} onClick={() => setOption(product.id, opt.name, val)} style={{
                                width: "24px", height: "24px", borderRadius: "50%",
                                background: hex, cursor: "pointer",
                                border: selected ? "3px solid var(--primary)" : "2px solid var(--border)",
                                outline: selected ? "2px solid white" : "none",
                                outlineOffset: "-4px",
                                boxShadow: selected ? "0 0 0 3px var(--primary)" : "var(--shadow-sm)",
                                transform: selected ? "scale(1.2)" : "scale(1)",
                                transition: "all 150ms",
                              }} />
                            );
                          }
                          return (
                            <button key={val} onClick={() => setOption(product.id, opt.name, val)} style={{
                              padding: "3px 10px", borderRadius: "6px", fontSize: "0.72rem", fontWeight: 500,
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
                  ))}

                  {/* Price + CTA */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto", paddingTop: "0.5rem" }}>
                    <div>
                      <span style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--primary)" }}>
                        ${product.price.toFixed(2)}
                      </span>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-3)", marginLeft: "0.4rem" }}>
                        {product.stock > 20 ? "In stock" : product.stock > 0 ? `Only ${product.stock} left` : "Out of stock"}
                      </span>
                    </div>
                    <button
                      onClick={() => handleAddToCart(product)}
                      disabled={isAdding || product.stock === 0}
                      style={{
                        padding: "0.5rem 1rem",
                        background: product.stock === 0 ? "var(--surface-2)" :
                                    !ready ? "var(--surface-2)" : "var(--primary)",
                        color: product.stock === 0 || !ready ? "var(--text-3)" : "white",
                        borderRadius: "8px", fontWeight: 600, fontSize: "0.8rem",
                        border: `1.5px solid ${!ready || product.stock === 0 ? "var(--border)" : "var(--primary)"}`,
                        cursor: product.stock === 0 ? "not-allowed" : "pointer",
                        transition: "all 150ms",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {isAdding ? "Adding…" : product.stock === 0 ? "Out of Stock" : !ready ? "Select options" : "Add to Cart"}
                    </button>
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
