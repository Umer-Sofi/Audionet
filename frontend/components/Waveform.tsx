"use client";

import { MutableRefObject, useEffect, useRef } from "react";

/**
 * Live signal waveform.
 * - If the mic analyser is available, draws the real time-domain signal.
 * - Otherwise draws a low, calm idle line (clearly "no signal", not faked data).
 */
export default function Waveform({
  analyser,
  color,
}: {
  analyser: MutableRefObject<AnalyserNode | null>;
  color: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    let raf = 0;
    let t = 0;

    const draw = () => {
      raf = requestAnimationFrame(draw);
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      ctx.shadowBlur = 8;
      ctx.shadowColor = color;
      ctx.beginPath();

      const a = analyser.current;
      if (a) {
        const buf = new Uint8Array(a.fftSize);
        a.getByteTimeDomainData(buf);
        const step = buf.length / W;
        for (let x = 0; x < W; x++) {
          const v = buf[Math.floor(x * step)] / 128 - 1; // -1..1
          const y = H / 2 + v * (H / 2) * 0.9;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
      } else {
        // Idle: a calm, low-amplitude line.
        t += 0.05;
        for (let x = 0; x < W; x++) {
          const y = H / 2 + Math.sin(x * 0.03 + t) * 3 + Math.sin(x * 0.11 + t * 1.7) * 2;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [analyser, color]);

  return <canvas ref={canvasRef} width={620} height={110} className="waveform" />;
}
