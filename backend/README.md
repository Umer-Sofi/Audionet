# AudioNet

Send text between two laptops using **sound** — no Wi-Fi, no Bluetooth.
Type a message on Laptop A; Laptop B hears it through the mic and shows it.

```
text → binary → FSK tones → speaker → 🔊 air 🔊 → microphone → FFT → binary → text
```

## Run it (on BOTH laptops)

No system libraries needed — works on Python 3.9+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The first run asks for **microphone permission** — click Allow.
Check it's ready:  `curl localhost:8000/status`  → `{"status":"Listening"}`

## Send a message

Put the laptops close (~30 cm), turn the **sender's volume up**, keep it quiet.

```bash
# Laptop A — type your message here:
curl -X POST localhost:8000/send -H 'content-type: application/json' \
     -d '{"message":"hello"}'
```

```bash
# Laptop B — read what arrived (run it a couple times):
curl localhost:8000/received
# → {"message":"hello", "base_frequency":18200.0, "sync_score":1.0}
```

Swap roles to send the other way.

## The 3 endpoints

| Method | Path        | Purpose                              |
| ------ | ----------- | ------------------------------------ |
| POST   | `/send`     | Type a message → transmit it as sound |
| GET    | `/received` | The last message this laptop decoded  |
| GET    | `/status`   | `Idle` / `Listening` / `Sending`      |

## If it won't decode across laptops

The default tones are ~18 kHz (near-inaudible), which some laptop
speakers/mics can't reproduce. **First test in the audible band** so you can
literally hear it working: on **both** laptops, edit one line in
[app/config/frequencies.py](app/config/frequencies.py):

```python
bases = [4000.0, 5000.0, 6000.0, 7000.0]   # audible test band
```

Restart both, send "hello", confirm it arrives, then switch back to the
17600–19400 values for the silent ultrasonic version.

Other knobs (volume, baud, audio device) live in
[app/config/settings.py](app/config/settings.py) — override with `AUDIONET_*`
env vars.
