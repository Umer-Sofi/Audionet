"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Real microphone analysis via the Web Audio API.
 *
 * Everything here is measured, not faked: when the mic is off, metrics are
 * `null` and the UI shows "—". When on, we compute in-band noise / SNR / peak
 * offset from the live spectrum and expose the analyser for waveform drawing.
 */

export interface MicMetrics {
  noiseDb: number | null; // avg level in the AudioNet band (dBFS-ish)
  snrDb: number | null; // in-band peak minus out-of-band baseline
  offsetHz: number | null; // peak-frequency offset from the nearest expected tone
  peakHz: number | null; // dominant in-band frequency
}

const NULL_METRICS: MicMetrics = {
  noiseDb: null,
  snrDb: null,
  offsetHz: null,
  peakHz: null,
};

const BAND_LO = 17600;
const BAND_HI = 20000;

export function useMic(expectedFreqs: number[]) {
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MicMetrics>(NULL_METRICS);

  const ctxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const expectedRef = useRef<number[]>(expectedFreqs);
  expectedRef.current = expectedFreqs;

  const stop = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    ctxRef.current?.close();
    ctxRef.current = null;
    analyserRef.current = null;
    streamRef.current = null;
    setActive(false);
    setMetrics(NULL_METRICS);
  }, []);

  const start = useCallback(async () => {
    if (active) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      });
      streamRef.current = stream;
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      ctxRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 8192;
      analyser.smoothingTimeConstant = 0.5;
      src.connect(analyser);
      analyserRef.current = analyser;
      setActive(true);
      setError(null);

      const freqData = new Float32Array(analyser.frequencyBinCount);
      const nyq = ctx.sampleRate / 2;
      const hzPerBin = nyq / analyser.frequencyBinCount;

      intervalRef.current = setInterval(() => {
        analyser.getFloatFrequencyData(freqData); // dB values

        let inBandPeak = -Infinity;
        let inBandPeakHz = 0;
        let inBandSum = 0;
        let inBandCount = 0;
        let outSum = 0;
        let outCount = 0;

        for (let i = 0; i < freqData.length; i++) {
          const hz = i * hzPerBin;
          const db = freqData[i];
          if (!isFinite(db)) continue;
          if (hz >= BAND_LO && hz <= BAND_HI) {
            inBandSum += db;
            inBandCount++;
            if (db > inBandPeak) {
              inBandPeak = db;
              inBandPeakHz = hz;
            }
          } else if (hz >= 8000 && hz < 16000) {
            // Quiet reference region for a baseline.
            outSum += db;
            outCount++;
          }
        }

        const noiseDb = inBandCount ? inBandSum / inBandCount : null;
        const baseline = outCount ? outSum / outCount : null;
        const snrDb =
          inBandPeak > -Infinity && baseline != null ? inBandPeak - baseline : null;

        let offsetHz: number | null = null;
        if (inBandPeak > -Infinity && expectedRef.current.length) {
          const nearest = expectedRef.current.reduce((a, b) =>
            Math.abs(b - inBandPeakHz) < Math.abs(a - inBandPeakHz) ? b : a
          );
          offsetHz = Math.round(inBandPeakHz - nearest);
        }

        setMetrics({
          noiseDb: noiseDb != null ? Math.round(noiseDb) : null,
          snrDb: snrDb != null ? Math.round(snrDb) : null,
          offsetHz,
          peakHz: inBandPeak > -Infinity ? Math.round(inBandPeakHz) : null,
        });
      }, 250);
    } catch {
      setError("Microphone access denied");
    }
  }, [active]);

  useEffect(() => () => stop(), [stop]);

  return { active, error, metrics, analyser: analyserRef, start, stop };
}
