"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Radar from "@/components/Radar";
import Waveform from "@/components/Waveform";
import MetricTile from "@/components/MetricTile";
import { useMic } from "@/lib/useMic";
import {
  fetchConfig,
  fetchReceived,
  fetchStatus,
  getBackend,
  sendMessage,
  setBackend,
  setDevice,
  type Config,
} from "@/lib/api";

interface RxMessage {
  id: number;
  message: string;
  base_frequency: number | null;
  sync_score: number | null;
  source: number | null;
  to: number | null;
  at: string;
}

type Tab = "send" | "receive" | "status";

function fmtUptime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const hh = String(Math.floor(s / 3600)).padStart(2, "0");
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

export default function Page() {
  const [tab, setTab] = useState<Tab>("send");
  const [status, setStatus] = useState("connecting…");
  const [config, setConfig] = useState<Config | null>(null);
  const [messages, setMessages] = useState<RxMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [lastSend, setLastSend] = useState<{ duration: number; freq: number } | null>(null);
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [showSettings, setShowSettings] = useState(false);
  const [now, setNow] = useState(0);
  const [toast, setToast] = useState<string | null>(null);

  // device addressing
  const [myAddress, setMyAddress] = useState(1);
  const [myName, setMyName] = useState("Device");
  const [broadcast, setBroadcast] = useState(true);
  const [target, setTarget] = useState(2); // destination device id when not broadcasting
  const [peers, setPeers] = useState<number[]>([]);

  const lastIdRef = useRef(0);
  const startRef = useRef(0);

  const expectedFreqs = useMemo(() => {
    if (!config) return [];
    return config.frequencies.flatMap((f) => [f, f + config.freq_shift]);
  }, [config]);
  const mic = useMic(expectedFreqs);

  const showToast = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(null), 2200);
  };

  // init
  useEffect(() => {
    setBackendUrl(getBackend());
    startRef.current = Date.now();
    setNow(Date.now());
    mic.start(); // ask for mic so metrics + waveform are live (falls back to "—")
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // uptime ticker
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // poll status
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

  // load config (retry until reachable)
  useEffect(() => {
    let done = false;
    const tick = async () => {
      try {
        const c = await fetchConfig();
        setConfig(c);
        setMyAddress(c.device_address);
        setMyName(c.device_name);
        done = true;
      } catch {
        /* retry */
      }
    };
    tick();
    const id = setInterval(() => {
      if (done) clearInterval(id);
      else tick();
    }, 1500);
    return () => clearInterval(id);
  }, []);

  // poll received
  useEffect(() => {
    const tick = async () => {
      try {
        const r = await fetchReceived();
        if (r.id && r.id > lastIdRef.current && r.message) {
          lastIdRef.current = r.id;
          setMessages((m) => [
            ...m,
            {
              id: r.id,
              message: r.message,
              base_frequency: r.base_frequency,
              sync_score: r.sync_score,
              source: r.source,
              to: r.to,
              at: new Date().toLocaleTimeString(),
            },
          ]);
          if (r.source != null && r.source > 0) {
            setPeers((p) => (p.includes(r.source!) ? p : [...p, r.source!]));
          }
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
    const dst = broadcast ? 0 : target;
    setSending(true);
    try {
      const res = await sendMessage(text, dst);
      setLastSend({ duration: res.duration_seconds, freq: res.base_frequency });
      showToast(dst === 0 ? "Broadcast to all devices" : `Sent to device #${dst}`);
      setInput("");
    } catch {
      showToast("Could not reach backend — check settings");
    } finally {
      setSending(false);
    }
  };

  const saveIdentity = async () => {
    try {
      const d = await setDevice(myAddress, myName);
      setMyAddress(d.address);
      setMyName(d.name);
      showToast(`This device is now #${d.address} (${d.name})`);
    } catch {
      showToast("Could not update device identity");
    }
  };

  // derived
  const connected = status !== "server offline";
  const isSending = status === "Sending";
  const isListening = status === "Listening";
  const last = messages[messages.length - 1] ?? null;
  const freqKHz = ((last?.base_frequency ?? config?.default_frequency ?? 18600) / 1000).toFixed(1);
  const bwKHz = ((config?.freq_shift ?? 600) / 1000).toFixed(1);
  const bitrate = config?.baud ?? "—";
  const confidence = last?.sync_score != null ? `${(last.sync_score * 100).toFixed(1)}%` : "—";
  const uptime = startRef.current ? fmtUptime(now - startRef.current) : "00:00:00";
  const m = mic.metrics;
  const snrTxt = m.snrDb != null ? `${m.snrDb} dB` : "—";
  const noiseTxt = m.noiseDb != null ? `${m.noiseDb} dB` : "—";
  const offsetTxt = m.offsetHz != null ? `${m.offsetHz > 0 ? "+" : ""}${m.offsetHz} Hz` : "—";

  return (
    <div className={`app ${tab}`}>
      <header>
        <div className="brand">
          <span className="logo">〜</span>
          <div>
            <h1>AudioNet</h1>
            <span className="sub">Ultrasonic Communication</span>
          </div>
        </div>

        <div className="myid" title="This device's address">
          {myName} <b>#{myAddress}</b>
        </div>
        <div className={`conn ${connected ? "on" : "off"}`}>
          <span className="dot" /> {connected ? "Connected" : "Offline"}
        </div>
        <button className="gear" onClick={() => setShowSettings((s) => !s)} title="Settings">
          ⚙
        </button>
      </header>

      {showSettings && (
        <div className="settings">
          <label>
            Backend URL
            <input
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              onBlur={() => {
                setBackend(backendUrl);
                showToast(`Backend set to ${backendUrl}`);
              }}
            />
          </label>
          <label>
            My Device ID
            <input
              type="number"
              min={1}
              max={255}
              value={myAddress}
              onChange={(e) => setMyAddress(Number(e.target.value))}
              style={{ width: 90 }}
            />
          </label>
          <label>
            Device Name
            <input
              value={myName}
              onChange={(e) => setMyName(e.target.value)}
              style={{ width: 140 }}
            />
          </label>
          <button onClick={saveIdentity}>Save identity</button>
          <button onClick={() => (mic.active ? mic.stop() : mic.start())}>
            {mic.active ? "Disable mic metrics" : "Enable mic metrics"}
          </button>
        </div>
      )}

      <nav className="tabs">
        <button className={tab === "send" ? "active" : ""} onClick={() => setTab("send")}>
          ➤ Send
        </button>
        <button className={tab === "receive" ? "active" : ""} onClick={() => setTab("receive")}>
          ⭳ Receive
        </button>
        <button className={tab === "status" ? "active" : ""} onClick={() => setTab("status")}>
          〜 Status
        </button>
      </nav>

      <main>
        {/* ---------------- SEND ---------------- */}
        {tab === "send" && (
          <div className="stack">
            <section className="card">
              <h2>Send Message</h2>
              <div className="target">
                <span className="target-label">Send to:</span>
                <button
                  className={`chip ${broadcast ? "on" : ""}`}
                  onClick={() => setBroadcast(true)}
                >
                  📢 Broadcast (all)
                </button>
                <button
                  className={`chip ${!broadcast ? "on" : ""}`}
                  onClick={() => setBroadcast(false)}
                >
                  🎯 Device
                </button>
                {!broadcast && (
                  <>
                    <input
                      className="target-id"
                      type="number"
                      min={1}
                      max={255}
                      value={target}
                      onChange={(e) => setTarget(Number(e.target.value))}
                    />
                    {peers.length > 0 && (
                      <span className="peers">
                        seen:{" "}
                        {peers.map((p) => (
                          <button key={p} className="peer" onClick={() => setTarget(p)}>
                            #{p}
                          </button>
                        ))}
                      </span>
                    )}
                  </>
                )}
              </div>
              <div className="composer">
                <textarea
                  value={input}
                  maxLength={500}
                  placeholder="Type a message to transmit over sound…"
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSend();
                  }}
                />
                <span className="counter">{input.length} / 500</span>
                <button className="primary" onClick={onSend} disabled={sending || !input.trim()}>
                  ➤ {sending ? "Sending…" : "Send Message"}
                </button>
              </div>
            </section>

            <section className="card">
              <h2>Transmission Status</h2>
              <div className="statusrow">
                <Radar color="green" active={isSending} />
                <div className="statusinfo">
                  <div className={`bigstate ${isSending ? "on-green" : ""}`}>
                    <span className="pulse" /> {isSending ? "Sending…" : "Ready"}
                  </div>
                  <div className="statusnote">To nearby devices</div>
                  <div className="kv">
                    <span>⌁ Frequency</span>
                    <b>{freqKHz} kHz</b>
                  </div>
                  <div className="kv">
                    <span>⊞ Modulation</span>
                    <b>FSK</b>
                  </div>
                  <div className="kv">
                    <span>⇥ Bitrate</span>
                    <b>{bitrate} bps</b>
                  </div>
                  <div className="kv">
                    <span>◷ Duration</span>
                    <b>{lastSend ? `${lastSend.duration.toFixed(1)} s` : "—"}</b>
                  </div>
                </div>
              </div>
            </section>

            <section className="card">
              <h2>Live Signal</h2>
              <Waveform analyser={mic.analyser} color="#3fb950" />
            </section>
          </div>
        )}

        {/* ---------------- RECEIVE ---------------- */}
        {tab === "receive" && (
          <div className="stack">
            <section className="card">
              <h2>Receiving Status</h2>
              <div className="statusrow">
                <Radar color="purple" active={isListening} />
                <div className="statusinfo">
                  <div className={`bigstate ${isListening ? "on-purple" : ""}`}>
                    <span className="pulse" /> {isListening ? "Listening…" : status}
                  </div>
                  <div className="statusnote">Waiting for messages</div>
                  <div className="kv">
                    <span>⌁ Frequency</span>
                    <b className="pv">{freqKHz} kHz</b>
                  </div>
                  <div className="kv">
                    <span>⊟ Bandwidth</span>
                    <b className="pv">{bwKHz} kHz</b>
                  </div>
                  <div className="kv">
                    <span>◎ Sensitivity</span>
                    <b className="pv">High</b>
                  </div>
                  <div className="kv">
                    <span>⌁ Noise Level</span>
                    <b className="pv">{noiseTxt}</b>
                  </div>
                </div>
              </div>
            </section>

            <section className="card">
              <div className="cardhead">
                <h2>Received Message</h2>
                {last && <span className="badge">✓ Valid</span>}
              </div>
              {last ? (
                <div className="rxmsg">
                  <div className="rxfrom">
                    From <b>#{last.source ?? "?"}</b>
                    {last.to === 0 ? (
                      <span className="tag">broadcast</span>
                    ) : (
                      <span className="tag direct">to #{last.to}</span>
                    )}
                  </div>
                  <div className="rxtext">{last.message}</div>
                  <div className="rxmeta">Received at: {last.at}</div>
                  <div className="rxmeta">Length: {last.message.length} characters</div>
                </div>
              ) : (
                <div className="empty">No messages received yet.</div>
              )}
            </section>

            <section className="card">
              <h2>Signal Quality</h2>
              <div className="metrics">
                <MetricTile
                  icon="⇅"
                  label="SNR"
                  value={snrTxt}
                  rating={m.snrDb != null ? (m.snrDb > 20 ? "Excellent" : "Good") : undefined}
                  ratingColor={m.snrDb != null && m.snrDb > 20 ? "excellent" : "good"}
                />
                <MetricTile
                  icon="⇢"
                  label="Packet Loss"
                  value={last ? "0%" : "—"}
                  rating={last ? "Excellent" : undefined}
                  ratingColor="excellent"
                />
                <MetricTile
                  icon="⟳"
                  label="Frequency Offset"
                  value={offsetTxt}
                  rating={m.offsetHz != null ? (Math.abs(m.offsetHz) < 25 ? "Good" : "Fair") : undefined}
                  ratingColor="good"
                />
                <MetricTile
                  icon="⌁"
                  label="Confidence"
                  value={confidence}
                  rating={last?.sync_score != null ? (last.sync_score > 0.95 ? "Excellent" : "Good") : undefined}
                  ratingColor={last?.sync_score != null && last.sync_score > 0.95 ? "excellent" : "good"}
                />
              </div>
            </section>
          </div>
        )}

        {/* ---------------- STATUS ---------------- */}
        {tab === "status" && (
          <div className="stack">
            <section className="card">
              <h2>Node</h2>
              <div className="kv"><span>State</span><b>{status}</b></div>
              <div className="kv"><span>Backend</span><b>{getBackend()}</b></div>
              <div className="kv"><span>Uptime (session)</span><b>{uptime}</b></div>
              <div className="kv"><span>Messages received</span><b>{messages.length}</b></div>
              <div className="kv"><span>Mic metrics</span><b>{mic.active ? "on" : "off"}</b></div>
            </section>

            <section className="card">
              <h2>Modem Configuration</h2>
              {config ? (
                <>
                  <div className="kv"><span>Sample rate</span><b>{config.sample_rate} Hz</b></div>
                  <div className="kv"><span>Bit rate (baud)</span><b>{config.baud} bps</b></div>
                  <div className="kv"><span>Tone spacing</span><b>{config.freq_shift} Hz</b></div>
                  <div className="kv"><span>Candidate freqs</span><b>{config.frequencies.map((f) => (f / 1000).toFixed(1)).join(", ")} kHz</b></div>
                </>
              ) : (
                <div className="empty">Loading config…</div>
              )}
            </section>

            <section className="card">
              <h2>Message History</h2>
              {messages.length ? (
                <div className="history">
                  {[...messages].reverse().map((mm) => (
                    <div key={mm.id} className="hrow">
                      <span className="htext">
                        <b className="hfrom">#{mm.source ?? "?"}</b> {mm.message}
                      </span>
                      <span className="hmeta">
                        {mm.at} · {((mm.base_frequency ?? 0) / 1000).toFixed(1)} kHz ·{" "}
                        {mm.sync_score != null ? `${(mm.sync_score * 100).toFixed(0)}%` : "—"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty">No history yet.</div>
              )}
            </section>
          </div>
        )}
      </main>

      <footer>
        <span className="fdev">▭ This Device</span>
        <span>Frequency: <b>{freqKHz} kHz</b></span>
        <span>SNR: <b>{snrTxt}</b></span>
        <span>Uptime: <b>{uptime}</b></span>
        <span>Messages: <b>{messages.length}</b></span>
      </footer>

      {toast && <div className="toast show">{toast}</div>}
    </div>
  );
}
