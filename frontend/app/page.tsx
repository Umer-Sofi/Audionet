"use client";

import { useEffect, useRef, useState } from "react";
import Spectrum from "@/components/Spectrum";
import {
  fetchReceived,
  fetchStatus,
  getBackend,
  sendMessage,
  setBackend,
  type NodeStatus,
} from "@/lib/api";

interface Bubble {
  kind: "sent" | "recv";
  text: string;
  meta: string;
}

type Tab = "messages" | "spectrum";

export default function Page() {
  const [tab, setTab] = useState<Tab>("messages");
  const [status, setStatus] = useState<string>("connecting…");
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [toast, setToast] = useState<string | null>(null);

  const lastIdRef = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  };

  // Load persisted backend URL on mount.
  useEffect(() => {
    setBackendUrl(getBackend());
  }, []);

  // Auto-scroll to newest bubble.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [bubbles]);

  // Poll /status.
  useEffect(() => {
    const tick = async () => {
      try {
        setStatus(await fetchStatus());
      } catch {
        setStatus("server offline");
      }
    };
    tick();
    const id = setInterval(tick, 900);
    return () => clearInterval(id);
  }, []);

  // Poll /received for new messages.
  useEffect(() => {
    const tick = async () => {
      try {
        const r = await fetchReceived();
        if (r.id && r.id > lastIdRef.current && r.message) {
          lastIdRef.current = r.id;
          const freq = r.base_frequency ? `${(r.base_frequency / 1000).toFixed(1)} kHz` : "";
          const sync = r.sync_score != null ? ` · sync ${(r.sync_score * 100).toFixed(0)}%` : "";
          setBubbles((b) => [...b, { kind: "recv", text: r.message, meta: `received · ${freq}${sync}` }]);
        }
      } catch {
        /* transient */
      }
    };
    tick();
    const id = setInterval(tick, 700);
    return () => clearInterval(id);
  }, []);

  const onSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const res = await sendMessage(text);
      const freq = res.base_frequency ? `${(res.base_frequency / 1000).toFixed(1)} kHz` : "";
      setBubbles((b) => [...b, { kind: "sent", text, meta: `sent · ${freq}` }]);
      setInput("");
    } catch {
      showToast("Could not reach backend — check the URL");
    } finally {
      setSending(false);
    }
  };

  const statusClass = status.toLowerCase().includes("listen")
    ? "listening"
    : status.toLowerCase().includes("send")
    ? "sending"
    : "idle";

  return (
    <div className="app">
      <header>
        <div>
          <h1>🔊 AudioNet</h1>
          <span className="sub">text over sound</span>
        </div>
        <label className="backend">
          Backend:
          <input
            value={backendUrl}
            onChange={(e) => setBackendUrl(e.target.value)}
            onBlur={() => {
              setBackend(backendUrl);
              showToast(`Backend set to ${backendUrl}`);
            }}
          />
        </label>
        <div className="status">
          <span className={`dot ${statusClass}`} />
          <span>{status}</span>
        </div>
      </header>

      <div className="tabs">
        <div className={`tab ${tab === "messages" ? "active" : ""}`} onClick={() => setTab("messages")}>
          💬 Messages
        </div>
        <div className={`tab ${tab === "spectrum" ? "active" : ""}`} onClick={() => setTab("spectrum")}>
          📶 Spectrum
        </div>
      </div>

      <main>
        {tab === "messages" ? (
          <section className="view">
            <div className="messages">
              {bubbles.length === 0 ? (
                <div className="empty">
                  No messages yet. Type below and hit Send — this laptop&apos;s speaker plays it,
                  the other laptop&apos;s mic hears it and it appears there.
                </div>
              ) : (
                bubbles.map((b, i) => (
                  <div key={i} className={`bubble ${b.kind}`}>
                    {b.text}
                    <span className="meta">{b.meta}</span>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="composer">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && onSend()}
                placeholder="Type a message and press Enter…"
                autoComplete="off"
                disabled={sending}
              />
              <button onClick={onSend} disabled={sending}>
                {sending ? "Sending…" : "Send"}
              </button>
            </div>
          </section>
        ) : (
          <Spectrum onError={showToast} />
        )}
      </main>

      {toast && <div className="toast show">{toast}</div>}
    </div>
  );
}
