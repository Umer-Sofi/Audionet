"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Live frequency spectrum of the browser's microphone (Web Audio API).
 * Purely visual — independent of the Python backend. The AudioNet band
 * (~17.6–20 kHz) is highlighted so you can watch the FSK tones appear.
 */
export default function Spectrum({ onError }: { onError: (msg: string) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [running, setRunning] = useState(false);

  const ctxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);

  const stop = () => {
    setRunning(false);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    ctxRef.current?.close();
    ctxRef.current = null;
    const c = canvasRef.current;
    if (c) c.getContext("2d")?.clearRect(0, 0, c.width, c.height);
  };

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      });
      streamRef.current = stream;
      const audioCtx = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      ctxRef.current = audioCtx;
      const src = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 8192;
      analyser.smoothingTimeConstant = 0.6;
      src.connect(analyser);
      analyserRef.current = analyser;
      setRunning(true);
    } catch {
      onError("Mic access denied for spectrum");
    }
  };

  // Draw loop
  useEffect(() => {
    if (!running) return;
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const analyser = analyserRef.current!;
    const audioCtx = ctxRef.current!;
    const freqData = new Uint8Array(analyser.frequencyBinCount);

    const draw = () => {
      rafRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(freqData);
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      const nyq = audioCtx.sampleRate / 2;
      const maxHz = 22000;
      const bins = freqData.length;
      const hzPerBin = nyq / bins;

      // AudioNet band highlight
      const bandLo = (17600 / maxHz) * W;
      const bandHi = (20000 / maxHz) * W;
      ctx.fillStyle = "rgba(227,179,65,0.10)";
      ctx.fillRect(bandLo, 0, bandHi - bandLo, H);

      const usableBins = Math.floor(maxHz / hzPerBin);
      for (let i = 0; i < usableBins; i++) {
        const hz = i * hzPerBin;
        const x = (hz / maxHz) * W;
        const v = freqData[i] / 255;
        const h = v * H;
        const inBand = hz >= 17600 && hz <= 20000;
        ctx.fillStyle = inBand
          ? `rgba(57,211,195,${0.35 + v * 0.65})`
          : `rgba(90,120,160,${0.25 + v * 0.55})`;
        ctx.fillRect(x, H - h, Math.max(W / usableBins, 1) + 0.5, h);
      }

      ctx.fillStyle = "#8b949e";
      ctx.font = "11px sans-serif";
      for (let khz = 2; khz <= 22; khz += 2) {
        const x = ((khz * 1000) / maxHz) * W;
        ctx.fillRect(x, H - 4, 1, 4);
        ctx.fillText(`${khz}k`, x - 6, H - 8);
      }
    };
    draw();
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [running]);

  // Cleanup on unmount
  useEffect(() => () => stop(), []);

  return (
    <section className="view spectrum">
      <div className="specbar">
        <button onClick={() => (running ? stop() : start())}>
          {running ? "⏸ Stop mic spectrum" : "▶ Start mic spectrum"}
        </button>
        <span>
          <span className="swatch" style={{ background: "#39d3c3" }} />
          live spectrum (this browser&apos;s mic)
        </span>
        <span>
          <span className="swatch" style={{ background: "#e3b341" }} />
          AudioNet band (~17.6–20 kHz)
        </span>
      </div>
      <canvas ref={canvasRef} width={1000} height={360} />
    </section>
  );
}
