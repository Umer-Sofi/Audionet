# AudioNet — Frontend

A Next.js (App Router + TypeScript) web UI for the AudioNet backend:
a chat view to send/receive messages over sound, plus a live mic spectrum.

## Prerequisites

- Node.js 18+ (tested on Node 20)
- The [AudioNet backend](../backend) running (default `http://localhost:8000`)

## Run

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**.

The header has a **Backend** field (default `http://localhost:8000`) — change it
if your backend runs on another host/port; it's remembered in the browser.
You can also set a default via `.env.local`:

```bash
cp .env.local.example .env.local
# edit NEXT_PUBLIC_BACKEND_URL
```

## Using it

- **💬 Messages** — type a message, press Enter/Send. Your laptop's speaker
  transmits it; the other laptop (running its own backend + frontend) shows it
  as a received bubble with the frequency and sync quality.
- **📶 Spectrum** — live FFT of this browser's microphone, with the AudioNet
  band (~17.6–20 kHz) highlighted so you can watch the tones during a transfer.
  (Uses the browser mic directly; independent of the backend.)

The status pill (top-right) reflects the backend: **Listening / Sending / Idle**.

## Build for production

```bash
npm run build
npm run start
```

## How it talks to the backend

`lib/api.ts` calls three endpoints:

| UI action            | Backend call     |
| -------------------- | ---------------- |
| Send a message       | `POST /send`     |
| Poll for new message | `GET /received`  |
| Status pill          | `GET /status`    |

CORS is enabled on the backend, so the frontend can run on a different
port/origin than the API.
