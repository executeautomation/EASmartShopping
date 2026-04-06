"use client";
import { useState, useRef, useEffect } from "react";
import { getSessionId, addToCart, addBundleToCart, clearPendingOptions, type BundleItem } from "@/lib/api";

// A pending option item — same shape as BundleItem but with quantity + already_selected
interface PendingItem {
  product_id: number;
  name: string;
  price: number;
  image: string;
  options: { name: string; values: string[] }[];
  quantity: number;
  already_selected: Record<string, string>;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  products?: { id: number; name: string; price: number }[];
  bundle_items?: BundleItem[];
  pending_options?: PendingItem[];
}

// ── Shared: small product row ─────────────────────────────────────────────────

function ProductThumb({ item }: { item: { name: string; price: number; image: string; category?: string } }) {
  return (
    <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
      {item.image && item.image.startsWith("http") ? (
        <img
          src={item.image}
          alt={item.name}
          style={{
            width: 44, height: 44, borderRadius: "0.4rem",
            objectFit: "cover", flexShrink: 0, border: "1px solid #e5e7eb",
          }}
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
      ) : (
        <div style={{
          width: 44, height: 44, borderRadius: "0.4rem",
          background: "#f3f4f6", display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: "1.4rem", flexShrink: 0,
        }}>
          {item.image || "📦"}
        </div>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#1f2937", lineHeight: 1.3 }}>
          {item.name}
        </div>
        {item.category && (
          <div style={{ fontSize: "0.72rem", color: "#6b7280", marginTop: "0.1rem" }}>
            {item.category}
          </div>
        )}
      </div>
      <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#2563eb", flexShrink: 0, alignSelf: "center" }}>
        ${item.price.toFixed(2)}
      </div>
    </div>
  );
}

function OptionChips({
  opt,
  selected,
  disabled,
  onSelect,
}: {
  opt: { name: string; values: string[] };
  selected: string;
  disabled: boolean;
  onSelect: (val: string) => void;
}) {
  return (
    <div style={{ marginTop: "0.45rem" }}>
      <div style={{ fontSize: "0.7rem", color: "#6b7280", marginBottom: "0.25rem", fontWeight: 500 }}>
        {opt.name}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
        {opt.values.map((val) => {
          const isSelected = selected === val;
          return (
            <button
              key={val}
              onClick={() => onSelect(val)}
              disabled={disabled}
              style={{
                padding: "0.2rem 0.55rem",
                borderRadius: "999px",
                border: isSelected ? "1.5px solid #2563eb" : "1.5px solid #d1d5db",
                background: isSelected ? "#2563eb" : "white",
                color: isSelected ? "white" : "#374151",
                fontSize: "0.7rem",
                cursor: disabled ? "default" : "pointer",
                fontWeight: isSelected ? 600 : 400,
                transition: "all 0.15s",
              }}
            >
              {val}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Option Picker Card (single product needs options) ──────────────────────────

function OptionPickerCard({
  items,
  onAdded,
}: {
  items: PendingItem[];
  onAdded: () => void;
}) {
  const [selections, setSelections] = useState<Record<number, Record<string, string>>>(() => {
    const init: Record<number, Record<string, string>> = {};
    for (const item of items) {
      init[item.product_id] = { ...item.already_selected };
      for (const opt of item.options) {
        if (!init[item.product_id][opt.name] && opt.values.length > 0) {
          init[item.product_id][opt.name] = opt.values[0];
        }
      }
    }
    return init;
  });
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const [error, setError] = useState("");

  const handleSelect = (productId: number, optName: string, value: string) => {
    setSelections((prev) => ({ ...prev, [productId]: { ...prev[productId], [optName]: value } }));
  };

  const handleAdd = async () => {
    setAdding(true);
    setError("");
    try {
      for (const item of items) {
        await addToCart(item.product_id, item.quantity, selections[item.product_id] || {});
      }
      await clearPendingOptions();
      setAdded(true);
      onAdded();
    } catch {
      setError("Failed to add to cart. Please try again.");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div style={{
      background: "#f8faff",
      border: "1.5px solid #bfdbfe",
      borderRadius: "0.75rem",
      overflow: "hidden",
      marginTop: "0.5rem",
      width: "100%",
    }}>
      <div style={{
        background: "#2563eb", color: "white",
        padding: "0.6rem 0.9rem", fontSize: "0.82rem", fontWeight: 700,
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <span>🛍️ Choose your options</span>
        <span style={{ fontWeight: 600, opacity: 0.9 }}>
          {items.length > 1 ? `${items.length} items` : `$${items[0].price.toFixed(2)}`}
        </span>
      </div>

      <div style={{ padding: "0.6rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {items.map((item) => (
          <div key={item.product_id} style={{
            background: "white", borderRadius: "0.5rem",
            border: "1px solid #e5e7eb", padding: "0.5rem",
          }}>
            <ProductThumb item={item} />
            {item.options.map((opt) => (
              <OptionChips
                key={opt.name}
                opt={opt}
                selected={selections[item.product_id]?.[opt.name] || ""}
                disabled={added}
                onSelect={(val) => handleSelect(item.product_id, opt.name, val)}
              />
            ))}
          </div>
        ))}
      </div>

      <div style={{ padding: "0.6rem", paddingTop: 0 }}>
        {error && <div style={{ color: "#dc2626", fontSize: "0.72rem", marginBottom: "0.4rem" }}>{error}</div>}
        <button
          onClick={handleAdd}
          disabled={adding || added}
          style={{
            width: "100%", padding: "0.55rem",
            background: added ? "#16a34a" : adding ? "#93c5fd" : "#2563eb",
            color: "white", border: "none", borderRadius: "0.5rem",
            fontSize: "0.82rem", fontWeight: 700,
            cursor: adding || added ? "default" : "pointer",
            transition: "background 0.2s",
          }}
        >
          {added ? "✅ Added to Cart!" : adding ? "Adding…" : "🛒 Add to Cart"}
        </button>
      </div>
    </div>
  );
}

// ── Markdown table parser ─────────────────────────────────────────────────────

type TextSegment  = { type: "text";  value: string };
type TableSegment = { type: "table"; headers: string[]; rows: string[][] };
type ContentSegment = TextSegment | TableSegment;

function parseMarkdownContent(text: string): ContentSegment[] {
  const segments: ContentSegment[] = [];
  const lines = text.split("\n");
  const textBuf: string[] = [];
  let i = 0;

  const flushText = () => {
    const v = textBuf.splice(0).join("\n").trim();
    if (v) segments.push({ type: "text", value: v });
  };

  while (i < lines.length) {
    if (lines[i].trim().startsWith("|")) {
      flushText();
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      const isSep = (l: string) => /^\s*\|[\s:\-|]+\|\s*$/.test(l);
      const parseRow = (l: string) =>
        l.split("|").slice(1, -1).map((c) => c.trim().replace(/^\*\*|\*\*$/g, "").replace(/^`|`$/g, ""));
      const dataLines = tableLines.filter((l) => !isSep(l));
      if (dataLines.length >= 2) {
        segments.push({ type: "table", headers: parseRow(dataLines[0]), rows: dataLines.slice(1).map(parseRow) });
      } else {
        segments.push({ type: "text", value: tableLines.join("\n") });
      }
    } else {
      textBuf.push(lines[i]);
      i++;
    }
  }
  flushText();
  return segments;
}

// ── Interactive comparison table component ───────────────────────────────────

function ComparisonTable({
  headers, rows, products,
}: {
  headers: string[];
  rows: string[][];
  products?: { id: number; name: string; price: number }[];
}) {
  const [adding, setAdding] = useState<number | null>(null);
  const [added, setAdded]   = useState<Set<number>>(new Set());

  // Map column index → product (skip col 0 = feature label column)
  const colProducts: Array<{ id: number; name: string; price: number } | null> = headers.map((h, ci) => {
    if (ci === 0) return null;
    return products?.find((p) => h.toLowerCase().includes(p.name.toLowerCase().split(" ")[0])) ?? null;
  });

  const handleAdd = async (colIdx: number) => {
    const prod = colProducts[colIdx];
    if (!prod) return;
    setAdding(colIdx);
    try {
      await addToCart(prod.id, 1, {});
      window.dispatchEvent(new Event("cart-updated"));
      setAdded((prev) => new Set([...prev, colIdx]));
    } catch { /* ignore */ }
    setAdding(null);
  };

  // Detect "recommendation" rows to highlight
  const isRecommendRow = (row: string[]) =>
    row[0]?.toLowerCase().includes("recommend") || row[0]?.toLowerCase().includes("best for") || row[0]?.toLowerCase().includes("verdict");

  const colCount = headers.length;

  return (
    <div style={{
      marginTop: "0.5rem",
      borderRadius: "0.75rem",
      overflow: "hidden",
      border: "1px solid rgba(37,99,235,0.15)",
      boxShadow: "0 2px 12px rgba(37,99,235,0.08)",
      fontSize: "0.8rem",
    }}>
      {/* Header row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: `1fr ${Array(colCount - 1).fill("1fr").join(" ")}`,
        background: "linear-gradient(135deg,#1e3a8a,#2563eb)",
        color: "white",
      }}>
        {headers.map((h, ci) => (
          <div key={ci} style={{
            padding: "0.6rem 0.7rem",
            fontWeight: 600,
            fontSize: ci === 0 ? "0.72rem" : "0.78rem",
            textTransform: ci === 0 ? "uppercase" : "none",
            letterSpacing: ci === 0 ? "0.04em" : 0,
            opacity: ci === 0 ? 0.75 : 1,
            borderLeft: ci > 0 ? "1px solid rgba(255,255,255,0.15)" : "none",
          }}>{h}</div>
        ))}
      </div>

      {/* Data rows */}
      {rows.map((row, ri) => {
        const isRec = isRecommendRow(row);
        return (
          <div key={ri} style={{
            display: "grid",
            gridTemplateColumns: `1fr ${Array(colCount - 1).fill("1fr").join(" ")}`,
            background: isRec ? "rgba(37,99,235,0.06)" : ri % 2 === 0 ? "white" : "#f8faff",
            borderTop: "1px solid rgba(37,99,235,0.07)",
          }}>
            {row.map((cell, ci) => (
              <div key={ci} style={{
                padding: "0.5rem 0.7rem",
                color: isRec ? "#1d4ed8" : ci === 0 ? "#6b7280" : "#1f2937",
                fontWeight: isRec ? 600 : ci === 0 ? 500 : 400,
                fontSize: ci === 0 ? "0.72rem" : "0.78rem",
                borderLeft: ci > 0 ? "1px solid rgba(37,99,235,0.07)" : "none",
                lineHeight: 1.4,
              }}>{cell}</div>
            ))}
          </div>
        );
      })}

      {/* Add to cart row — only show if we matched any product */}
      {colProducts.some((p) => p !== null) && (
        <div style={{
          display: "grid",
          gridTemplateColumns: `1fr ${Array(colCount - 1).fill("1fr").join(" ")}`,
          background: "#f0f7ff",
          borderTop: "1px solid rgba(37,99,235,0.1)",
          padding: "0.4rem 0",
        }}>
          <div style={{ padding: "0 0.7rem", display: "flex", alignItems: "center" }}>
            <span style={{ fontSize: "0.7rem", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.04em" }}>Add to Cart</span>
          </div>
          {colProducts.slice(1).map((prod, ci) => {
            const colIdx = ci + 1;
            const isAdded = added.has(colIdx);
            return (
              <div key={ci} style={{ padding: "0.35rem 0.5rem", borderLeft: "1px solid rgba(37,99,235,0.07)" }}>
                {prod ? (
                  <button
                    onClick={() => handleAdd(colIdx)}
                    disabled={adding === colIdx || isAdded}
                    style={{
                      width: "100%",
                      padding: "0.3rem 0.4rem",
                      borderRadius: "0.4rem",
                      border: "none",
                      background: isAdded ? "#d1fae5" : "linear-gradient(135deg,#1d4ed8,#3b82f6)",
                      color: isAdded ? "#065f46" : "white",
                      fontSize: "0.72rem",
                      fontWeight: 600,
                      cursor: isAdded ? "default" : "pointer",
                      opacity: adding === colIdx ? 0.7 : 1,
                      transition: "all 0.2s",
                    }}
                  >
                    {isAdded ? "✓ Added" : adding === colIdx ? "Adding…" : `+ Add $${prod.price.toFixed(2)}`}
                  </button>
                ) : (
                  <div style={{ fontSize: "0.68rem", color: "#d1d5db", textAlign: "center" }}>—</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BundleCard({ items, onAdded }: { items: BundleItem[]; onAdded: () => void }) {
  // localItems is mutable — user can remove items before adding
  const [localItems, setLocalItems] = useState<BundleItem[]>(items);
  const [selections, setSelections] = useState<Record<number, Record<string, string>>>(() => {
    const init: Record<number, Record<string, string>> = {};
    for (const item of items) {
      init[item.product_id] = {};
      for (const opt of item.options) {
        if (opt.values.length > 0) init[item.product_id][opt.name] = opt.values[0];
      }
    }
    return init;
  });
  const [adding, setAdding]   = useState(false);
  const [added, setAdded]     = useState(false);
  const [error, setError]     = useState("");
  const [removed, setRemoved] = useState<Set<number>>(new Set());

  const activeItems = localItems.filter((i) => !removed.has(i.product_id));
  const total       = activeItems.reduce((s, i) => s + i.price, 0);

  const removeItem = (productId: number) => {
    setRemoved((prev) => new Set([...prev, productId]));
  };

  const handleAdd = async () => {
    if (activeItems.length === 0) return;
    setAdding(true); setError("");
    try {
      await addBundleToCart(activeItems.map((item) => ({
        product_id: item.product_id,
        selected_options: selections[item.product_id] || {},
      })));
      setAdded(true); onAdded();
    } catch { setError("Failed to add bundle. Please try again."); }
    finally { setAdding(false); }
  };

  if (activeItems.length === 0) {
    return (
      <div style={{ background: "#f8faff", border: "1.5px solid #bfdbfe", borderRadius: "0.75rem", padding: "1rem", textAlign: "center", marginTop: "0.5rem", fontSize: "0.82rem", color: "#6b7280" }}>
        All items removed from bundle.
      </div>
    );
  }

  return (
    <div style={{ background: "#f8faff", border: "1.5px solid #bfdbfe", borderRadius: "0.75rem", overflow: "hidden", marginTop: "0.5rem", width: "100%" }}>
      {/* Header */}
      <div style={{ background: "#2563eb", color: "white", padding: "0.6rem 0.9rem", fontSize: "0.82rem", fontWeight: 700, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>🎁 Bundle — {activeItems.length} item{activeItems.length !== 1 ? "s" : ""}</span>
        <span style={{ opacity: 0.9 }}>${total.toFixed(2)} total</span>
      </div>

      {/* Item list */}
      <div style={{ padding: "0.6rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {localItems.map((item) => {
          const isRemoved = removed.has(item.product_id);
          return (
            <div key={item.product_id} style={{
              background: isRemoved ? "#f9fafb" : "white",
              borderRadius: "0.5rem",
              border: `1px solid ${isRemoved ? "#e5e7eb" : "#e5e7eb"}`,
              padding: "0.5rem",
              opacity: isRemoved ? 0.4 : 1,
              transition: "opacity 0.2s",
              position: "relative",
            }}>
              {/* Remove button */}
              {!added && (
                <button
                  onClick={() => isRemoved ? setRemoved((p) => { const s = new Set(p); s.delete(item.product_id); return s; }) : removeItem(item.product_id)}
                  title={isRemoved ? "Restore item" : "Remove from bundle"}
                  style={{
                    position: "absolute", top: "4px", right: "4px",
                    width: 20, height: 20, borderRadius: "50%",
                    background: isRemoved ? "#d1fae5" : "#fee2e2",
                    border: "none", cursor: "pointer",
                    fontSize: "0.65rem", fontWeight: 700,
                    color: isRemoved ? "#16a34a" : "#dc2626",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    lineHeight: 1,
                  }}
                >
                  {isRemoved ? "+" : "×"}
                </button>
              )}
              <ProductThumb item={item} />
              {!isRemoved && item.options.map((opt) => (
                <OptionChips key={opt.name} opt={opt}
                  selected={selections[item.product_id]?.[opt.name] || ""}
                  disabled={added}
                  onSelect={(val) => setSelections((prev) => ({ ...prev, [item.product_id]: { ...prev[item.product_id], [opt.name]: val } }))}
                />
              ))}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: "0.6rem", paddingTop: 0 }}>
        {removed.size > 0 && !added && (
          <div style={{ fontSize: "0.72rem", color: "#6b7280", marginBottom: "0.4rem", textAlign: "center" }}>
            {removed.size} item{removed.size > 1 ? "s" : ""} removed · click <strong>+</strong> to restore
          </div>
        )}
        {error && <div style={{ color: "#dc2626", fontSize: "0.72rem", marginBottom: "0.4rem" }}>{error}</div>}
        <button onClick={handleAdd} disabled={adding || added || activeItems.length === 0} style={{
          width: "100%", padding: "0.55rem",
          background: added ? "#16a34a" : adding ? "#93c5fd" : "#2563eb",
          color: "white", border: "none", borderRadius: "0.5rem",
          fontSize: "0.82rem", fontWeight: 700,
          cursor: adding || added ? "default" : "pointer", transition: "background 0.2s",
        }}>
          {added ? "✅ Bundle Added to Cart!" : adding ? "Adding…" : `🛒 Add ${activeItems.length} Item${activeItems.length !== 1 ? "s" : ""} to Cart`}
        </button>
      </div>
    </div>
  );
}

// ── ChatWidget ───────────────────────────────────────────────────────────────

// Inject keyframe animations once
const CHAT_STYLES = `
  @keyframes chatOpen {
    from { opacity: 0; transform: scale(0.94) translateY(14px); }
    to   { opacity: 1; transform: scale(1)    translateY(0);    }
  }
  @keyframes chatClose {
    from { opacity: 1; transform: scale(1)    translateY(0);    }
    to   { opacity: 0; transform: scale(0.94) translateY(14px); }
  }
  @keyframes msgIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0);   }
  }
  @keyframes fabPulse {
    0%, 100% { box-shadow: 0 4px 16px rgba(37,99,235,0.45); }
    50%       { box-shadow: 0 4px 28px rgba(37,99,235,0.7);  }
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  .chat-msg { animation: msgIn 0.22s ease both; }
  .chat-scrollbar::-webkit-scrollbar { width: 4px; }
  .chat-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .chat-scrollbar::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
  .chat-input:focus { border-color: #2563eb !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.15); }
  .chat-send:hover:not(:disabled) { background: #1d4ed8 !important; transform: scale(1.07); }
  .chat-send { transition: background 0.15s, transform 0.15s; }
`;

export default function ChatWidget() {
  const [isOpen, setIsOpen]           = useState(false);
  const [isClosing, setIsClosing]     = useState(false);
  const [size, setSize]               = useState({ width: 440, height: 580 });
  const [activeBundleIdx, setActiveBundleIdx] = useState<number>(-1);
  const [messages, setMessages]       = useState<Message[]>([
    { id: "init", role: "assistant", content: "Hi! I'm your EA SmartKart assistant. Ask me about products, compare items, or say \"build me a gaming PC\" to get an interactive bundle! 🛍️" },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const resizeOrigin   = useRef<{ x: number; y: number; w: number; h: number } | null>(null);
  const styleInjected  = useRef(false);

  // Inject CSS once
  useEffect(() => {
    if (styleInjected.current) return;
    styleInjected.current = true;
    const el = document.createElement("style");
    el.textContent = CHAT_STYLES;
    document.head.appendChild(el);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const refreshCart = () => window.dispatchEvent(new Event("cart-updated"));

  // ── Resize via top-left grip ──────────────────────────────────────────────
  const onResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    resizeOrigin.current = { x: e.clientX, y: e.clientY, w: size.width, h: size.height };

    const onMove = (ev: MouseEvent) => {
      if (!resizeOrigin.current) return;
      const { x, y, w, h } = resizeOrigin.current;
      setSize({
        width:  Math.max(360, Math.min(720, w + (x - ev.clientX))),
        height: Math.max(460, Math.min(Math.floor(window.innerHeight * 0.88), h + (y - ev.clientY))),
      });
    };
    const onUp = () => {
      resizeOrigin.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  // ── Open / close with animation ───────────────────────────────────────────
  const openWidget = () => { setIsClosing(false); setIsOpen(true); };
  const closeWidget = () => {
    setIsClosing(true);
    setTimeout(() => { setIsOpen(false); setIsClosing(false); }, 220);
  };

  // ── Chat send ─────────────────────────────────────────────────────────────
  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setLoading(true);

    const msgId = `msg_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

    setMessages((prev) => [
      ...prev,
      { id: `u_${msgId}`, role: "user", content: userMsg },
      { id: msgId, role: "assistant", content: "", streaming: true },
    ]);

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, session_id: getSessionId() }),
      });
      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (!payload) continue;
          try {
            const data = JSON.parse(payload);
            if (data.type === "chunk") {
              setMessages((prev) => {
                const msgs = [...prev];
                const last = msgs[msgs.length - 1];
                msgs[msgs.length - 1] = { ...last, content: last.content + data.content };
                return msgs;
              });
            } else if (data.type === "done") {
              setMessages((prev) => {
                const msgs = [...prev];
                const last = msgs[msgs.length - 1];
                msgs[msgs.length - 1] = {
                  ...last,
                  streaming: false,
                  products:        data.products_mentioned,
                  bundle_items:    data.bundle_items    ?? undefined,
                  pending_options: data.pending_options ?? undefined,
                };
                if (data.bundle_items?.length) setActiveBundleIdx(msgs.length - 1);
                return msgs;
              });
              if (data.cart_updated) refreshCart();
            } else if (data.type === "error") {
              setMessages((prev) => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { id: msgId, role: "assistant", content: "Sorry, something went wrong. Please try again." };
                return msgs;
              });
            }
          } catch { /* skip malformed SSE */ }
        }
      }
    } catch {
      setMessages((prev) => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: "Sorry, something went wrong. Please try again." };
        return msgs;
      });
    } finally {
      setLoading(false);
    }
  };

  // ── FAB (closed state) ────────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <button
        onClick={openWidget}
        title="Open Shopping Assistant"
        style={{
          position: "fixed", bottom: "1.5rem", right: "1.5rem",
          width: "58px", height: "58px", borderRadius: "50%",
          background: "linear-gradient(135deg, #1d4ed8, #3b82f6)",
          color: "white", border: "none", fontSize: "1.4rem",
          cursor: "pointer", zIndex: 1000,
          animation: "fabPulse 3s ease-in-out infinite",
          transition: "transform 0.15s",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
        onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
      >
        🤖
      </button>
    );
  }

  // ── Widget ────────────────────────────────────────────────────────────────
  return (
    <div style={{
      position: "fixed",
      bottom: "1.5rem", right: "1.5rem",
      width: `${size.width}px`, height: `${size.height}px`,
      background: "#ffffff",
      borderRadius: "1.125rem",
      boxShadow: "0 12px 40px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08)",
      display: "flex", flexDirection: "column",
      zIndex: 1000, overflow: "hidden",
      animation: isClosing ? "chatClose 0.22s ease forwards" : "chatOpen 0.25s cubic-bezier(0.34,1.3,0.64,1) both",
      border: "1px solid rgba(37,99,235,0.12)",
    }}>

      {/* ── Resize grip (top-left corner) ─────────────────────────────────── */}
      <div
        onMouseDown={onResizeStart}
        title="Drag to resize"
        style={{
          position: "absolute", top: 0, left: 0,
          width: "22px", height: "22px",
          cursor: "nw-resize",
          zIndex: 10,
          display: "flex", alignItems: "flex-start", justifyContent: "flex-start",
          padding: "5px",
        }}
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <circle cx="2" cy="2" r="1.2" fill="rgba(255,255,255,0.6)" />
          <circle cx="6" cy="2" r="1.2" fill="rgba(255,255,255,0.6)" />
          <circle cx="2" cy="6" r="1.2" fill="rgba(255,255,255,0.6)" />
          <circle cx="6" cy="6" r="1.2" fill="rgba(255,255,255,0.6)" />
        </svg>
      </div>

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div style={{
        background: "linear-gradient(135deg, #1d4ed8 0%, #2563eb 60%, #3b82f6 100%)",
        color: "white",
        padding: "0.875rem 1rem 0.875rem 1.25rem",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        flexShrink: 0,
        boxShadow: "0 2px 8px rgba(37,99,235,0.3)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div style={{
            width: 34, height: 34, borderRadius: "50%",
            background: "rgba(255,255,255,0.18)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "1.1rem",
          }}>🤖</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: "0.92rem", letterSpacing: "0.01em" }}>
              SmartKart Assistant
            </div>
            <div style={{ fontSize: "0.7rem", opacity: 0.8, marginTop: "1px", display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80", display: "inline-block" }} />
              Online · Powered by AI
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.4rem" }}>
          <button
            onClick={() => { setMessages([{ id: "init", role: "assistant", content: "Chat cleared! How can I help you?" }]); setActiveBundleIdx(-1); }}
            title="Clear chat"
            style={{
              background: "rgba(255,255,255,0.15)", border: "none", color: "white",
              width: 30, height: 30, borderRadius: "50%",
              cursor: "pointer", fontSize: "0.8rem",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.28)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.15)")}
          >🗑️</button>
          <button
            onClick={closeWidget}
            title="Close"
            style={{
              background: "rgba(255,255,255,0.15)", border: "none", color: "white",
              width: 30, height: 30, borderRadius: "50%",
              cursor: "pointer", fontSize: "1rem",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.28)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.15)")}
          >✕</button>
        </div>
      </div>

      {/* ── Messages ──────────────────────────────────────────────────────── */}
      <div
        className="chat-scrollbar"
        style={{
          flex: 1, overflowY: "auto", padding: "1rem",
          display: "flex", flexDirection: "column", gap: "0.65rem",
          background: "linear-gradient(180deg, #f8faff 0%, #f1f5ff 100%)",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            className="chat-msg"
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: (msg.bundle_items || msg.pending_options || (!msg.streaming && parseMarkdownContent(msg.content).some(s => s.type === "table"))) ? "100%" : "88%",
              width:    (msg.bundle_items || msg.pending_options || (!msg.streaming && parseMarkdownContent(msg.content).some(s => s.type === "table"))) ? "100%" : undefined,
              animationDelay: `${Math.min(i * 0.04, 0.2)}s`,
            }}
          >
            {/* Avatar row for assistant */}
            {msg.role === "assistant" && (msg.content || msg.streaming) && (() => {
              const segments = msg.streaming ? null : parseMarkdownContent(msg.content);
              const hasTable = segments?.some((s) => s.type === "table");
              return (
                <div style={{ display: "flex", alignItems: "flex-end", gap: "0.4rem" }}>
                  <div style={{
                    width: 26, height: 26, borderRadius: "50%",
                    background: "linear-gradient(135deg,#1d4ed8,#3b82f6)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "0.75rem", flexShrink: 0, marginBottom: "2px",
                    alignSelf: "flex-start", marginTop: "4px",
                  }}>🤖</div>
                  <div style={{
                    background: "white",
                    color: "#1f2937",
                    padding: "0.7rem 0.9rem",
                    borderRadius: "0.2rem 0.9rem 0.9rem 0.9rem",
                    fontSize: "0.875rem", lineHeight: "1.5",
                    whiteSpace: "pre-wrap",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                    border: "1px solid rgba(37,99,235,0.08)",
                    maxWidth: hasTable ? "calc(100% - 34px)" : "calc(100% - 34px)",
                    minWidth: hasTable ? "min(100%, 320px)" : undefined,
                  }}>
                    {msg.streaming ? (
                      <>
                        {msg.content}
                        <span style={{ display: "inline-block", width: "2px", height: "14px", background: "#2563eb", marginLeft: "2px", verticalAlign: "middle", animation: "blink 1s step-end infinite" }} />
                      </>
                    ) : (
                      segments!.map((seg, si) =>
                        seg.type === "text" ? (
                          <span key={si} style={{ whiteSpace: "pre-wrap", display: "block" }}>{seg.value}</span>
                        ) : (
                          <ComparisonTable key={si} headers={seg.headers} rows={seg.rows} products={msg.products} />
                        )
                      )
                    )}
                  </div>
                </div>
              );
            })()}

            {/* User bubble */}
            {msg.role === "user" && (
              <div style={{
                background: "linear-gradient(135deg, #1d4ed8, #3b82f6)",
                color: "white",
                padding: "0.7rem 0.9rem",
                borderRadius: "0.9rem 0.2rem 0.9rem 0.9rem",
                fontSize: "0.875rem", lineHeight: "1.5",
                whiteSpace: "pre-wrap",
                boxShadow: "0 2px 8px rgba(37,99,235,0.25)",
              }}>
                {msg.content}
              </div>
            )}

            {/* Interactive bundle card — only active for the latest bundle request */}
            {!msg.streaming && msg.bundle_items && msg.bundle_items.length > 0 && (
              <div style={{ marginLeft: "30px" }}>
                {i === activeBundleIdx ? (
                  <BundleCard items={msg.bundle_items} onAdded={refreshCart} />
                ) : (
                  <div style={{
                    marginTop: "0.4rem",
                    padding: "0.4rem 0.7rem",
                    background: "#f3f4f6",
                    borderRadius: "0.5rem",
                    fontSize: "0.72rem",
                    color: "#9ca3af",
                    border: "1px solid #e5e7eb",
                    display: "flex", alignItems: "center", gap: "0.3rem",
                  }}>
                    <span>🔒</span> Bundle superseded — scroll down for the active one
                  </div>
                )}
              </div>
            )}

            {/* Interactive option picker */}
            {!msg.streaming && msg.pending_options && msg.pending_options.length > 0 && (
              <div style={{ marginLeft: "30px" }}>
                <OptionPickerCard items={msg.pending_options} onAdded={refreshCart} />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input ─────────────────────────────────────────────────────────── */}
      <div style={{
        padding: "0.75rem 0.875rem",
        borderTop: "1px solid rgba(37,99,235,0.1)",
        display: "flex", gap: "0.5rem", alignItems: "center",
        background: "white",
        flexShrink: 0,
      }}>
        <input
          className="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about products, build a bundle…"
          disabled={loading}
          style={{
            flex: 1, padding: "0.6rem 1rem",
            border: "1.5px solid #e5e7eb", borderRadius: "1.5rem",
            outline: "none", fontSize: "0.875rem",
            background: "#f8faff",
            transition: "border-color 0.15s, box-shadow 0.15s",
            color: "#1f2937",
            opacity: loading ? 0.6 : 1,
          }}
        />
        <button
          className="chat-send"
          onClick={handleSend}
          disabled={loading}
          style={{
            background: loading
              ? "#93c5fd"
              : "linear-gradient(135deg, #1d4ed8, #3b82f6)",
            color: "white", border: "none", borderRadius: "50%",
            width: "40px", height: "40px", flexShrink: 0,
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: "1rem",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: loading ? "none" : "0 2px 8px rgba(37,99,235,0.35)",
          }}
        >
          {loading
            ? <span style={{ display: "inline-block", width: 16, height: 16, border: "2.5px solid rgba(255,255,255,0.4)", borderTopColor: "white", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
            : "➤"}
        </button>
      </div>
    </div>
  );
}
